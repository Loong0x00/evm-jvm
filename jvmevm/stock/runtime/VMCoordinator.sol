// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {StockTypes} from "./StockTypes.sol";

error StockControlError(uint256 code);

interface ITinyJvmStepModule {
    function inspect(address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash)
        external view returns (uint32 codeOffset, uint32 codeLength, uint8 maxStack, uint8 maxLocals);

    function step(
        address page,
        bytes32 expectedPageHash,
        bytes32 expectedPayloadHash,
        StockTypes.Machine calldata beforeState,
        uint8 budget
    ) external view returns (StockTypes.Machine memory afterState, uint8 executed);
}

/// Persistent, hash-pinned S0 controller. Each resume is one atomic transaction.
contract VMCoordinator {
    uint256 private constant INT_TAG = uint256(1) << 64;
    uint256 private constant COMMIT_RESERVE = 800_000;
    uint256 private constant CALL_MARGIN = 20_000;

    address public immutable module;
    address public immutable page;
    bytes32 public immutable expectedModuleHash;
    bytes32 public immutable expectedPageHash;
    bytes32 public immutable expectedPayloadHash;

    StockTypes.Machine private machineState;
    uint64 private currentEpoch;
    uint64 private currentTotalSteps;
    bytes32 private currentStateDigest;
    bool private entered;

    event Checkpoint(
        uint64 indexed epoch,
        uint64 totalSteps,
        uint32 pc,
        uint8 sp,
        bool done,
        int32 result,
        uint8 executed,
        uint8 dirtyWords,
        bytes32 stateDigest
    );

    constructor(
        address module_,
        address page_,
        bytes32 expectedModuleHash_,
        bytes32 expectedPageHash_,
        bytes32 expectedPayloadHash_
    ) {
        module = module_;
        page = page_;
        expectedModuleHash = expectedModuleHash_;
        expectedPageHash = expectedPageHash_;
        expectedPayloadHash = expectedPayloadHash_;
        _checkModule();
        _inspect();
        currentStateDigest = _digest(machineState, 0, 0);
    }

    function resume(uint64 expectedEpoch, uint8 maxJvmSteps, uint8 maxDirtyWords)
        external returns (
            uint64 newEpoch,
            bool done,
            int32 result,
            uint8 executed,
            uint8 dirtyWords
        )
    {
        if (machineState.done) revert StockControlError(1);
        _checkModule();
        if (expectedEpoch != currentEpoch) revert StockControlError(3);
        if (maxJvmSteps == 0 || maxJvmSteps > 16 || maxDirtyWords == 0 || maxDirtyWords > 32) {
            revert StockControlError(4);
        }
        if (entered) revert StockControlError(7);
        if (gasleft() <= COMMIT_RESERVE + CALL_MARGIN) revert StockControlError(5);
        entered = true;

        StockTypes.Machine memory beforeState = machineState;
        bytes memory input = abi.encodeCall(
            ITinyJvmStepModule.step,
            (page, expectedPageHash, expectedPayloadHash, beforeState, maxJvmSteps)
        );
        // Loading state, acquiring the lock and encoding calldata consumed gas
        // after the early guard. Recheck the actual call boundary before subtraction.
        uint256 available = gasleft();
        if (available <= COMMIT_RESERVE + CALL_MARGIN) revert StockControlError(5);
        uint256 stipend = available - COMMIT_RESERVE - CALL_MARGIN;
        (bool ok, bytes memory output) = module.staticcall{gas: stipend}(input);
        if (!ok) _bubble(output);
        if (gasleft() < COMMIT_RESERVE) revert StockControlError(5);

        (StockTypes.Machine memory afterState, uint8 count) = _decodeStep(output);
        if (!_canonical(afterState) || count == 0 || count > maxJvmSteps
            || (afterState.pc == beforeState.pc && afterState.done == beforeState.done)) {
            revert StockControlError(7);
        }
        if (currentEpoch == type(uint64).max || currentTotalSteps > type(uint64).max - count) {
            revert StockControlError(7);
        }

        dirtyWords = _dirty(beforeState, afterState);
        if (dirtyWords > maxDirtyWords) revert StockControlError(6);
        newEpoch = currentEpoch + 1;
        uint64 newTotalSteps = currentTotalSteps + count;
        bytes32 newDigest = _digest(afterState, newEpoch, newTotalSteps);

        // No persistent machine/header write occurs until every external result and
        // conservative dirty-word budget has been checked.
        machineState = afterState;
        currentEpoch = newEpoch;
        currentTotalSteps = newTotalSteps;
        currentStateDigest = newDigest;
        entered = false;

        done = afterState.done;
        result = afterState.result;
        executed = count;
        emit Checkpoint(
            newEpoch, newTotalSteps, afterState.pc, afterState.sp, done, result,
            count, dirtyWords, newDigest
        );
    }

    function checkpoint()
        external view returns (
            uint64 epoch,
            uint64 totalSteps,
            bytes32 stateDigest,
            StockTypes.Machine memory machine
        )
    {
        return (currentEpoch, currentTotalSteps, currentStateDigest, machineState);
    }

    function _checkModule() private view {
        uint256 size;
        bytes32 hash;
        address target = module;
        assembly ("memory-safe") {
            size := extcodesize(target)
            hash := extcodehash(target)
        }
        if (size == 0 || hash != expectedModuleHash) revert StockControlError(2);
    }

    function _inspect() private view {
        bytes memory input = abi.encodeCall(
            ITinyJvmStepModule.inspect,
            (page, expectedPageHash, expectedPayloadHash)
        );
        (bool ok, bytes memory output) = module.staticcall(input);
        if (!ok) _bubble(output);
        if (output.length != 128) revert StockControlError(7);
        uint256[4] memory words = abi.decode(output, (uint256[4]));
        if (words[0] > type(uint32).max || words[1] == 0 || words[1] > 256
            || words[2] > 8 || words[3] > 4) revert StockControlError(7);
    }

    function _decodeStep(bytes memory output)
        private pure returns (StockTypes.Machine memory s, uint8 executed)
    {
        // Machine is 17 static ABI words, followed by executed.
        if (output.length != 18 * 32) revert StockControlError(7);
        uint256[18] memory w = abi.decode(output, (uint256[18]));
        uint32 resultBits = uint32(w[16]);
        uint256 canonicalResult = resultBits <= uint32(type(int32).max)
            ? uint256(resultBits)
            : (~uint256(type(uint32).max)) | uint256(resultBits);
        if (w[0] > type(uint32).max || w[1] > type(uint8).max || w[2] > type(uint8).max
            || w[15] > 1 || w[16] != canonicalResult || w[17] > type(uint8).max) {
            revert StockControlError(7);
        }
        s.pc = uint32(w[0]);
        s.sp = uint8(w[1]);
        s.initialized = uint8(w[2]);
        for (uint256 i; i < 8; ++i) s.stack[i] = w[3 + i];
        for (uint256 i; i < 4; ++i) s.locals[i] = w[11 + i];
        s.done = w[15] != 0;
        s.result = int32(resultBits);
        executed = uint8(w[17]);
    }

    function _canonical(StockTypes.Machine memory s) private pure returns (bool) {
        if (s.sp > 8 || s.initialized >> 4 != 0 || (!s.done && s.result != 0)) return false;
        for (uint256 i; i < 8; ++i) {
            if (i < s.sp) {
                if (!_tagged(s.stack[i])) return false;
            } else if (s.stack[i] != 0) return false;
        }
        for (uint256 i; i < 4; ++i) {
            bool init = (s.initialized & (uint8(1) << i)) != 0;
            if (init ? !_tagged(s.locals[i]) : s.locals[i] != 0) return false;
        }
        return !s.done || s.sp == 0;
    }

    function _dirty(StockTypes.Machine memory a, StockTypes.Machine memory b)
        private pure returns (uint8 count)
    {
        count = 3; // epoch, totalSteps and digest
        if (a.pc != b.pc) ++count;
        if (a.sp != b.sp) ++count;
        if (a.initialized != b.initialized) ++count;
        if (a.done != b.done) ++count;
        if (a.result != b.result) ++count;
        for (uint256 i; i < 8; ++i) if (a.stack[i] != b.stack[i]) ++count;
        for (uint256 i; i < 4; ++i) if (a.locals[i] != b.locals[i]) ++count;
    }

    function _digest(StockTypes.Machine memory s, uint64 epoch, uint64 totalSteps)
        private view returns (bytes32)
    {
        return keccak256(abi.encode(
            uint32(1), expectedPayloadHash, expectedModuleHash, s, epoch, totalSteps
        ));
    }

    function _tagged(uint256 x) private pure returns (bool) {
        return (x & ~(INT_TAG | type(uint32).max)) == 0 && (x & INT_TAG) != 0;
    }

    function _bubble(bytes memory reason) private pure {
        // Preserve an empty nested exceptional-halt payload as empty; in
        // particular, do not relabel module OOG as a structured control error.
        assembly ("memory-safe") { revert(add(reason, 0x20), mload(reason)) }
    }
}
