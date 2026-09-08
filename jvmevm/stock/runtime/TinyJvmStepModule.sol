// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {StockTypes} from "./StockTypes.sol";

error StockPageError(uint256 code);
error StockClassError(uint256 code, uint256 offset);
error StockBytecodeError(uint256 code, uint256 pc);

/// Stateless parser, verifier and bounded executor for the frozen S0 integer profile.
contract TinyJvmStepModule {
    uint256 private constant INT_TAG = uint256(1) << 64;

    struct Parsed {
        uint32 codeOffset;
        uint32 codeLength;
        uint8 maxStack;
        uint8 maxLocals;
        bytes starts;
        uint32[] constantOffsets;
    }

    function inspect(address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash)
        external view returns (uint32 codeOffset, uint32 codeLength, uint8 maxStack, uint8 maxLocals)
    {
        bytes memory d = _page(page, expectedPageHash, expectedPayloadHash);
        Parsed memory p = _parse(d);
        return (p.codeOffset, p.codeLength, p.maxStack, p.maxLocals);
    }

    function step(
        address page,
        bytes32 expectedPageHash,
        bytes32 expectedPayloadHash,
        StockTypes.Machine calldata beforeState,
        uint8 budget
    ) external view returns (StockTypes.Machine memory afterState, uint8 executed) {
        if (budget == 0 || budget > 16) revert StockBytecodeError(14, beforeState.pc);
        bytes memory d = _page(page, expectedPageHash, expectedPayloadHash);
        Parsed memory p = _parse(d);
        afterState = beforeState;
        _validateMachine(afterState, p);

        while (executed < budget && !afterState.done) {
            uint32 pc = afterState.pc;
            uint8 op = uint8(d[uint256(p.codeOffset) + pc]);
            if (op == 0x00) {
                afterState.pc = pc + 1;
            } else if (op >= 0x02 && op <= 0x08) {
                uint32 v = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                _push(afterState, p.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x10) {
                _push(afterState, p.maxStack, _sign8(uint8(d[uint256(p.codeOffset) + pc + 1])), pc);
                afterState.pc = pc + 2;
            } else if (op == 0x11) {
                uint16 x = (uint16(uint8(d[uint256(p.codeOffset) + pc + 1])) << 8)
                    | uint16(uint8(d[uint256(p.codeOffset) + pc + 2]));
                _push(afterState, p.maxStack, _sign16(x), pc);
                afterState.pc = pc + 3;
            } else if (op == 0x12 || op == 0x13) {
                uint16 index = op == 0x12
                    ? uint16(uint8(d[uint256(p.codeOffset) + pc + 1]))
                    : (uint16(uint8(d[uint256(p.codeOffset) + pc + 1])) << 8)
                        | uint16(uint8(d[uint256(p.codeOffset) + pc + 2]));
                // The parser proved the tag and bounds. Integer bytes follow the tag.
                uint256 cp = p.constantOffsets[index];
                uint32 v = _u4raw(d, cp + 1);
                _push(afterState, p.maxStack, v, pc);
                afterState.pc = pc + (op == 0x12 ? 2 : 3);
            } else if (op == 0x15 || (op >= 0x1a && op <= 0x1d)) {
                uint8 local = op == 0x15 ? uint8(d[uint256(p.codeOffset) + pc + 1]) : op - 0x1a;
                if ((afterState.initialized & (uint8(1) << local)) == 0) revert StockBytecodeError(11, pc);
                _pushTagged(afterState, p.maxStack, afterState.locals[local], pc);
                afterState.pc = pc + (op == 0x15 ? 2 : 1);
            } else if (op == 0x36 || (op >= 0x3b && op <= 0x3e)) {
                uint8 local = op == 0x36 ? uint8(d[uint256(p.codeOffset) + pc + 1]) : op - 0x3b;
                uint256 v = _pop(afterState, pc);
                afterState.locals[local] = v;
                afterState.initialized |= uint8(1) << local;
                afterState.pc = pc + (op == 0x36 ? 2 : 1);
            } else if (op == 0x60 || op == 0x64 || op == 0x68) {
                uint32 b = _bits(_pop(afterState, pc));
                uint32 a = _bits(_pop(afterState, pc));
                uint32 v;
                unchecked {
                    if (op == 0x60) v = a + b;
                    else if (op == 0x64) v = a - b;
                    else v = a * b;
                }
                _push(afterState, p.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x74) {
                uint32 a = _bits(_pop(afterState, pc));
                uint32 v;
                unchecked { v = uint32(0) - a; }
                _push(afterState, p.maxStack, v, pc);
                afterState.pc = pc + 1;
            } else if (op == 0x84) {
                uint8 local = uint8(d[uint256(p.codeOffset) + pc + 1]);
                if ((afterState.initialized & (uint8(1) << local)) == 0) revert StockBytecodeError(11, pc);
                uint32 addend = _sign8(uint8(d[uint256(p.codeOffset) + pc + 2]));
                uint32 v;
                unchecked { v = _bits(afterState.locals[local]) + addend; }
                afterState.locals[local] = _tag(v);
                afterState.pc = pc + 3;
            } else if (op == 0xac) {
                if (afterState.sp != 1) revert StockBytecodeError(5, pc);
                uint32 v = _bits(_pop(afterState, pc));
                afterState.pc = pc + 1;
                afterState.done = true;
                afterState.result = int32(v);
            } else {
                // Unreachable: every unsupported instruction was rejected by _parse.
                revert StockBytecodeError(6, pc);
            }
            unchecked { ++executed; }
            if (!afterState.done && afterState.pc >= p.codeLength) {
                revert StockBytecodeError(7, afterState.pc);
            }
        }
    }

    function _page(address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash)
        private view returns (bytes memory payload)
    {
        uint256 size;
        bytes32 actualHash;
        assembly ("memory-safe") {
            size := extcodesize(page)
            actualHash := extcodehash(page)
        }
        if (size < 2 || size > 4097) revert StockPageError(1);
        bytes32 firstWord;
        assembly ("memory-safe") {
            extcodecopy(page, 0, 0, 1)
            firstWord := mload(0)
        }
        if (bytes1(firstWord) != 0x00) revert StockPageError(2);
        if (actualHash != expectedPageHash) revert StockPageError(3);
        payload = new bytes(size - 1);
        assembly ("memory-safe") { extcodecopy(page, add(payload, 0x20), 1, sub(size, 1)) }
        if (keccak256(payload) != expectedPayloadHash) revert StockPageError(4);
    }

    function _parse(bytes memory d) private pure returns (Parsed memory out) {
        uint256 n = d.length;
        _need(n, 0, 10, n);
        if (_u4raw(d, 0) != 0xcafebabe || _u2raw(d, 4) != 0 || _u2raw(d, 6) != 52) {
            revert StockClassError(2, _u4raw(d, 0) != 0xcafebabe ? 0 : 4);
        }
        uint16 cpCount = _u2raw(d, 8);
        if (cpCount < 1 || cpCount > 512) revert StockClassError(3, 8);
        uint8[] memory tags = new uint8[](cpCount);
        uint32[] memory offsets = new uint32[](cpCount);
        uint16[] memory utfLens = new uint16[](cpCount);
        uint256 pos = 10;
        for (uint256 i = 1; i < cpCount; ++i) {
            _need(n, pos, 1, n);
            uint8 tag = uint8(d[pos]);
            tags[i] = tag;
            offsets[i] = uint32(pos);
            unchecked { ++pos; }
            if (tag == 1) {
                _need(n, pos, 2, n);
                uint16 len = _u2raw(d, pos);
                utfLens[i] = len;
                pos += 2;
                _need(n, pos, len, n);
                pos += len;
            } else if (tag == 3 || tag == 4) {
                _need(n, pos, 4, n); pos += 4;
            } else if (tag == 5 || tag == 6) {
                if (i + 1 >= cpCount) revert StockClassError(3, offsets[i]);
                _need(n, pos, 8, n); pos += 8; unchecked { ++i; }
            } else if (tag == 7 || tag == 8 || tag == 16) {
                _need(n, pos, 2, n); pos += 2;
            } else if (tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 18) {
                _need(n, pos, 4, n); pos += 4;
            } else if (tag == 15) {
                _need(n, pos, 3, n); pos += 3;
            } else {
                revert StockClassError(3, offsets[i]);
            }
        }

        _need(n, pos, 8, n);
        uint16 access = _u2raw(d, pos);
        uint16 thisIndex = _u2raw(d, pos + 2);
        uint16 superIndex = _u2raw(d, pos + 4);
        uint16 interfaceCount = _u2raw(d, pos + 6);
        if ((access & 0x0001) == 0 || (access & ~uint16(0x0431)) != 0
            || (access & 0x0410) == 0x0410 || interfaceCount != 0) {
            revert StockClassError(4, pos);
        }
        _className(d, tags, offsets, utfLens, thisIndex, false, pos + 2);
        _className(d, tags, offsets, utfLens, superIndex, true, pos + 4);
        pos += 8;

        _need(n, pos, uint256(interfaceCount) * 2 + 2, n);
        pos += uint256(interfaceCount) * 2;
        uint16 fieldCount = _u2raw(d, pos); pos += 2;
        if (fieldCount != 0) revert StockClassError(4, pos - 2);

        _need(n, pos, 2, n);
        uint256 methodCountOffset = pos;
        uint16 methodCount = _u2raw(d, pos); pos += 2;
        uint256 runCount;
        uint256 ambiguousOffset;
        uint256 rootAccessOffset;
        uint256 rootDescriptorOffset;
        uint256 rootCodeOffset;
        bool runDescriptorOK;
        bool runAccessOK;
        uint256 codeCount;
        uint256 duplicateCodeOffset;
        for (uint256 m; m < methodCount; ++m) {
            _need(n, pos, 8, n);
            uint256 methodOffset = pos;
            uint16 methodAccess = _u2raw(d, pos);
            uint16 nameIndex = _u2raw(d, pos + 2);
            uint16 descIndex = _u2raw(d, pos + 4);
            uint16 attrCount = _u2raw(d, pos + 6);
            _utfIndex(tags, nameIndex, pos + 2);
            _utfIndex(tags, descIndex, pos + 4);
            bool isRun = _utfEq(d, offsets, utfLens, nameIndex, bytes("run"));
            if (_utfEq(d, offsets, utfLens, nameIndex, bytes("<clinit>"))) {
                revert StockClassError(4, methodOffset);
            }
            if (isRun) {
                if (runCount == 0) {
                    rootAccessOffset = methodOffset;
                    rootDescriptorOffset = methodOffset + 4;
                    rootCodeOffset = methodOffset + 6;
                    runDescriptorOK = _utfEq(d, offsets, utfLens, descIndex, bytes("()I"));
                    bool visibility = (methodAccess & 0x0001) != 0 && (methodAccess & 0x0006) == 0;
                    uint16 forbidden = 0x0520; // synchronized, native, abstract
                    uint16 legal = 0x1dff; // all Java 8 method flag bits
                    runAccessOK = visibility && (methodAccess & 0x0008) != 0
                        && (methodAccess & forbidden) == 0 && (methodAccess & ~legal) == 0;
                } else if (ambiguousOffset == 0) {
                    ambiguousOffset = methodOffset;
                }
                ++runCount;
            }
            pos += 8;
            for (uint256 a; a < attrCount; ++a) {
                _need(n, pos, 6, n);
                uint256 attrOffset = pos;
                uint16 attrName = _u2raw(d, pos);
                _utfIndex(tags, attrName, pos);
                uint32 attrLen = _u4raw(d, pos + 2);
                pos += 6;
                _need(n, pos, attrLen, n);
                if (isRun && _utfEq(d, offsets, utfLens, attrName, bytes("Code"))) {
                    ++codeCount;
                    if (codeCount > 1 && duplicateCodeOffset == 0) duplicateCodeOffset = attrOffset;
                    _parseCode(d, pos, attrLen, tags, offsets, utfLens, out, attrOffset);
                }
                pos += attrLen;
            }
        }
        if (runCount == 0) revert StockClassError(5, methodCountOffset);
        if (runCount > 1) revert StockClassError(5, ambiguousOffset);
        if (!runAccessOK) revert StockClassError(5, rootAccessOffset);
        if (!runDescriptorOK) revert StockClassError(5, rootDescriptorOffset);
        if (codeCount != 1) revert StockClassError(6, codeCount == 0 ? rootCodeOffset : duplicateCodeOffset);

        _need(n, pos, 2, n);
        uint16 classAttrs = _u2raw(d, pos); pos += 2;
        for (uint256 a; a < classAttrs; ++a) {
            _need(n, pos, 6, n);
            uint16 attrName = _u2raw(d, pos);
            _utfIndex(tags, attrName, pos);
            uint32 attrLen = _u4raw(d, pos + 2);
            pos += 6;
            _need(n, pos, attrLen, n);
            pos += attrLen;
        }
        if (pos != n) revert StockClassError(1, pos);
        out.starts = _predecode(d, out, tags, offsets);
        // Reuse the offsets already validated in this resume. Rescanning a
        // 512-entry CP at each ldc could exceed the coordinator's step stipend.
        out.constantOffsets = offsets;
    }

    function _parseCode(
        bytes memory d, uint256 body, uint256 len,
        uint8[] memory tags, uint32[] memory offsets, uint16[] memory utfLens,
        Parsed memory out, uint256 attrOffset
    ) private pure {
        uint256 end = body + len;
        if (len < 12) revert StockClassError(6, attrOffset);
        uint16 maxStack = _u2raw(d, body);
        uint16 maxLocals = _u2raw(d, body + 2);
        uint32 codeLen = _u4raw(d, body + 4);
        if (maxStack > 8) revert StockClassError(6, body);
        if (maxLocals > 4) revert StockClassError(6, body + 2);
        if (codeLen == 0 || codeLen > 256) revert StockClassError(6, body + 4);
        uint256 codeOffset = body + 8;
        _need(d.length, codeOffset, codeLen, end);
        uint256 p = codeOffset + codeLen;
        _need(d.length, p, 2, end);
        uint16 handlers = _u2raw(d, p); p += 2;
        if (handlers != 0) revert StockClassError(6, p - 2);
        _need(d.length, p, uint256(handlers) * 8 + 2, end);
        p += uint256(handlers) * 8;
        uint16 attrs = _u2raw(d, p); p += 2;
        for (uint256 i; i < attrs; ++i) {
            _need(d.length, p, 6, end);
            uint16 name = _u2raw(d, p);
            _utfIndex(tags, name, p);
            uint32 nestedLen = _u4raw(d, p + 2);
            p += 6;
            _need(d.length, p, nestedLen, end);
            p += nestedLen;
        }
        if (p != end) revert StockClassError(6, p);
        out.codeOffset = uint32(codeOffset);
        out.codeLength = codeLen;
        out.maxStack = uint8(maxStack);
        out.maxLocals = uint8(maxLocals);
    }

    function _predecode(bytes memory d, Parsed memory p, uint8[] memory tags, uint32[] memory offsets)
        private pure returns (bytes memory starts)
    {
        starts = new bytes(p.codeLength);
        uint256 pc;
        while (pc < p.codeLength) {
            starts[pc] = 0x01;
            uint8 op = uint8(d[uint256(p.codeOffset) + pc]);
            uint256 width = 1;
            if (op == 0x10 || op == 0x12 || op == 0x15 || op == 0x36) width = 2;
            else if (op == 0x11 || op == 0x13 || op == 0x84) width = 3;
            else if (!(op == 0x00 || (op >= 0x02 && op <= 0x08)
                || (op >= 0x1a && op <= 0x1d) || (op >= 0x3b && op <= 0x3e)
                || op == 0x60 || op == 0x64 || op == 0x68 || op == 0x74 || op == 0xac)) {
                revert StockBytecodeError(6, pc);
            }
            if (pc + width > p.codeLength) revert StockBytecodeError(2, pc);
            if (op == 0x12 || op == 0x13) {
                uint16 index = op == 0x12
                    ? uint16(uint8(d[uint256(p.codeOffset) + pc + 1]))
                    : (uint16(uint8(d[uint256(p.codeOffset) + pc + 1])) << 8)
                        | uint16(uint8(d[uint256(p.codeOffset) + pc + 2]));
                if (index == 0 || index >= tags.length || tags[index] != 3) {
                    revert StockBytecodeError(6, pc);
                }
                // offsets is deliberately touched so a malformed zero offset cannot pass.
                if (offsets[index] == 0) revert StockBytecodeError(6, pc);
            }
            if (op == 0x15 || op == 0x36 || op == 0x84) {
                uint8 local = uint8(d[uint256(p.codeOffset) + pc + 1]);
                if (local >= p.maxLocals) revert StockBytecodeError(8, pc);
            } else if ((op >= 0x1a && op <= 0x1d) && op - 0x1a >= p.maxLocals) {
                revert StockBytecodeError(8, pc);
            } else if ((op >= 0x3b && op <= 0x3e) && op - 0x3b >= p.maxLocals) {
                revert StockBytecodeError(8, pc);
            }
            pc += width;
        }
    }

    function _validateMachine(StockTypes.Machine memory s, Parsed memory p) private pure {
        if (s.done || s.result != 0 || s.sp > p.maxStack || s.initialized >> p.maxLocals != 0
            || s.pc >= p.codeLength || p.starts[s.pc] != 0x01) {
            revert StockBytecodeError(s.pc >= p.codeLength || (s.pc < p.codeLength && p.starts[s.pc] != 0x01) ? 12 : 14, s.pc);
        }
        for (uint256 i; i < 8; ++i) {
            if (i < s.sp) {
                if (!_tagged(s.stack[i])) revert StockBytecodeError(14, s.pc);
            } else if (s.stack[i] != 0) revert StockBytecodeError(14, s.pc);
        }
        for (uint256 i; i < 4; ++i) {
            bool init = (s.initialized & (uint8(1) << i)) != 0;
            if (i >= p.maxLocals && (init || s.locals[i] != 0)) revert StockBytecodeError(14, s.pc);
            if (i < p.maxLocals && (init ? !_tagged(s.locals[i]) : s.locals[i] != 0)) {
                revert StockBytecodeError(14, s.pc);
            }
        }
    }

    function _className(
        bytes memory d, uint8[] memory tags, uint32[] memory offsets, uint16[] memory lens,
        uint16 index, bool mustObject, uint256 errorOffset
    ) private pure {
        if (index == 0 || index >= tags.length || tags[index] != 7) revert StockClassError(3, errorOffset);
        uint16 name = _u2raw(d, uint256(offsets[index]) + 1);
        _utfIndex(tags, name, errorOffset);
        uint256 start = uint256(offsets[name]) + 3;
        uint256 len = lens[name];
        if (len == 0) revert StockClassError(3, errorOffset);
        bool component = false;
        for (uint256 i; i < len; ++i) {
            uint8 c = uint8(d[start + i]);
            if (c == 0 || c >= 0x80 || c == 0x2e || c == 0x3b || c == 0x5b) revert StockClassError(3, errorOffset);
            if (c == 0x2f) {
                if (!component || i + 1 == len) revert StockClassError(3, errorOffset);
                component = false;
            } else component = true;
        }
        bool isObject = _utfEq(d, offsets, lens, name, bytes("java/lang/Object"));
        if ((mustObject && !isObject) || (!mustObject && isObject)) {
            revert StockClassError(4, errorOffset);
        }
    }

    function _utfIndex(uint8[] memory tags, uint16 index, uint256 off) private pure {
        if (index == 0 || index >= tags.length || tags[index] != 1) revert StockClassError(3, off);
    }

    function _utfEq(bytes memory d, uint32[] memory offsets, uint16[] memory lens, uint16 index, bytes memory value)
        private pure returns (bool)
    {
        if (lens[index] != value.length) return false;
        uint256 start = uint256(offsets[index]) + 3;
        for (uint256 i; i < value.length; ++i) if (d[start + i] != value[i]) return false;
        return true;
    }

    function _need(uint256 actual, uint256 pos, uint256 amount, uint256 boundary) private pure {
        if (pos > boundary || amount > boundary - pos || boundary > actual) revert StockClassError(1, pos);
    }

    function _u2raw(bytes memory d, uint256 p) private pure returns (uint16) {
        return (uint16(uint8(d[p])) << 8) | uint16(uint8(d[p + 1]));
    }

    function _u4raw(bytes memory d, uint256 p) private pure returns (uint32) {
        return (uint32(uint8(d[p])) << 24) | (uint32(uint8(d[p + 1])) << 16)
            | (uint32(uint8(d[p + 2])) << 8) | uint32(uint8(d[p + 3]));
    }

    function _sign8(uint8 x) private pure returns (uint32) {
        return (x & 0x80) == 0 ? uint32(x) : uint32(x) | 0xffffff00;
    }

    function _sign16(uint16 x) private pure returns (uint32) {
        return (x & 0x8000) == 0 ? uint32(x) : uint32(x) | 0xffff0000;
    }

    function _tag(uint32 x) private pure returns (uint256) { return INT_TAG | uint256(x); }
    function _bits(uint256 x) private pure returns (uint32) { return uint32(x); }
    function _tagged(uint256 x) private pure returns (bool) { return (x & ~(INT_TAG | type(uint32).max)) == 0 && (x & INT_TAG) != 0; }

    function _push(StockTypes.Machine memory s, uint8 maxStack, uint32 value, uint256 pc) private pure {
        _pushTagged(s, maxStack, _tag(value), pc);
    }

    function _pushTagged(StockTypes.Machine memory s, uint8 maxStack, uint256 value, uint256 pc) private pure {
        if (s.sp >= maxStack) revert StockBytecodeError(9, pc);
        s.stack[s.sp] = value;
        unchecked { ++s.sp; }
    }

    function _pop(StockTypes.Machine memory s, uint256 pc) private pure returns (uint256 value) {
        if (s.sp == 0) revert StockBytecodeError(3, pc);
        unchecked { --s.sp; }
        value = s.stack[s.sp];
        s.stack[s.sp] = 0;
    }
}
