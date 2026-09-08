// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {
    S1Types, S1MethodError, S1BytecodeError, S1ControlError
} from "./S1Types.sol";
import {S1Codec, IS1ClassRegistry} from "./S1Codec.sol";

interface IS1StepModule {
    function step(
        S1Types.ProgramContext calldata program,
        S1Types.MachineV2 calldata beforeState,
        uint16 budget
    ) external view returns (S1Types.MachineV2 memory afterState, uint16 executed);
}

/// Hash-pinned persistent schema-2 controller. Every resume is one atomic
/// transaction and the committed total-step cap makes valid loops finite.
contract S1Coordinator {
    uint256 private constant INT_TAG = uint256(1) << 64;
    uint256 private constant COMMIT_RESERVE = 800_000;
    uint256 private constant CALL_MARGIN = 20_000;

    address public immutable parser;
    bytes32 public immutable expectedParserHash;
    address public immutable module;
    bytes32 public immutable expectedModuleHash;
    bytes32 public immutable classId;
    bytes32 public immutable programId;
    bytes32 public immutable argsHash;
    bytes32 public immutable inputRoot;
    uint64 public immutable maxTotalSteps;

    address private immutable rawPage;
    bytes32 private immutable rawPageHash;
    bytes32 private immutable payloadHash;
    address private immutable metadataPage;
    bytes32 private immutable metadataHash;
    uint16 private immutable selectedMethod;
    uint16 private immutable selectedCodeLength;
    uint8 private immutable selectedMaxStack;
    uint8 private immutable selectedMaxLocals;
    uint256 private immutable selectedStarts;

    S1Types.MachineV2 private machineState;
    uint64 private currentEpoch;
    uint64 private currentTotalSteps;
    bytes32 private currentStateDigest;
    bool private entered;

    event CheckpointV2(
        uint64 indexed epoch,
        bytes32 indexed programId,
        uint64 totalSteps,
        uint32 pc,
        uint8 sp,
        uint8 lifecycle,
        int32 result,
        uint16 executed,
        uint8 dirtyWords,
        bytes32 stateDigest
    );

    constructor(
        address parser_,
        bytes32 expectedParserHash_,
        bytes32 classId_,
        address module_,
        bytes32 expectedModuleHash_,
        bytes memory entry_,
        int32[] memory args_,
        uint64 maxTotalSteps_
    ) {
        parser = parser_;
        expectedParserHash = expectedParserHash_;
        module = module_;
        expectedModuleHash = expectedModuleHash_;
        classId = classId_;
        if (maxTotalSteps_ == 0 || maxTotalSteps_ > 4096) revert S1ControlError(4);
        maxTotalSteps = maxTotalSteps_;

        (uint256 moduleSize, bytes32 actualModuleHash) = S1Codec.codeInfo(module_);
        if (moduleSize == 0 || actualModuleHash != expectedModuleHash_) revert S1ControlError(2);
        S1Codec.ClassView memory c = S1Codec.loadClass(
            parser_, expectedParserHash_, classId_
        );
        rawPage = c.rawPage;
        rawPageHash = c.rawPageHash;
        payloadHash = c.payloadHash;
        metadataPage = c.metadataPage;
        metadataHash = c.metadataHash;

        _validateEntry(entry_);
        bytes32 entryHash = keccak256(entry_);
        uint256 found = type(uint256).max;
        uint256 nextLiteral;
        for (uint16 i; i < c.methodCount; ++i) {
            S1Codec.MethodView memory candidate = S1Codec.loadMethod(c, i);
            if (candidate.errorDomain == 0) {
                if (candidate.literalBase != nextLiteral) revert S1ControlError(2);
                nextLiteral += candidate.literalCount;
            }
            if (candidate.nameHash == entryHash) {
                if (found != type(uint256).max) revert S1MethodError(2, i);
                found = i;
            }
        }
        if (nextLiteral != c.literalCount) revert S1ControlError(2);
        if (found == type(uint256).max) revert S1MethodError(1, type(uint256).max);
        S1Codec.MethodView memory m = S1Codec.loadMethod(c, uint16(found));
        if (m.errorDomain == 1) revert S1MethodError(m.errorCode, m.errorLocation);
        if (m.errorDomain == 2) revert S1BytecodeError(m.errorCode, m.errorLocation);
        // Domain-zero records must independently describe a legal root.
        bool visibility = (m.access & 0x0001) != 0 && (m.access & 0x0006) == 0;
        if (!visibility || (m.access & 0x0008) == 0 || (m.access & 0x0520) != 0
            || (m.access & ~uint16(0x1dff)) != 0) revert S1ControlError(2);
        if (args_.length != m.argc) revert S1MethodError(7, m.declaredIndex);

        selectedMethod = m.declaredIndex;
        selectedCodeLength = m.codeLength;
        selectedMaxStack = m.maxStack;
        selectedMaxLocals = m.maxLocals;
        selectedStarts = m.starts;
        programId = S1Codec.programId(classId_, m, expectedModuleHash_);
        argsHash = keccak256(abi.encode(args_));
        inputRoot = S1Codec.inputRoot(programId, argsHash, maxTotalSteps_);

        for (uint256 i; i < args_.length; ++i) {
            machineState.locals[i] = _tag(uint32(args_[i]));
        }
        if (args_.length != 0) machineState.initialized = uint8((uint256(1) << args_.length) - 1);
        currentStateDigest = _digest(machineState, 0, 0);
    }

    function programContext() public view returns (S1Types.ProgramContext memory p) {
        p.parser = parser;
        p.parserCodeHash = expectedParserHash;
        p.classId = classId;
        p.rawPage = rawPage;
        p.rawPageHash = rawPageHash;
        p.payloadHash = payloadHash;
        p.metadataPage = metadataPage;
        p.metadataHash = metadataHash;
        p.methodIndex = selectedMethod;
        p.programId = programId;
    }

    function resume(uint64 expectedEpoch, uint16 maxJvmSteps, uint8 maxDirtyWords)
        external returns (
            uint64 newEpoch,
            uint8 lifecycle,
            int32 result,
            uint16 executed,
            uint8 dirtyWords
        )
    {
        if (machineState.lifecycle != S1Types.RUNNABLE) revert S1ControlError(1);
        _checkComponents();
        if (expectedEpoch != currentEpoch) revert S1ControlError(3);
        if (maxJvmSteps == 0 || maxJvmSteps > 128 || maxDirtyWords == 0 || maxDirtyWords > 32) {
            revert S1ControlError(4);
        }
        if (entered) revert S1ControlError(7);
        uint64 remaining = maxTotalSteps - currentTotalSteps;
        uint16 effectiveBudget = maxJvmSteps;
        if (remaining < effectiveBudget) effectiveBudget = uint16(remaining);
        if (effectiveBudget == 0) revert S1ControlError(7);
        if (gasleft() <= COMMIT_RESERVE + CALL_MARGIN) revert S1ControlError(5);
        entered = true;

        S1Types.MachineV2 memory beforeState = machineState;
        S1Types.ProgramContext memory context = programContext();
        bytes memory input = abi.encodeCall(IS1StepModule.step, (context, beforeState, effectiveBudget));
        // Retain the S0 post-encoding guard: state loads, the lock and ABI
        // preparation all consume gas after the early check.
        uint256 available = gasleft();
        if (available <= COMMIT_RESERVE + CALL_MARGIN) revert S1ControlError(5);
        uint256 stipend = available - COMMIT_RESERVE - CALL_MARGIN;
        (bool ok, bytes memory output) = module.staticcall{gas: stipend}(input);
        if (!ok) _bubble(output);
        if (gasleft() < COMMIT_RESERVE) revert S1ControlError(5);

        (S1Types.MachineV2 memory afterState, uint16 count) = _decodeStep(output);
        if (!_canonical(afterState, false) || count == 0 || count > effectiveBudget
            || (afterState.lifecycle == S1Types.RUNNABLE && count != effectiveBudget)) {
            revert S1ControlError(7);
        }
        if (currentEpoch == type(uint64).max || currentTotalSteps > type(uint64).max - count) {
            revert S1ControlError(7);
        }
        uint64 newTotalSteps = currentTotalSteps + count;
        if (newTotalSteps > maxTotalSteps) revert S1ControlError(7);
        // A Java return at the exact cap wins. Otherwise cap exhaustion is an
        // explicit successful STEP_LIMIT checkpoint preserving the machine.
        if (afterState.lifecycle == S1Types.RUNNABLE && newTotalSteps == maxTotalSteps) {
            afterState.lifecycle = S1Types.STEP_LIMIT;
        }
        if (!_canonical(afterState, true)) revert S1ControlError(7);

        dirtyWords = _dirty(beforeState, afterState);
        if (dirtyWords > maxDirtyWords) revert S1ControlError(6);
        newEpoch = currentEpoch + 1;
        bytes32 newDigest = _digest(afterState, newEpoch, newTotalSteps);

        machineState = afterState;
        currentEpoch = newEpoch;
        currentTotalSteps = newTotalSteps;
        currentStateDigest = newDigest;
        entered = false;

        lifecycle = afterState.lifecycle;
        result = afterState.result;
        executed = count;
        emit CheckpointV2(
            newEpoch, programId, newTotalSteps, afterState.pc, afterState.sp,
            lifecycle, result, count, dirtyWords, newDigest
        );
    }

    function checkpoint() external view returns (
        uint32 schema,
        bytes32 returnedClassId,
        bytes32 returnedProgramId,
        bytes32 returnedInputRoot,
        uint64 epoch,
        uint64 totalSteps,
        bytes32 stateDigest,
        S1Types.MachineV2 memory machine
    ) {
        return (
            uint32(2), classId, programId, inputRoot, currentEpoch,
            currentTotalSteps, currentStateDigest, machineState
        );
    }

    function _checkComponents() private view {
        (uint256 parserSize, bytes32 parserHash) = S1Codec.codeInfo(parser);
        (uint256 moduleSize, bytes32 moduleHash) = S1Codec.codeInfo(module);
        (uint256 rawSize, bytes32 actualRawHash) = S1Codec.codeInfo(rawPage);
        (uint256 metaSize, bytes32 actualMetaHash) = S1Codec.codeInfo(metadataPage);
        if (parserSize == 0 || parserHash != expectedParserHash || moduleSize == 0
            || moduleHash != expectedModuleHash || rawSize < 2 || rawSize > 4097
            || actualRawHash != rawPageHash || metaSize < 193 || metaSize > 8192
            || actualMetaHash != metadataHash) revert S1ControlError(2);
        (bool ok, bytes memory answer) = parser.staticcall(
            abi.encodeCall(IS1ClassRegistry.classRecord, (classId))
        );
        if (!ok || answer.length != 64) revert S1ControlError(2);
        (address issuedPage, bytes32 issuedHash) = abi.decode(answer, (address, bytes32));
        if (issuedPage != metadataPage || issuedHash != metadataHash) revert S1ControlError(2);
    }

    function _decodeStep(bytes memory output)
        private pure returns (S1Types.MachineV2 memory s, uint16 executed)
    {
        // MachineV2 is 21 static ABI words followed by executed.
        if (output.length != 22 * 32) revert S1ControlError(7);
        uint256[22] memory w = abi.decode(output, (uint256[22]));
        uint32 resultBits = uint32(w[20]);
        uint256 canonicalResult = resultBits <= uint32(type(int32).max)
            ? uint256(resultBits) : (~uint256(type(uint32).max)) | uint256(resultBits);
        if (w[0] > type(uint32).max || w[1] > type(uint8).max
            || w[2] > type(uint8).max || w[3] > type(uint8).max
            || w[20] != canonicalResult || w[21] > type(uint16).max) revert S1ControlError(7);
        s.pc = uint32(w[0]);
        s.sp = uint8(w[1]);
        s.initialized = uint8(w[2]);
        s.lifecycle = uint8(w[3]);
        for (uint256 i; i < 8; ++i) s.stack[i] = w[4 + i];
        for (uint256 i; i < 8; ++i) s.locals[i] = w[12 + i];
        s.result = int32(resultBits);
        executed = uint16(w[21]);
    }

    function _canonical(S1Types.MachineV2 memory s, bool allowStepLimit) private view returns (bool) {
        if (s.lifecycle > (allowStepLimit ? S1Types.STEP_LIMIT : S1Types.RETURNED)
            || s.sp > selectedMaxStack || s.initialized >> selectedMaxLocals != 0
            || (s.lifecycle != S1Types.RETURNED && s.result != 0)) return false;
        if (s.lifecycle != S1Types.RETURNED
            && (s.pc >= selectedCodeLength || (selectedStarts & (uint256(1) << s.pc)) == 0)) return false;
        if (s.lifecycle == S1Types.RETURNED && s.sp != 0) return false;
        for (uint256 i; i < 8; ++i) {
            if (i < s.sp) {
                if (!_tagged(s.stack[i])) return false;
            } else if (s.stack[i] != 0) return false;
            bool init = (s.initialized & uint8(uint256(1) << i)) != 0;
            if (i >= selectedMaxLocals && (init || s.locals[i] != 0)) return false;
            if (i < selectedMaxLocals && (init ? !_tagged(s.locals[i]) : s.locals[i] != 0)) return false;
        }
        return true;
    }

    function _dirty(S1Types.MachineV2 memory a, S1Types.MachineV2 memory b)
        private pure returns (uint8 count)
    {
        count = 3; // epoch, totalSteps and digest
        if (a.pc != b.pc) ++count;
        if (a.sp != b.sp) ++count;
        if (a.initialized != b.initialized) ++count;
        if (a.lifecycle != b.lifecycle) ++count;
        if (a.result != b.result) ++count;
        for (uint256 i; i < 8; ++i) if (a.stack[i] != b.stack[i]) ++count;
        for (uint256 i; i < 8; ++i) if (a.locals[i] != b.locals[i]) ++count;
    }

    function _digest(S1Types.MachineV2 memory s, uint64 epoch, uint64 totalSteps)
        private view returns (bytes32)
    {
        return keccak256(abi.encode(
            uint32(2), inputRoot, expectedParserHash, expectedModuleHash,
            s, epoch, totalSteps
        ));
    }

    function _validateEntry(bytes memory entry) private pure {
        if (entry.length == 0 || entry.length > 64) {
            revert S1MethodError(8, type(uint256).max);
        }
        for (uint256 i; i < entry.length; ++i) {
            uint8 c = uint8(entry[i]);
            if (c == 0 || c >= 0x80 || c == 0x2e || c == 0x3b || c == 0x5b
                || c == 0x2f || c == 0x3c || c == 0x3e) {
                revert S1MethodError(8, type(uint256).max);
            }
        }
    }

    function _tag(uint32 x) private pure returns (uint256) { return INT_TAG | uint256(x); }
    function _tagged(uint256 x) private pure returns (bool) {
        return (x & ~(INT_TAG | type(uint32).max)) == 0 && (x & INT_TAG) != 0;
    }
    function _bubble(bytes memory reason) private pure {
        assembly ("memory-safe") { revert(add(reason, 0x20), mload(reason)) }
    }
}
