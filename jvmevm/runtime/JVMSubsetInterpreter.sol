// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;

/// @notice A deliberately tiny JVM classfile interpreter which runs entirely in EVM bytecode.
/// It is not a JVM: it accepts one unambiguous static (int...)int method and implements only
/// the integer constants, local loads/stores, integer expressions, conditional branches,
/// goto, and return listed in JAVA_EVM_M2B_PLAN.md.
contract JVMSubsetInterpreter {
    error ClassError(uint256 code, uint256 offset);
    error MethodError(uint256 code);
    error BytecodeError(uint256 code, uint256 pc);
    error JavaException(uint256 kind);

    uint256 private constant MAX_CONSTANT_POOL = 4096;
    // Explicit allocation caps make malformed-class cost predictable. A Code attribute is at
    // most 65535 bytes in a JVM classfile; this subset further caps operand stack and locals.
    uint256 private constant MAX_CODE = 65535;
    uint256 private constant MAX_STACK = 1024;
    uint256 private constant MAX_LOCALS = 1024;

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
        // Zero means "not CONSTANT_Integer"; integer bits are stored plus one so all bit
        // patterns, including 0xffffffff, remain distinguishable without host resolution.
        uint256[] memory integerConstants = new uint256[](cpCount);
        for (uint256 i = 1; i < cpCount; ++i) {
            uint8 tag = _u1(r);
            if (tag == 1) { // CONSTANT_Utf8
                uint256 n = _u2(r);
                utfOffset[i] = r.pos;
                utfLength[i] = n;
                _skip(r, n);
            } else if (tag == 3) { // CONSTANT_Integer
                integerConstants[i] = uint256(_u4(r)) + 1;
            } else if (tag == 4) {
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
        return _execute(classfile, selected, integerConstants, args, argumentCount);
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
        if (codeLength == 0 || codeLength > MAX_CODE || codeLength > end - c.pos) {
            revert ClassError(7, c.pos);
        }
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

    function _execute(
        bytes memory classfile,
        Selected memory s,
        uint256[] memory integerConstants,
        int32[] calldata args,
        uint256 argc
    ) private pure returns (int32)
    {
        if (s.maxStack > MAX_STACK) revert BytecodeError(1, 0);
        if (s.maxLocals > MAX_LOCALS) revert BytecodeError(10, 0);

        // Predecode every instruction, including unreachable code, before execution. This makes
        // branch-to-operand and truncated-operand rejection independent of the path taken.
        bool[] memory starts = _predecode(classfile, s, integerConstants);
        uint32[] memory stack = new uint32[](s.maxStack);
        uint32[] memory locals = new uint32[](s.maxLocals);
        bool[] memory initialized = new bool[](s.maxLocals);
        for (uint256 i = 0; i < argc; ++i) {
            locals[i] = uint32(args[i]);
            initialized[i] = true;
        }

        uint256 sp;
        uint256 pc;
        while (pc < s.codeLength) {
            uint256 opPC = pc;
            uint8 op = uint8(classfile[s.codeOffset + pc]);
            ++pc;
            if (op >= 0x02 && op <= 0x08) { // iconst_m1 ... iconst_5
                uint32 value = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                sp = _push(stack, sp, value, opPC);
            } else if (op == 0x10) { // bipush signed byte
                sp = _push(stack, sp, uint32(int32(int8(uint8(classfile[s.codeOffset + pc])))), opPC);
                ++pc;
            } else if (op == 0x11) { // sipush signed short
                sp = _push(stack, sp, uint32(int32(_signed16(classfile, s.codeOffset + pc))), opPC);
                pc += 2;
            } else if (op == 0x12 || op == 0x13) { // ldc / ldc_w, CONSTANT_Integer only
                uint256 index;
                if (op == 0x12) {
                    index = uint8(classfile[s.codeOffset + pc]);
                    ++pc;
                } else {
                    index = _unsigned16(classfile, s.codeOffset + pc);
                    pc += 2;
                }
                if (index == 0 || index >= integerConstants.length || integerConstants[index] == 0) {
                    revert BytecodeError(13, opPC);
                }
                sp = _push(stack, sp, uint32(integerConstants[index] - 1), opPC);
            } else if (op == 0x15) { // iload index
                uint256 local = uint8(classfile[s.codeOffset + pc]);
                ++pc;
                sp = _load(stack, sp, locals, initialized, local, opPC);
            } else if (op >= 0x1a && op <= 0x1d) { // iload_0 ... iload_3
                sp = _load(stack, sp, locals, initialized, op - 0x1a, opPC);
            } else if (op == 0x36) { // istore index
                uint256 local = uint8(classfile[s.codeOffset + pc]);
                ++pc;
                sp = _store(stack, sp, locals, initialized, local, opPC);
            } else if (op >= 0x3b && op <= 0x3e) { // istore_0 ... istore_3
                sp = _store(stack, sp, locals, initialized, op - 0x3b, opPC);
            } else if (op == 0x60 || op == 0x64 || op == 0x68) { // iadd / isub / imul
                if (sp < 2) revert BytecodeError(3, opPC);
                unchecked {
                    if (op == 0x60) stack[sp - 2] = stack[sp - 2] + stack[sp - 1];
                    else if (op == 0x64) stack[sp - 2] = stack[sp - 2] - stack[sp - 1];
                    else stack[sp - 2] = stack[sp - 2] * stack[sp - 1];
                }
                --sp; // uint32 arithmetic above is Java int32 wraparound
            } else if (op == 0x6c || op == 0x70) { // idiv / irem
                if (sp < 2) revert BytecodeError(3, opPC);
                int32 dividend = int32(stack[sp - 2]);
                int32 divisor = int32(stack[sp - 1]);
                if (divisor == 0) revert JavaException(1);
                // Solidity rejects MIN/-1, while Java defines wrapped quotient MIN and remainder 0.
                if (dividend == type(int32).min && divisor == -1) {
                    stack[sp - 2] = op == 0x6c ? uint32(0x80000000) : 0;
                } else if (op == 0x6c) {
                    stack[sp - 2] = uint32(dividend / divisor);
                } else {
                    stack[sp - 2] = uint32(dividend % divisor);
                }
                --sp;
            } else if (op == 0x74) { // ineg
                if (sp == 0) revert BytecodeError(3, opPC);
                unchecked {
                    stack[sp - 1] = uint32(0) - stack[sp - 1];
                }
            } else if (op == 0x78 || op == 0x7a || op == 0x7c) { // ishl / ishr / iushr
                if (sp < 2) revert BytecodeError(3, opPC);
                uint256 shift = uint256(stack[sp - 1] & 31);
                if (op == 0x78) stack[sp - 2] = stack[sp - 2] << shift;
                else if (op == 0x7a) stack[sp - 2] = uint32(int32(stack[sp - 2]) >> shift);
                else stack[sp - 2] = stack[sp - 2] >> shift;
                --sp;
            } else if (op == 0x7e || op == 0x80 || op == 0x82) { // iand / ior / ixor
                if (sp < 2) revert BytecodeError(3, opPC);
                if (op == 0x7e) stack[sp - 2] &= stack[sp - 1];
                else if (op == 0x80) stack[sp - 2] |= stack[sp - 1];
                else stack[sp - 2] ^= stack[sp - 1];
                --sp;
            } else if (op == 0x84) { // iinc index, signed-byte constant
                uint256 local = uint8(classfile[s.codeOffset + pc]);
                int8 amount = int8(uint8(classfile[s.codeOffset + pc + 1]));
                if (local >= locals.length) revert BytecodeError(8, opPC);
                if (!initialized[local]) revert BytecodeError(11, opPC);
                unchecked {
                    locals[local] += uint32(int32(amount));
                }
                pc += 2;
            } else if (op == 0x91 || op == 0x92 || op == 0x93) { // i2b / i2c / i2s
                if (sp == 0) revert BytecodeError(3, opPC);
                if (op == 0x91) stack[sp - 1] = uint32(int32(int8(uint8(stack[sp - 1]))));
                else if (op == 0x92) stack[sp - 1] = uint32(uint16(stack[sp - 1]));
                else stack[sp - 1] = uint32(int32(int16(uint16(stack[sp - 1]))));
            } else if (op >= 0x99 && op <= 0x9e) { // ifeq ... ifle
                if (sp == 0) revert BytecodeError(3, opPC);
                int32 value = int32(stack[sp - 1]);
                --sp;
                bool take = _unaryCondition(op, value);
                pc = take ? _decodedTarget(classfile, s.codeOffset, opPC) : pc + 2;
            } else if (op >= 0x9f && op <= 0xa4) { // if_icmpeq ... if_icmple
                if (sp < 2) revert BytecodeError(3, opPC);
                int32 left = int32(stack[sp - 2]);
                int32 right = int32(stack[sp - 1]);
                sp -= 2;
                bool take = _binaryCondition(op, left, right);
                pc = take ? _decodedTarget(classfile, s.codeOffset, opPC) : pc + 2;
            } else if (op == 0xa7) { // goto
                pc = _decodedTarget(classfile, s.codeOffset, opPC);
            } else if (op == 0xac) { // ireturn (valid before later/unreachable code)
                if (sp != 1) revert BytecodeError(4, opPC);
                return int32(stack[0]);
            } else {
                // _predecode rejects this before execution; retained as defense in depth.
                revert BytecodeError(6, opPC);
            }
        }
        revert BytecodeError(7, pc); // reachable fall-through is not an int return
    }

    function _predecode(bytes memory data, Selected memory s, uint256[] memory integerConstants)
        private
        pure
        returns (bool[] memory starts)
    {
        starts = new bool[](s.codeLength);
        uint256 pc;
        while (pc < s.codeLength) {
            starts[pc] = true;
            uint8 op = uint8(data[s.codeOffset + pc]);
            uint256 width = _instructionWidth(op, pc);
            if (width > s.codeLength - pc) revert BytecodeError(2, pc);
            if (op == 0x12 || op == 0x13) {
                uint256 index = op == 0x12
                    ? uint8(data[s.codeOffset + pc + 1])
                    : _unsigned16(data, s.codeOffset + pc + 1);
                if (index == 0 || index >= integerConstants.length || integerConstants[index] == 0) {
                    revert BytecodeError(13, pc);
                }
            }
            pc += width;
        }
        pc = 0;
        while (pc < s.codeLength) {
            uint8 op = uint8(data[s.codeOffset + pc]);
            uint256 width = _instructionWidth(op, pc);
            if (op >= 0x99 && op <= 0xa7) {
                uint256 target = _decodedTarget(data, s.codeOffset, pc);
                if (target >= s.codeLength || !starts[target]) revert BytecodeError(12, pc);
            }
            pc += width;
        }
    }

    function _instructionWidth(uint8 op, uint256 pc) private pure returns (uint256) {
        if (
            (op >= 0x02 && op <= 0x08) || (op >= 0x1a && op <= 0x1d)
                || (op >= 0x3b && op <= 0x3e) || op == 0x60 || op == 0x64 || op == 0x68
                || op == 0x6c || op == 0x70 || op == 0x74 || op == 0x78 || op == 0x7a
                || op == 0x7c || op == 0x7e || op == 0x80 || op == 0x82
                || (op >= 0x91 && op <= 0x93) || op == 0xac
        ) return 1;
        if (op == 0x10 || op == 0x12 || op == 0x15 || op == 0x36) return 2;
        if (op == 0x11 || op == 0x13 || op == 0x84 || (op >= 0x99 && op <= 0xa4) || op == 0xa7) {
            return 3;
        }
        revert BytecodeError(6, pc);
    }

    function _decodedTarget(bytes memory data, uint256 codeOffset, uint256 pc)
        private
        pure
        returns (uint256)
    {
        int256 target = int256(pc) + int256(_signed16(data, codeOffset + pc + 1));
        if (target < 0 || target > int256(MAX_CODE)) revert BytecodeError(12, pc);
        return uint256(target);
    }

    function _signed16(bytes memory data, uint256 off) private pure returns (int16) {
        return int16(_unsigned16(data, off));
    }

    function _unsigned16(bytes memory data, uint256 off) private pure returns (uint16) {
        return (uint16(uint8(data[off])) << 8) | uint16(uint8(data[off + 1]));
    }

    function _push(uint32[] memory stack, uint256 sp, uint32 value, uint256 pc)
        private
        pure
        returns (uint256)
    {
        if (sp >= stack.length) revert BytecodeError(9, pc);
        stack[sp] = value;
        return sp + 1;
    }

    function _load(
        uint32[] memory stack,
        uint256 sp,
        uint32[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _store(
        uint32[] memory stack,
        uint256 sp,
        uint32[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        locals[local] = stack[sp - 1];
        initialized[local] = true;
        return sp - 1;
    }

    function _unaryCondition(uint8 op, int32 value) private pure returns (bool) {
        if (op == 0x99) return value == 0;
        if (op == 0x9a) return value != 0;
        if (op == 0x9b) return value < 0;
        if (op == 0x9c) return value >= 0;
        if (op == 0x9d) return value > 0;
        return value <= 0; // 0x9e
    }

    function _binaryCondition(uint8 op, int32 left, int32 right) private pure returns (bool) {
        if (op == 0x9f) return left == right;
        if (op == 0xa0) return left != right;
        if (op == 0xa1) return left < right;
        if (op == 0xa2) return left >= right;
        if (op == 0xa3) return left > right;
        return left <= right; // 0xa4
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
