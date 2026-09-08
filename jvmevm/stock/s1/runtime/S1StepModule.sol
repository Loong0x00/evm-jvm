// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {
    S1Types, S1MethodError, S1BytecodeError, S1ControlError
} from "./S1Types.sol";
import {S1Codec} from "./S1Codec.sol";

/// Stateless schema-2 executor. Metadata is accepted only through the parser's
/// append-only class registry; callers supply no Code offsets or start maps.
contract S1StepModule {
    uint256 private constant INT_TAG = uint256(1) << 64;

    function step(
        S1Types.ProgramContext calldata program,
        S1Types.MachineV2 calldata beforeState,
        uint16 budget
    ) external view returns (S1Types.MachineV2 memory afterState, uint16 executed) {
        if (budget == 0 || budget > 128) revert S1ControlError(4);
        S1Codec.ClassView memory c = S1Codec.loadClass(
            program.parser, program.parserCodeHash, program.classId
        );
        if (program.rawPage != c.rawPage || program.rawPageHash != c.rawPageHash
            || program.payloadHash != c.payloadHash || program.metadataPage != c.metadataPage
            || program.metadataHash != c.metadataHash) revert S1ControlError(2);
        S1Codec.MethodView memory m = S1Codec.loadMethod(c, program.methodIndex);
        if (m.errorDomain == 1) revert S1MethodError(m.errorCode, m.errorLocation);
        if (m.errorDomain == 2) revert S1BytecodeError(m.errorCode, m.errorLocation);
        bytes32 moduleHash;
        assembly ("memory-safe") { moduleHash := extcodehash(address()) }
        if (S1Codec.programId(program.classId, m, moduleHash) != program.programId) {
            revert S1ControlError(2);
        }

        bytes memory code = new bytes(m.codeLength);
        address rawTarget = c.rawPage;
        uint256 rawOffset = uint256(m.codeOffset) + 1;
        uint256 codeLength = m.codeLength;
        assembly ("memory-safe") {
            extcodecopy(rawTarget, add(code, 0x20), rawOffset, codeLength)
        }
        (uint16[] memory literalPC, uint32[] memory literalBits) = _literals(c, m, code);

        afterState = beforeState;
        _validateMachine(afterState, m);
        while (executed < budget && afterState.lifecycle == S1Types.RUNNABLE) {
            uint32 pc = afterState.pc;
            if (pc >= m.codeLength || (m.starts & (uint256(1) << pc)) == 0) {
                revert S1BytecodeError(12, pc);
            }
            uint8 op = uint8(code[pc]);
            if (op == 0x00) {
                afterState.pc = pc + 1;
            } else if (op >= 0x02 && op <= 0x08) {
                uint32 v = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                _push(afterState, m.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x10) {
                _push(afterState, m.maxStack, _sign8(uint8(code[pc + 1])), pc);
                afterState.pc = pc + 2;
            } else if (op == 0x11) {
                _push(afterState, m.maxStack, _sign16(_u2(code, pc + 1)), pc);
                afterState.pc = pc + 3;
            } else if (op == 0x12 || op == 0x13) {
                _push(afterState, m.maxStack, _literal(literalPC, literalBits, uint16(pc)), pc);
                afterState.pc = pc + (op == 0x12 ? 2 : 3);
            } else if (op == 0x15 || (op >= 0x1a && op <= 0x1d)) {
                uint8 local = op == 0x15 ? uint8(code[pc + 1]) : op - 0x1a;
                if (local >= m.maxLocals) revert S1BytecodeError(8, pc);
                if ((afterState.initialized & (uint8(1) << local)) == 0) {
                    revert S1BytecodeError(11, pc);
                }
                _pushTagged(afterState, m.maxStack, afterState.locals[local], pc);
                afterState.pc = pc + (op == 0x15 ? 2 : 1);
            } else if (op == 0x36 || (op >= 0x3b && op <= 0x3e)) {
                uint8 local = op == 0x36 ? uint8(code[pc + 1]) : op - 0x3b;
                if (local >= m.maxLocals) revert S1BytecodeError(8, pc);
                afterState.locals[local] = _pop(afterState, pc);
                afterState.initialized |= uint8(1) << local;
                afterState.pc = pc + (op == 0x36 ? 2 : 1);
            } else if (op == 0x60 || op == 0x64 || op == 0x68) {
                uint32 b = _bits(_pop(afterState, pc));
                uint32 av = _bits(_pop(afterState, pc));
                uint32 v;
                unchecked {
                    if (op == 0x60) v = av + b;
                    else if (op == 0x64) v = av - b;
                    else v = av * b;
                }
                _push(afterState, m.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x74) {
                uint32 av = _bits(_pop(afterState, pc));
                uint32 v;
                unchecked { v = uint32(0) - av; }
                _push(afterState, m.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x84) {
                uint8 local = uint8(code[pc + 1]);
                if (local >= m.maxLocals) revert S1BytecodeError(8, pc);
                if ((afterState.initialized & (uint8(1) << local)) == 0) {
                    revert S1BytecodeError(11, pc);
                }
                uint32 v;
                unchecked { v = _bits(afterState.locals[local]) + _sign8(uint8(code[pc + 2])); }
                afterState.locals[local] = _tag(v);
                afterState.pc = pc + 3;
            } else if (op >= 0x99 && op <= 0x9e) {
                int32 av = int32(_bits(_pop(afterState, pc)));
                bool take = op == 0x99 ? av == 0 : op == 0x9a ? av != 0
                    : op == 0x9b ? av < 0 : op == 0x9c ? av >= 0
                    : op == 0x9d ? av > 0 : av <= 0;
                afterState.pc = take ? _target(code, m, pc) : pc + 3;
            } else if (op >= 0x9f && op <= 0xa4) {
                int32 b = int32(_bits(_pop(afterState, pc)));
                int32 av = int32(_bits(_pop(afterState, pc)));
                bool take = op == 0x9f ? av == b : op == 0xa0 ? av != b
                    : op == 0xa1 ? av < b : op == 0xa2 ? av >= b
                    : op == 0xa3 ? av > b : av <= b;
                afterState.pc = take ? _target(code, m, pc) : pc + 3;
            } else if (op == 0xa7) {
                afterState.pc = _target(code, m, pc);
            } else if (op == 0xac) {
                if (afterState.sp != 1) revert S1BytecodeError(5, pc);
                uint32 v = _bits(_pop(afterState, pc));
                afterState.pc = pc + 1;
                afterState.lifecycle = S1Types.RETURNED;
                afterState.result = int32(v);
            } else {
                revert S1BytecodeError(6, pc);
            }
            unchecked { ++executed; }
            if (afterState.lifecycle == S1Types.RUNNABLE
                && (afterState.pc >= m.codeLength
                    || (m.starts & (uint256(1) << afterState.pc)) == 0)) {
                revert S1BytecodeError(afterState.pc >= m.codeLength ? 7 : 12, afterState.pc);
            }
        }
    }

    function _literals(
        S1Codec.ClassView memory c, S1Codec.MethodView memory m, bytes memory code
    ) private view returns (uint16[] memory pcs, uint32[] memory bits) {
        pcs = new uint16[](m.literalCount);
        bits = new uint32[](m.literalCount);
        bytes memory records = new bytes(uint256(m.literalCount) * 8);
        if (records.length != 0) {
            address target = c.metadataPage;
            uint256 sourceOffset = 1 + 192 + uint256(c.methodCount) * 128
                + uint256(m.literalBase) * 8;
            uint256 amount = records.length;
            assembly ("memory-safe") {
                extcodecopy(target, add(records, 0x20), sourceOffset, amount)
            }
        }
        uint16 previous;
        for (uint16 i; i < m.literalCount; ++i) {
            uint256 p = uint256(i) * 8;
            uint16 methodIndex = _u2(records, p);
            uint16 pc = _u2(records, p + 2);
            uint32 value = _u4(records, p + 4);
            if (methodIndex != m.declaredIndex || pc >= m.codeLength
                || (i != 0 && pc <= previous) || (m.starts & (uint256(1) << pc)) == 0
                || (uint8(code[pc]) != 0x12 && uint8(code[pc]) != 0x13)) {
                revert S1BytecodeError(16, pc);
            }
            pcs[i] = pc;
            bits[i] = value;
            previous = pc;
        }
    }

    function _literal(uint16[] memory pcs, uint32[] memory bits, uint16 pc)
        private pure returns (uint32)
    {
        uint256 lo;
        uint256 hi = pcs.length;
        while (lo < hi) {
            uint256 mid = (lo + hi) >> 1;
            if (pcs[mid] < pc) lo = mid + 1;
            else hi = mid;
        }
        if (lo >= pcs.length || pcs[lo] != pc) revert S1BytecodeError(16, pc);
        return bits[lo];
    }

    function _target(bytes memory code, S1Codec.MethodView memory m, uint32 pc)
        private pure returns (uint32 target)
    {
        int256 signedTarget = int256(uint256(pc)) + int256(int16(_u2(code, pc + 1)));
        if (signedTarget < 0 || uint256(signedTarget) >= m.codeLength) {
            revert S1BytecodeError(15, pc);
        }
        target = uint32(uint256(signedTarget));
        if ((m.starts & (uint256(1) << target)) == 0) revert S1BytecodeError(15, pc);
    }

    function _validateMachine(S1Types.MachineV2 memory s, S1Codec.MethodView memory m) private pure {
        if (s.lifecycle != S1Types.RUNNABLE || s.result != 0 || s.sp > m.maxStack
            || s.initialized >> m.maxLocals != 0 || s.pc >= m.codeLength
            || (m.starts & (uint256(1) << s.pc)) == 0) {
            bool badPC = s.pc >= m.codeLength
                || (s.pc < m.codeLength && (m.starts & (uint256(1) << s.pc)) == 0);
            revert S1BytecodeError(badPC ? 12 : 14, s.pc);
        }
        for (uint256 i; i < 8; ++i) {
            if (i < s.sp) {
                if (!_tagged(s.stack[i])) revert S1BytecodeError(14, s.pc);
            } else if (s.stack[i] != 0) revert S1BytecodeError(14, s.pc);
            bool init = (s.initialized & uint8(uint256(1) << i)) != 0;
            if (i >= m.maxLocals && (init || s.locals[i] != 0)) revert S1BytecodeError(14, s.pc);
            if (i < m.maxLocals && (init ? !_tagged(s.locals[i]) : s.locals[i] != 0)) {
                revert S1BytecodeError(14, s.pc);
            }
        }
    }

    function _push(S1Types.MachineV2 memory s, uint8 maxStack, uint32 value, uint256 pc) private pure {
        _pushTagged(s, maxStack, _tag(value), pc);
    }
    function _pushTagged(S1Types.MachineV2 memory s, uint8 maxStack, uint256 value, uint256 pc) private pure {
        if (s.sp >= maxStack) revert S1BytecodeError(9, pc);
        s.stack[s.sp] = value;
        unchecked { ++s.sp; }
    }
    function _pop(S1Types.MachineV2 memory s, uint256 pc) private pure returns (uint256 value) {
        if (s.sp == 0) revert S1BytecodeError(3, pc);
        unchecked { --s.sp; }
        value = s.stack[s.sp];
        s.stack[s.sp] = 0;
    }
    function _tag(uint32 x) private pure returns (uint256) { return INT_TAG | uint256(x); }
    function _bits(uint256 x) private pure returns (uint32) { return uint32(x); }
    function _tagged(uint256 x) private pure returns (bool) {
        return (x & ~(INT_TAG | type(uint32).max)) == 0 && (x & INT_TAG) != 0;
    }
    function _sign8(uint8 x) private pure returns (uint32) {
        return (x & 0x80) == 0 ? uint32(x) : uint32(x) | 0xffffff00;
    }
    function _sign16(uint16 x) private pure returns (uint32) {
        return (x & 0x8000) == 0 ? uint32(x) : uint32(x) | 0xffff0000;
    }
    function _u2(bytes memory d, uint256 p) private pure returns (uint16) {
        return (uint16(uint8(d[p])) << 8) | uint16(uint8(d[p + 1]));
    }
    function _u4(bytes memory d, uint256 p) private pure returns (uint32) {
        return (uint32(uint8(d[p])) << 24) | (uint32(uint8(d[p + 1])) << 16)
            | (uint32(uint8(d[p + 2])) << 8) | uint32(uint8(d[p + 3]));
    }
}
