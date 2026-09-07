// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;

/// @notice A deliberately tiny JVM classfile interpreter which runs entirely in EVM bytecode.
/// It is not a JVM: it accepts one unambiguous static (int...)int method and implements only
/// iload/iload_<n>, iadd, and ireturn.
contract JVMSubsetInterpreter {
    error ClassError(uint256 code, uint256 offset);
    error MethodError(uint256 code);
    error BytecodeError(uint256 code, uint256 pc);

    uint256 private constant MAX_CONSTANT_POOL = 4096;
    uint256 private constant MAX_STACK = 1024;

    struct Reader {
        bytes data;
        uint256 pos;
    }

    struct Selected {
        bool found;
        uint16 access;
        uint256 descriptorOffset;
        uint256 descriptorLength;
        uint256 codeOffset;
        uint256 codeLength;
        uint16 maxStack;
        uint16 maxLocals;
    }

    /// @dev Error codes are intentionally compact to keep the generic runtime small. The host
    /// reports the raw revert data; all parsing, selection, and dispatch failures originate here.
    function interpret(bytes calldata rawClass, string calldata entry, int32[] calldata args)
        external
        pure
        returns (int32)
    {
        bytes memory classfile = rawClass; // unchanged class bytes, copied by Solidity ABI decoding
        bytes memory wanted = bytes(entry);
        Reader memory r = Reader(classfile, 0);
        if (_u4(r) != 0xcafebabe) revert ClassError(1, 0);
        _u2(r); // minor
        _u2(r); // major

        uint256 cpCount = _u2(r);
        if (cpCount == 0 || cpCount > MAX_CONSTANT_POOL || cpCount > classfile.length) {
            revert ClassError(2, r.pos);
        }
        uint256[] memory utfOffset = new uint256[](cpCount);
        uint256[] memory utfLength = new uint256[](cpCount);
        for (uint256 i = 1; i < cpCount; ++i) {
            uint8 tag = _u1(r);
            if (tag == 1) { // CONSTANT_Utf8
                uint256 n = _u2(r);
                utfOffset[i] = r.pos;
                utfLength[i] = n;
                _skip(r, n);
            } else if (tag == 3 || tag == 4) {
                _skip(r, 4);
            } else if (tag == 5 || tag == 6) {
                _skip(r, 8);
                if (i + 1 >= cpCount) revert ClassError(3, r.pos);
                ++i; // long/double occupy two entries
            } else if (tag == 7 || tag == 8 || tag == 16 || tag == 19 || tag == 20) {
                _skip(r, 2);
            } else if (
                tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 17 || tag == 18
            ) {
                _skip(r, 4);
            } else if (tag == 15) {
                _skip(r, 3);
            } else {
                revert ClassError(4, r.pos - 1);
            }
        }

        _skip(r, 6); // class access_flags, this_class, super_class
        uint256 interfacesCount = _u2(r);
        _skip(r, _checkedMul2(interfacesCount, r.pos));
        _skipMembers(r); // fields

        uint256 methodsCount = _u2(r);
        Selected memory selected;
        bool hasClassInitializer;
        for (uint256 m = 0; m < methodsCount; ++m) {
            uint16 access = _u2(r);
            uint256 nameIndex = _u2(r);
            uint256 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            _validUtf8(nameIndex, utfOffset, utfLength, r.pos);
            _validUtf8(descriptorIndex, utfOffset, utfLength, r.pos);
            bool named = _equals(classfile, utfOffset[nameIndex], utfLength[nameIndex], wanted);
            if (_equalsLiteral(classfile, utfOffset[nameIndex], utfLength[nameIndex], bytes("<clinit>"))) {
                hasClassInitializer = true;
            }
            if (named) {
                if (selected.found) revert MethodError(2); // overloaded/ambiguous name
                selected.found = true;
                selected.access = access;
                selected.descriptorOffset = utfOffset[descriptorIndex];
                selected.descriptorLength = utfLength[descriptorIndex];
            }
            bool sawCode;
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                _validUtf8(attributeNameIndex, utfOffset, utfLength, r.pos);
                uint256 attributeStart = r.pos;
                _skip(r, attributeLength);
                if (
                    named && _equalsLiteral(
                        classfile,
                        utfOffset[attributeNameIndex],
                        utfLength[attributeNameIndex],
                        bytes("Code")
                    )
                ) {
                    if (sawCode) revert MethodError(3);
                    sawCode = true;
                    _readCode(classfile, attributeStart, attributeLength, selected);
                }
            }
            if (named && !sawCode) revert MethodError(4);
        }
        _skipAttributes(r); // class attributes
        if (r.pos != classfile.length) revert ClassError(5, r.pos);

        if (!selected.found) revert MethodError(1);
        if (hasClassInitializer) revert MethodError(5); // no JVM class-initialization semantics
        if ((selected.access & 0x0008) == 0) revert MethodError(6); // ACC_STATIC
        if ((selected.access & (0x0020 | 0x0100 | 0x0400)) != 0) revert MethodError(7); // synchronized/native/abstract
        uint256 argumentCount = _intDescriptor(
            classfile, selected.descriptorOffset, selected.descriptorLength
        );
        if (args.length != argumentCount) revert MethodError(9);
        if (selected.maxLocals < argumentCount) revert MethodError(10);
        return _execute(classfile, selected, args, argumentCount);
    }

    function _readCode(bytes memory classfile, uint256 start, uint256 length, Selected memory s)
        private
        pure
    {
        if (start > type(uint256).max - length || start + length > classfile.length) {
            revert ClassError(6, start);
        }
        Reader memory c = Reader(classfile, start);
        uint256 end = start + length;
        s.maxStack = _u2Bounded(c, end);
        s.maxLocals = _u2Bounded(c, end);
        uint256 codeLength = _u4Bounded(c, end);
        if (codeLength == 0 || codeLength > end - c.pos) revert ClassError(7, c.pos);
        s.codeOffset = c.pos;
        s.codeLength = codeLength;
        c.pos += codeLength;
        uint256 exceptionCount = _u2Bounded(c, end);
        if (exceptionCount != 0) revert MethodError(8); // exception semantics unsupported
        uint256 nestedCount = _u2Bounded(c, end);
        for (uint256 i = 0; i < nestedCount; ++i) {
            _u2Bounded(c, end); // nested attribute name index is irrelevant to execution
            uint256 n = _u4Bounded(c, end);
            if (n > end - c.pos) revert ClassError(8, c.pos);
            c.pos += n;
        }
        if (c.pos != end) revert ClassError(9, c.pos);
    }

    function _execute(bytes memory classfile, Selected memory s, int32[] calldata args, uint256 argc)
        private
        pure
        returns (int32)
    {
        if (s.maxStack == 0 || s.maxStack > MAX_STACK) revert BytecodeError(1, 0);
        uint32[] memory stack = new uint32[](s.maxStack);
        uint256 sp;
        uint256 pc;
        while (pc < s.codeLength) {
            uint8 op = uint8(classfile[s.codeOffset + pc]);
            ++pc;
            if (op == 0x15) { // iload index
                if (pc >= s.codeLength) revert BytecodeError(2, pc - 1);
                uint256 local = uint8(classfile[s.codeOffset + pc]);
                ++pc;
                sp = _load(stack, sp, local, args, argc, pc - 2);
            } else if (op >= 0x1a && op <= 0x1d) { // iload_0 ... iload_3
                sp = _load(stack, sp, op - 0x1a, args, argc, pc - 1);
            } else if (op == 0x60) { // iadd
                if (sp < 2) revert BytecodeError(3, pc - 1);
                unchecked {
                    stack[sp - 2] = stack[sp - 2] + stack[sp - 1]; // Java int32 wraparound
                }
                --sp;
            } else if (op == 0xac) { // ireturn
                if (sp != 1) revert BytecodeError(4, pc - 1);
                if (pc != s.codeLength) revert BytecodeError(5, pc - 1);
                return int32(stack[0]);
            } else {
                revert BytecodeError(6, pc - 1);
            }
        }
        revert BytecodeError(7, pc);
    }

    function _load(
        uint32[] memory stack,
        uint256 sp,
        uint256 local,
        int32[] calldata args,
        uint256 argc,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= argc) revert BytecodeError(8, pc);
        if (sp >= stack.length) revert BytecodeError(9, pc);
        stack[sp] = uint32(args[local]);
        return sp + 1;
    }

    function _intDescriptor(bytes memory data, uint256 off, uint256 n)
        private
        pure
        returns (uint256 count)
    {
        if (n < 3 || uint8(data[off]) != 0x28) revert MethodError(11); // '('
        uint256 i = 1;
        while (i < n && uint8(data[off + i]) != 0x29) { // ')'
            if (uint8(data[off + i]) != 0x49) revert MethodError(11); // 'I'
            ++count;
            ++i;
        }
        if (i + 2 != n || uint8(data[off + i]) != 0x29 || uint8(data[off + i + 1]) != 0x49) {
            revert MethodError(11);
        }
    }

    function _skipMembers(Reader memory r) private pure {
        uint256 count = _u2(r);
        for (uint256 i = 0; i < count; ++i) {
            _skip(r, 6);
            _skipAttributes(r);
        }
    }

    function _skipAttributes(Reader memory r) private pure {
        uint256 count = _u2(r);
        for (uint256 i = 0; i < count; ++i) {
            _skip(r, 2);
            _skip(r, _u4(r));
        }
    }

    function _validUtf8(
        uint256 index,
        uint256[] memory offsets,
        uint256[] memory lengths,
        uint256 at
    ) private pure {
        if (index == 0 || index >= offsets.length || offsets[index] == 0) revert ClassError(10, at);
        // lengths[index] may legitimately be zero; offset proves this was a Utf8 entry.
        lengths;
    }

    function _equals(bytes memory data, uint256 off, uint256 n, bytes memory wanted)
        private
        pure
        returns (bool)
    {
        if (n != wanted.length) return false;
        for (uint256 i = 0; i < n; ++i) if (data[off + i] != wanted[i]) return false;
        return true;
    }

    function _equalsLiteral(bytes memory data, uint256 off, uint256 n, bytes memory literal)
        private
        pure
        returns (bool)
    {
        return _equals(data, off, n, literal);
    }

    function _checkedMul2(uint256 n, uint256 at) private pure returns (uint256) {
        if (n > type(uint256).max / 2) revert ClassError(11, at);
        return n * 2;
    }

    function _skip(Reader memory r, uint256 n) private pure {
        if (n > r.data.length - r.pos) revert ClassError(12, r.pos);
        r.pos += n;
    }

    function _u1(Reader memory r) private pure returns (uint8 v) {
        if (r.pos >= r.data.length) revert ClassError(12, r.pos);
        v = uint8(r.data[r.pos]);
        ++r.pos;
    }

    function _u2(Reader memory r) private pure returns (uint16 v) {
        if (r.data.length - r.pos < 2) revert ClassError(12, r.pos);
        v = (uint16(uint8(r.data[r.pos])) << 8) | uint16(uint8(r.data[r.pos + 1]));
        r.pos += 2;
    }

    function _u4(Reader memory r) private pure returns (uint32 v) {
        if (r.data.length - r.pos < 4) revert ClassError(12, r.pos);
        v = (uint32(uint8(r.data[r.pos])) << 24) | (uint32(uint8(r.data[r.pos + 1])) << 16)
            | (uint32(uint8(r.data[r.pos + 2])) << 8) | uint32(uint8(r.data[r.pos + 3]));
        r.pos += 4;
    }

    function _u2Bounded(Reader memory r, uint256 end) private pure returns (uint16 v) {
        if (r.pos > end || end - r.pos < 2) revert ClassError(13, r.pos);
        return _u2(r);
    }

    function _u4Bounded(Reader memory r, uint256 end) private pure returns (uint32 v) {
        if (r.pos > end || end - r.pos < 4) revert ClassError(13, r.pos);
        return _u4(r);
    }
}
