// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;

/// @notice A deliberately small JVM classfile interpreter which runs entirely in EVM bytecode.
/// It accepts either one ordinary class or an unordered raw-class bundle, selects an
/// unambiguous static (int...)int root, and supports direct class-aware static I/V calls.
contract JVMSubsetInterpreter {
    error ClassError(uint256 code, uint256 offset);
    error MethodError(uint256 code);
    error BytecodeError(uint256 code, uint256 pc);
    error JavaException(uint256 kind);
    error CallError(uint256 code, uint256 pc);
    error LinkError(uint256 code, uint256 detail);
    error FieldError(uint256 code, uint256 location);
    error InitError(uint256 code, uint256 classIndex);
    error HierarchyError(uint256 code, uint256 classIndex);
    error ArrayError(uint256 code, uint256 pc);
    error ReferenceError(uint256 code, uint256 pc);
    error ObjectError(uint256 code, uint256 pc);

    uint256 private constant MAX_CONSTANT_POOL = 4096;
    uint256 private constant MAX_CODE = 65535;
    uint256 private constant MAX_STACK = 1024;
    uint256 private constant MAX_LOCALS = 1024;
    uint256 private constant MAX_FRAMES = 128; // root plus Java frames and init continuations
    uint256 private constant MAX_ARRAYS = 1024;
    uint256 private constant MAX_ARRAY_LENGTH = 65536;
    uint256 private constant MAX_ARRAY_ELEMENTS = 262144;
    uint256 private constant MAX_OBJECTS = 1024;
    uint256 private constant MAX_OBJECT_FIELDS = 1024;
    uint256 private constant MAX_OBJECT_FIELD_SLOTS = 65536;
    uint256 private constant MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS;
    uint256 private constant KIND_SHIFT = 32;
    uint256 private constant KIND_INT = 1;
    uint256 private constant KIND_REF = 2;
    uint256 private constant KIND_UNINIT = 3;
    uint8 private constant HEAP_ARRAY = 1;
    uint8 private constant HEAP_OBJECT = 2;

    struct Reader {
        bytes data;
        uint256 pos;
    }

    struct Selected {
        bool loaded;
        uint256 descriptorOffset;
        uint256 descriptorLength;
        uint256 codeOffset;
        uint256 codeLength;
        uint256 maxStack;
        uint256 maxLocals;
        uint256 argumentCount;
        uint8[] argumentKinds;
        uint256[] argumentTypeOffsets;
        uint256[] argumentTypeLengths;
        uint8 returnKind; // 1 = int, 2 = void, 3 = supported reference
        uint256 returnTypeOffset;
        uint256 returnTypeLength;
    }

    struct FieldInfo {
        uint16 accessFlags;
        uint16 nameIndex;
        uint16 descriptorIndex;
        bool hasConstant;
        uint32 constantValue;
    }

    struct ClassInfo {
        bytes data;
        // One packed word per CP slot. Low byte is the tag. Utf8 stores offset/length,
        // Integer stores its 32 bits, and reference entries store their u2 operands.
        uint256[] cp;
        FieldInfo[] fields;
        // One packed word per method: flags/name/descriptor and lazy Code attribute location.
        uint256[] methods;
        uint256 thisNameOffset;
        uint256 thisNameLength;
        uint256 superNameOffset;
        uint256 superNameLength;
        uint256 initializerPlusOne;
        uint16 accessFlags;
        bool invalidInitializer;
        bool unsupportedSemantics;
        bool hasSuperclass;
    }

    struct Frame {
        uint256 classIndex;
        uint256 methodIndex;
        uint256 pc;
        uint256 sp;
        uint256 callPC;
        uint256[] stack; // low 32 bits payload, kind above it
        uint256[] locals;
        bool[] initialized;
        bool isInitializer;
        bool isInitContinuation;
        bool isConstructor;
        bool isConstructorLinked;
        uint256 thisHandle;
    }

    function interpret(bytes calldata rawClass, string calldata entry, int32[] calldata args)
        external
        pure
        returns (int32)
    {
        ClassInfo memory c;
        c.data = rawClass; // unchanged class bytes, copied by Solidity ABI decoding
        Reader memory r = Reader(c.data, 0);
        if (_u4(r) != 0xcafebabe) revert ClassError(1, 0);
        _u2(r); // minor
        _u2(r); // major
        c.cp = _readConstantPool(r);

        uint16 classAccess = _u2(r);
        c.accessFlags = classAccess;
        uint256 thisClass = _u2(r);
        uint256 superClass = _u2(r);
        (c.thisNameOffset, c.thisNameLength) = _className(c, thisClass, r.pos);
        // This stage executes an ordinary class, not an interface.
        if ((classAccess & 0x0200) != 0) revert MethodError(7);
        if (superClass != 0) {
            (c.superNameOffset, c.superNameLength) = _className(c, superClass, r.pos);
            c.hasSuperclass = true;
        }

        uint256 interfacesCount = _u2(r);
        if (interfacesCount != 0) revert LinkError(5, 0);
        _skip(r, _checkedMul2(interfacesCount, r.pos));
        c.fields = _readFields(r, c);

        uint256 methodsCount = _u2(r);
        c.methods = new uint256[](methodsCount);
        bytes memory wanted = bytes(entry);
        uint256 rootPlusOne;
        for (uint256 m = 0; m < methodsCount; ++m) {
            uint16 access = _u2(r);
            uint256 nameIndex = _u2(r);
            uint256 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            _validUtf8(nameIndex, c.cp, r.pos);
            _validUtf8(descriptorIndex, c.cp, r.pos);
            (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[nameIndex]);
            if (_equals(c.data, nameOffset, nameLength, wanted)) {
                if (rootPlusOne != 0) revert MethodError(2);
                rootPlusOne = m + 1;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("<clinit>"))) {
                if (c.initializerPlusOne != 0) c.invalidInitializer = true;
                else c.initializerPlusOne = m + 1;
            }
            uint256 packed = uint256(access) | (nameIndex << 16) | (descriptorIndex << 32);
            uint256 codeCount;
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                _validUtf8(attributeNameIndex, c.cp, r.pos);
                uint256 attributeStart = r.pos;
                _skip(r, attributeLength);
                (uint256 attributeNameOffset, uint256 attributeNameLength) =
                    _utf(c.cp[attributeNameIndex]);
                if (
                    _equalsLiteral(
                        c.data, attributeNameOffset, attributeNameLength, bytes("Code")
                    )
                ) {
                    ++codeCount;
                    if (codeCount == 1) {
                        packed |= attributeStart << 48;
                        packed |= attributeLength << 112;
                    }
                }
            }
            packed |= codeCount << 144;
            c.methods[m] = packed;
        }
        _skipAttributes(r); // class attributes
        if (r.pos != c.data.length) revert ClassError(5, r.pos);
        if (rootPlusOne == 0) revert MethodError(1);

        uint256 root = rootPlusOne - 1;
        uint256 rootMeta = c.methods[root];
        uint16 rootAccess = uint16(rootMeta);
        if ((rootAccess & 0x0008) == 0) revert MethodError(6);
        if ((rootAccess & (0x0020 | 0x0100 | 0x0400)) != 0) revert MethodError(7);
        if (_methodCodeCount(rootMeta) != 1) {
            revert MethodError(_methodCodeCount(rootMeta) == 0 ? 4 : 3);
        }

        Selected[] memory selected = new Selected[](methodsCount);
        selected[root] = _loadRoot(c, rootMeta);
        if (selected[root].returnKind != 1) revert MethodError(11);
        if (args.length != selected[root].argumentCount) revert MethodError(9);
        if (selected[root].maxLocals < selected[root].argumentCount) revert MethodError(10);

        // CP ref -> resolved class/method avoids repeated scans during recursion. A real minimal
        // Object classfile is appended and parsed normally unless this input is Object itself.
        uint256[] memory referenceCache = new uint256[](c.cp.length);
        _predecode(c, selected[root]);
        bool suppliedObject = _isObjectClass(c);
        uint256 classCount = suppliedObject ? 1 : 2;
        ClassInfo[] memory classes = new ClassInfo[](classCount);
        classes[0] = c;
        if (!suppliedObject) classes[1] = _parseBundleClass(_bootstrapObject());
        Selected[][] memory selections = new Selected[][](classCount);
        selections[0] = selected;
        uint256[][] memory caches = new uint256[][](classCount);
        caches[0] = referenceCache;
        uint256[][] memory fieldCaches = new uint256[][](classCount);
        fieldCaches[0] = new uint256[](c.cp.length);
        return _execute(classes, selections, caches, fieldCaches, 0, root, args, false);
    }

    /// @notice Execute a named class from an unordered bundle of unchanged classfiles.
    /// Class declarations and every direct static owner are resolved from classfile metadata here.
    function interpretClasses(
        bytes[] calldata rawClasses,
        string calldata entryClass,
        string calldata entry,
        int32[] calldata args
    ) external pure returns (int32) {
        uint256 inputCount = rawClasses.length;
        if (inputCount == 0 || inputCount > 64) revert LinkError(1, inputCount);

        ClassInfo[] memory users = new ClassInfo[](inputCount);
        uint256 entryPlusOne;
        bool suppliedObject;
        bytes memory wantedClass = bytes(entryClass);
        for (uint256 i = 0; i < inputCount; ++i) {
            users[i] = _parseBundleClass(rawClasses[i]);
            for (uint256 j = 0; j < i; ++j) {
                if (_sameClassName(users[i], users[j])) revert LinkError(2, i);
            }
            if (_isObjectClass(users[i])) suppliedObject = true;
            if (
                _equals(
                    users[i].data,
                    users[i].thisNameOffset,
                    users[i].thisNameLength,
                    wantedClass
                )
            ) entryPlusOne = i + 1;
        }
        if (entryPlusOne == 0) revert LinkError(3, 0);
        uint256 count = suppliedObject ? inputCount : inputCount + 1;
        ClassInfo[] memory classes = new ClassInfo[](count);
        for (uint256 i = 0; i < inputCount; ++i) classes[i] = users[i];
        if (!suppliedObject) classes[inputCount] = _parseBundleClass(_bootstrapObject());
        uint256 rootClass = entryPlusOne - 1;
        _requireSupportedClass(classes[rootClass], rootClass);

        bytes memory wantedMethod = bytes(entry);
        uint256 rootPlusOne;
        for (uint256 m = 0; m < classes[rootClass].methods.length; ++m) {
            uint256 meta = classes[rootClass].methods[m];
            (uint256 nameOffset, uint256 nameLength) =
                _utf(classes[rootClass].cp[(meta >> 16) & 0xffff]);
            if (_equals(classes[rootClass].data, nameOffset, nameLength, wantedMethod)) {
                if (rootPlusOne != 0) revert MethodError(2);
                rootPlusOne = m + 1;
            }
        }
        if (rootPlusOne == 0) revert MethodError(1);
        uint256 root = rootPlusOne - 1;
        uint256 rootMeta = classes[rootClass].methods[root];
        uint16 rootAccess = uint16(rootMeta);
        if ((rootAccess & 0x0008) == 0) revert MethodError(6);
        if ((rootAccess & (0x0020 | 0x0100 | 0x0400)) != 0) revert MethodError(7);
        if (_methodCodeCount(rootMeta) != 1) {
            revert MethodError(_methodCodeCount(rootMeta) == 0 ? 4 : 3);
        }

        Selected[][] memory selected = new Selected[][](count);
        uint256[][] memory caches = new uint256[][](count);
        uint256[][] memory fieldCaches = new uint256[][](count);
        // Method selections and reference caches are allocated only as a class is entered.
        selected[rootClass] = new Selected[](classes[rootClass].methods.length);
        caches[rootClass] = new uint256[](classes[rootClass].cp.length);
        fieldCaches[rootClass] = new uint256[](classes[rootClass].cp.length);
        selected[rootClass][root] = _loadRoot(classes[rootClass], rootMeta);
        Selected memory rootSelection = selected[rootClass][root];
        if (rootSelection.returnKind != 1) revert MethodError(11);
        if (args.length != rootSelection.argumentCount) revert MethodError(9);
        if (rootSelection.maxLocals < rootSelection.argumentCount) revert MethodError(10);
        _predecode(classes[rootClass], rootSelection);
        return _execute(classes, selected, caches, fieldCaches, rootClass, root, args, true);
    }

    function _parseBundleClass(bytes memory rawClass) private pure returns (ClassInfo memory c) {
        c.data = rawClass;
        Reader memory r = Reader(c.data, 0);
        if (_u4(r) != 0xcafebabe) revert ClassError(1, 0);
        _u2(r);
        _u2(r);
        c.cp = _readConstantPool(r);

        c.accessFlags = _u2(r);
        uint256 thisClass = _u2(r);
        uint256 superClass = _u2(r);
        (c.thisNameOffset, c.thisNameLength) = _className(c, thisClass, r.pos);
        if (superClass != 0) {
            (c.superNameOffset, c.superNameLength) = _className(c, superClass, r.pos);
            c.hasSuperclass = true;
        }
        if ((c.accessFlags & 0x0200) != 0) c.unsupportedSemantics = true;

        uint256 interfacesCount = _u2(r);
        if (interfacesCount != 0) c.unsupportedSemantics = true;
        _skip(r, _checkedMul2(interfacesCount, r.pos));
        c.fields = _readFields(r, c);

        uint256 methodsCount = _u2(r);
        c.methods = new uint256[](methodsCount);
        for (uint256 m = 0; m < methodsCount; ++m) {
            uint16 access = _u2(r);
            uint256 nameIndex = _u2(r);
            uint256 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            _validUtf8(nameIndex, c.cp, r.pos);
            _validUtf8(descriptorIndex, c.cp, r.pos);
            (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[nameIndex]);
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("<clinit>"))) {
                if (c.initializerPlusOne != 0) c.invalidInitializer = true;
                else c.initializerPlusOne = m + 1;
            }
            uint256 packed = uint256(access) | (nameIndex << 16) | (descriptorIndex << 32);
            uint256 codeCount;
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                _validUtf8(attributeNameIndex, c.cp, r.pos);
                uint256 attributeStart = r.pos;
                _skip(r, attributeLength);
                (uint256 attributeNameOffset, uint256 attributeNameLength) =
                    _utf(c.cp[attributeNameIndex]);
                if (_equalsLiteral(c.data, attributeNameOffset, attributeNameLength, bytes("Code"))) {
                    ++codeCount;
                    if (codeCount == 1) {
                        packed |= attributeStart << 48;
                        packed |= attributeLength << 112;
                    }
                }
            }
            packed |= codeCount << 144;
            c.methods[m] = packed;
        }
        _skipAttributes(r);
        if (r.pos != c.data.length) revert ClassError(5, r.pos);
    }

    function _requireSupportedClass(ClassInfo memory c, uint256 classIndex) private pure {
        if (c.unsupportedSemantics) revert LinkError(5, classIndex);
    }

    function _sameClassName(ClassInfo memory a, ClassInfo memory b) private pure returns (bool) {
        if (a.thisNameLength != b.thisNameLength) return false;
        for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }
        return true;
    }

    function _isObjectClass(ClassInfo memory c) private pure returns (bool) {
        return _equalsLiteral(c.data, c.thisNameOffset, c.thisNameLength, bytes("java/lang/Object"));
    }

    function _findClass(
        ClassInfo[] memory classes, bytes memory nameData, uint256 nameOffset, uint256 nameLength
    ) private pure returns (bool found, uint256 classIndex) {
        for (uint256 i = 0; i < classes.length; ++i) {
            if (_equalsCross(nameData, nameOffset, nameLength, classes[i].data,
                classes[i].thisNameOffset, classes[i].thisNameLength)) return (true, i);
        }
    }

    function _readConstantPool(Reader memory r) private pure returns (uint256[] memory cp) {
        uint256 cpCount = _u2(r);
        if (cpCount == 0 || cpCount > MAX_CONSTANT_POOL || cpCount > r.data.length) {
            revert ClassError(2, r.pos);
        }
        cp = new uint256[](cpCount);
        for (uint256 i = 1; i < cpCount; ++i) {
            uint8 tag = _u1(r);
            if (tag == 1) { // CONSTANT_Utf8
                uint256 n = _u2(r);
                cp[i] = uint256(tag) | (r.pos << 8) | (n << 72);
                _skip(r, n);
            } else if (tag == 3 || tag == 4) {
                cp[i] = uint256(tag) | (uint256(_u4(r)) << 8);
            } else if (tag == 5 || tag == 6) {
                uint256 high = _u4(r);
                uint256 low = _u4(r);
                cp[i] = uint256(tag) | (high << 8) | (low << 40);
                if (i + 1 >= cpCount) revert ClassError(3, r.pos);
                ++i;
            } else if (tag == 7 || tag == 8 || tag == 16 || tag == 19 || tag == 20) {
                cp[i] = uint256(tag) | (uint256(_u2(r)) << 8);
            } else if (
                tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 17 || tag == 18
            ) {
                uint256 first = _u2(r);
                uint256 second = _u2(r);
                cp[i] = uint256(tag) | (first << 8) | (second << 24);
            } else if (tag == 15) {
                uint256 kind = _u1(r);
                uint256 index = _u2(r);
                cp[i] = uint256(tag) | (kind << 8) | (index << 16);
            } else {
                revert ClassError(4, r.pos - 1);
            }
        }
    }

    function _loadRoot(ClassInfo memory c, uint256 meta)
        private
        pure
        returns (Selected memory s)
    {
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.returnKind != 1) revert MethodError(11);
        for (uint256 i = 0; i < s.argumentKinds.length; ++i) {
            if (s.argumentKinds[i] != KIND_INT) revert MethodError(11);
        }
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        _readCode(c.data, start, length, s);
        if (s.maxStack > MAX_STACK) revert BytecodeError(1, 0);
        if (s.maxLocals > MAX_LOCALS) revert BytecodeError(10, 0);
        s.loaded = true;
    }

    function _loadCallee(ClassInfo memory c, uint256 method, uint256 callPC)
        private
        pure
        returns (Selected memory s)
    {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if (
            (access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
                || _methodCodeCount(meta) != 1
        ) revert CallError(4, callPC);
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c.data, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS || s.maxLocals < s.argumentCount) {
            revert CallError(4, callPC);
        }
        s.loaded = true;
    }

    function _execute(
        ClassInfo[] memory classes,
        Selected[][] memory selected,
        uint256[][] memory referenceCaches,
        uint256[][] memory fieldCaches,
        uint256 rootClass,
        uint256 root,
        int32[] calldata args,
        bool bundleMode
    ) private pure returns (int32) {
        Frame[] memory frames = new Frame[](MAX_FRAMES);
        frames[0] = _newFrame(rootClass, root, selected[rootClass][root], 0);
        for (uint256 i = 0; i < args.length; ++i) {
            frames[0].locals[i] = _packInt(uint32(args[i]));
            frames[0].initialized[i] = true;
        }
        uint256 depth = 1;
        uint8[] memory initializationState = new uint8[](classes.length);
        bool[] memory initializerStarted = new bool[](classes.length);
        uint256[][] memory staticValues = new uint256[][](classes.length);
        uint256[] memory parentLinks = new uint256[](classes.length);
        uint8[] memory hierarchyState = new uint8[](classes.length);
        for (uint256 i = 0; i < classes.length; ++i) {
            staticValues[i] = new uint256[](classes[i].fields.length);
            for (uint256 j = 0; j < classes[i].fields.length; ++j) {
                uint8 fieldKind = _fieldKind(classes[i], classes[i].fields[j]);
                if (fieldKind == KIND_INT) staticValues[i][j] = _packInt(0);
                else if (fieldKind == KIND_REF) staticValues[i][j] = _packRef(0);
            }
        }
        // Arrays and objects share one one-based, unforgeable handle namespace. The independent
        // logical limits still apply, while the outer tables remain lazy for scalar-only programs.
        uint32[][] memory arrayHeap;
        uint256[][] memory objectHeap;
        uint8[] memory heapKinds;
        uint256[] memory heapClasses;
        uint256 nextHandle;
        uint256 arrayCount;
        uint256 totalElements;
        uint256 objectCount;
        uint256 totalFieldSlots;
        // Build each dynamic class's default instance layout once. Copying the packed defaults
        // per allocation is linear; repeatedly resolving every descriptor and recomputing every
        // declaration offset made the 65,536-slot logical boundary needlessly quadratic.
        uint256[][] memory objectFieldDefaults = new uint256[][](classes.length);
        bool[] memory objectLayoutsLoaded = new bool[](classes.length);
        _validateHierarchy(classes, rootClass, parentLinks, hierarchyState);
        depth = _initializeClass(
            classes, staticValues, initializationState, frames, depth, rootClass,
            parentLinks, hierarchyState
        );

        while (depth != 0) {
            Frame memory f = frames[depth - 1];
            if (f.isInitContinuation) {
                uint256 initializingClass = f.classIndex;
                ClassInfo memory initializing = classes[initializingClass];
                if (initializing.initializerPlusOne != 0 && !initializerStarted[initializingClass]) {
                    initializerStarted[initializingClass] = true;
                    if (selected[initializingClass].length == 0) {
                        selected[initializingClass] = new Selected[](initializing.methods.length);
                        referenceCaches[initializingClass] = new uint256[](initializing.cp.length);
                        fieldCaches[initializingClass] = new uint256[](initializing.cp.length);
                    }
                    uint256 initializerMethod = initializing.initializerPlusOne - 1;
                    selected[initializingClass][initializerMethod] =
                        _loadInitializer(initializing, initializerMethod, initializingClass);
                    _predecode(initializing, selected[initializingClass][initializerMethod]);
                    if (depth == MAX_FRAMES) revert JavaException(2);
                    Frame memory initializer = _newFrame(
                        initializingClass, initializerMethod,
                        selected[initializingClass][initializerMethod], 0
                    );
                    initializer.isInitializer = true;
                    frames[depth] = initializer;
                    ++depth;
                    continue;
                }
                initializationState[initializingClass] = 2;
                --depth;
                continue;
            }
            ClassInfo memory c = classes[f.classIndex];
            Selected memory selection = selected[f.classIndex][f.methodIndex];
            if (f.pc >= selection.codeLength) revert BytecodeError(7, f.pc);
            uint256 opPC = f.pc;
            uint8 op = uint8(c.data[selection.codeOffset + f.pc]);
            ++f.pc;
            if (op == 0x00) { // nop
                continue;
            } else if (op == 0x01) { // aconst_null
                f.sp = _push(f.stack, f.sp, _packRef(0), opPC);
            } else if (op >= 0x02 && op <= 0x08) { // iconst_m1 ... iconst_5
                uint32 value = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                f.sp = _push(f.stack, f.sp, _packInt(value), opPC);
            } else if (op == 0x10) { // bipush
                f.sp = _push(f.stack, f.sp, _packInt(
                    uint32(int32(int8(uint8(c.data[selection.codeOffset + f.pc]))))
                ), opPC);
                ++f.pc;
            } else if (op == 0x11) { // sipush
                f.sp = _push(f.stack, f.sp, _packInt(
                    uint32(int32(_signed16(c.data, selection.codeOffset + f.pc)))
                ), opPC);
                f.pc += 2;
            } else if (op == 0x12 || op == 0x13) { // ldc / ldc_w, Integer only
                uint256 index;
                if (op == 0x12) {
                    index = uint8(c.data[selection.codeOffset + f.pc]);
                    ++f.pc;
                } else {
                    index = _unsigned16(c.data, selection.codeOffset + f.pc);
                    f.pc += 2;
                }
                if (index == 0 || index >= c.cp.length || uint8(c.cp[index]) != 3) {
                    revert BytecodeError(13, opPC);
                }
                f.sp = _push(f.stack, f.sp, _packInt(uint32(c.cp[index] >> 8)), opPC);
            } else if (op == 0x15 || op == 0x19) { // iload / aload
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                f.sp = op == 0x19
                    ? _loadReference(f.stack, f.sp, f.locals, f.initialized, local, opPC)
                    : _loadKind(f.stack, f.sp, f.locals, f.initialized, local, KIND_INT, opPC);
            } else if (op >= 0x1a && op <= 0x1d) { // iload_0..3
                f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x1a, KIND_INT, opPC
                );
            } else if (op >= 0x2a && op <= 0x2d) { // aload_0..3
                f.sp = _loadReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x2a, opPC
                );
            } else if (op == 0x2e) { // iaload
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint256 handle = _payload(f.stack[f.sp - 2]);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    _throwJava(5, frames, depth);
                }
                f.stack[f.sp - 2] = _packInt(arrayHeap[handle][uint256(uint32(index))]);
                --f.sp;
            } else if (op == 0x36 || op == 0x3a) { // istore / astore
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                f.sp = op == 0x3a
                    ? _storeReference(f.stack, f.sp, f.locals, f.initialized, local, opPC)
                    : _storeKind(f.stack, f.sp, f.locals, f.initialized, local, KIND_INT, opPC);
            } else if (op >= 0x3b && op <= 0x3e) { // istore_0..3
                f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x3b, KIND_INT, opPC
                );
            } else if (op >= 0x4b && op <= 0x4e) { // astore_0..3
                f.sp = _storeReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x4b, opPC
                );
            } else if (op == 0x4f) { // iastore
                if (f.sp < 3) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 3], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_INT, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint256 handle = _payload(f.stack[f.sp - 3]);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 2])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    _throwJava(5, frames, depth);
                }
                arrayHeap[handle][uint256(uint32(index))] = uint32(_payload(f.stack[f.sp - 1]));
                f.sp -= 3;
            } else if (op == 0x57) { // pop
                if (f.sp == 0) revert BytecodeError(3, opPC);
                --f.sp;
            } else if (op >= 0x58 && op <= 0x5f) {
                f.sp = _permuteCategory1(f.stack, f.sp, op, opPC);
            } else if (op == 0x60 || op == 0x64 || op == 0x68) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint32 right = uint32(_payload(f.stack[f.sp - 1]));
                unchecked {
                    if (op == 0x60) left += right;
                    else if (op == 0x64) left -= right;
                    else left *= right;
                }
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x6c || op == 0x70) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                int32 dividend = int32(uint32(_payload(f.stack[f.sp - 2])));
                int32 divisor = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (divisor == 0) _throwJava(1, frames, depth);
                uint32 result;
                if (dividend == type(int32).min && divisor == -1) {
                    result = op == 0x6c ? uint32(0x80000000) : 0;
                } else if (op == 0x6c) result = uint32(dividend / divisor);
                else result = uint32(dividend % divisor);
                f.stack[f.sp - 2] = _packInt(result);
                --f.sp;
            } else if (op == 0x74) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                unchecked {
                    f.stack[f.sp - 1] = _packInt(uint32(0) - uint32(_payload(f.stack[f.sp - 1])));
                }
            } else if (op == 0x78 || op == 0x7a || op == 0x7c) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint256 shift = _payload(f.stack[f.sp - 1]) & 31;
                if (op == 0x78) left <<= shift;
                else if (op == 0x7a) left = uint32(int32(left) >> shift);
                else left >>= shift;
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x7e || op == 0x80 || op == 0x82) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint32 right = uint32(_payload(f.stack[f.sp - 1]));
                if (op == 0x7e) left &= right;
                else if (op == 0x80) left |= right;
                else left ^= right;
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x84) { // iinc
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                int8 amount = int8(uint8(c.data[selection.codeOffset + f.pc + 1]));
                if (local >= f.locals.length) revert BytecodeError(8, opPC);
                if (!f.initialized[local]) revert BytecodeError(11, opPC);
                _requireKind(f.locals[local], KIND_INT, opPC);
                unchecked {
                    f.locals[local] = _packInt(
                        uint32(_payload(f.locals[local])) + uint32(int32(amount))
                    );
                }
                f.pc += 2;
            } else if (op == 0x91 || op == 0x92 || op == 0x93) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint32 value = uint32(_payload(f.stack[f.sp - 1]));
                if (op == 0x91) value = uint32(int32(int8(uint8(value))));
                else if (op == 0x92) value = uint32(uint16(value));
                else value = uint32(int32(int16(uint16(value))));
                f.stack[f.sp - 1] = _packInt(value);
            } else if (op >= 0x99 && op <= 0x9e) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int32 value = int32(uint32(_payload(f.stack[f.sp - 1])));
                --f.sp;
                f.pc = _unaryCondition(op, value)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op >= 0x9f && op <= 0xa4) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                int32 left = int32(uint32(_payload(f.stack[f.sp - 2])));
                int32 right = int32(uint32(_payload(f.stack[f.sp - 1])));
                f.sp -= 2;
                f.pc = _binaryCondition(op, left, right)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0xa5 || op == 0xa6) { // if_acmpeq / if_acmpne
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 2], heapKinds, nextHandle, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool equal = _payload(f.stack[f.sp - 2]) == _payload(f.stack[f.sp - 1]);
                f.sp -= 2;
                f.pc = ((op == 0xa5) == equal)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0xa7) {
                f.pc = _decodedTarget(c.data, selection.codeOffset, opPC);
            } else if (op == 0xbb) { // new
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                uint256 allocatedClass = _resolveNewClass(
                    classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                );
                uint256 fieldSlots = objectLayoutsLoaded[allocatedClass]
                    ? objectFieldDefaults[allocatedClass].length
                    : _instanceFieldCount(classes, allocatedClass, parentLinks, opPC);
                if (initializationState[allocatedClass] == 0) {
                    uint256 oldDepth = depth;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, allocatedClass,
                        parentLinks, hierarchyState
                    );
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                if (fieldSlots > MAX_OBJECT_FIELDS || objectCount == MAX_OBJECTS
                    || fieldSlots > MAX_OBJECT_FIELD_SLOTS - totalFieldSlots) {
                    _throwJava(7, frames, depth);
                }
                if (!objectLayoutsLoaded[allocatedClass]) {
                    objectFieldDefaults[allocatedClass] = _objectFieldDefaults(
                        classes, allocatedClass, fieldSlots, parentLinks
                    );
                    objectLayoutsLoaded[allocatedClass] = true;
                }
                if (heapKinds.length == 0) {
                    heapKinds = new uint8[](MAX_HANDLES + 1);
                    heapClasses = new uint256[](MAX_HANDLES + 1);
                    arrayHeap = new uint32[][](MAX_HANDLES + 1);
                    objectHeap = new uint256[][](MAX_HANDLES + 1);
                }
                ++objectCount;
                ++nextHandle;
                totalFieldSlots += fieldSlots;
                heapKinds[nextHandle] = HEAP_OBJECT;
                heapClasses[nextHandle] = allocatedClass;
                objectHeap[nextHandle] = new uint256[](fieldSlots);
                for (uint256 i = 0; i < fieldSlots; ++i) {
                    objectHeap[nextHandle][i] = objectFieldDefaults[allocatedClass][i];
                }
                f.sp = _push(f.stack, f.sp, (KIND_UNINIT << KIND_SHIFT) | nextHandle, opPC);
            } else if (op == 0xb2 || op == 0xb3) { // getstatic / putstatic
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 fieldClass, uint256 field, uint8 fieldKind,) = _resolveField(
                    classes, f.classIndex, refIndex, opPC, fieldCaches[f.classIndex],
                    op == 0xb3, true, f.isInitializer, parentLinks, hierarchyState
                );
                if (initializationState[fieldClass] == 0) {
                    uint256 oldDepth = depth;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, fieldClass,
                        parentLinks, hierarchyState
                    );
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                if (op == 0xb2) {
                    if (fieldKind == KIND_REF) {
                        _validatePackedRef(staticValues[fieldClass][field], heapKinds, nextHandle, opPC);
                    }
                    f.sp = _push(f.stack, f.sp, staticValues[fieldClass][field], opPC);
                } else {
                    if (f.sp == 0) revert BytecodeError(3, opPC);
                    _requireKind(f.stack[f.sp - 1], fieldKind, opPC);
                    if (fieldKind == KIND_REF) {
                        FieldInfo memory staticField = classes[fieldClass].fields[field];
                        (uint256 fieldOff, uint256 fieldLen) =
                            _utf(classes[fieldClass].cp[staticField.descriptorIndex]);
                        _requireAssignable(
                            classes, f.stack[f.sp - 1], classes[fieldClass].data, fieldOff, fieldLen,
                            heapKinds, heapClasses, nextHandle, parentLinks, opPC
                        );
                    }
                    staticValues[fieldClass][field] = f.stack[f.sp - 1];
                    --f.sp;
                }
            } else if (op == 0xb4 || op == 0xb5) { // getfield / putfield
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 fieldClass, uint256 field, uint8 fieldKind, uint256 symbolicClass) =
                    _resolveField(
                        classes, f.classIndex, refIndex, opPC, fieldCaches[f.classIndex],
                        op == 0xb5, false, f.isConstructor, parentLinks, hierarchyState
                    );
                uint256 needed = op == 0xb4 ? 1 : 2;
                if (f.sp < needed) revert BytecodeError(3, opPC);
                uint256 receiverSlot = f.sp - needed;
                uint256 receiver = f.stack[receiverSlot];
                uint256 receiverKind = _valueKind(receiver);
                uint256 handle = _payload(receiver);
                bool preSuperWrite = op == 0xb5 && receiverKind == KIND_UNINIT
                    && f.isConstructor && f.thisHandle == handle && f.classIndex == fieldClass;
                if (!preSuperWrite) _requireKind(receiver, KIND_REF, opPC);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                if (!_objectIsClass(heapClasses[handle], symbolicClass, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                _requireProtectedReceiver(
                    classes, f.classIndex, fieldClass,
                    classes[fieldClass].fields[field].accessFlags, heapClasses[handle],
                    parentLinks, opPC
                );
                uint256 objectOffset = _instanceFieldOffset(
                    classes, heapClasses[handle], fieldClass, field, parentLinks, opPC
                );
                if (op == 0xb4) {
                    f.stack[receiverSlot] = objectHeap[handle][objectOffset];
                } else {
                    uint256 fieldValue = f.stack[f.sp - 1];
                    _requireKind(fieldValue, fieldKind, opPC);
                    if (fieldKind == KIND_REF) {
                        FieldInfo memory instanceField = classes[fieldClass].fields[field];
                        (uint256 fieldOff, uint256 fieldLen) =
                            _utf(classes[fieldClass].cp[instanceField.descriptorIndex]);
                        _requireAssignable(
                            classes, fieldValue, classes[fieldClass].data, fieldOff, fieldLen,
                            heapKinds, heapClasses, nextHandle, parentLinks, opPC
                        );
                    }
                    objectHeap[handle][objectOffset] = fieldValue;
                    f.sp -= 2;
                }
            } else if (op == 0xb7) { // invokespecial
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 calleeClass, uint256 callee, uint256 symbolicClass, bool isConstructor) =
                    _resolveSpecial(
                        classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                    );
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                if (!selected[calleeClass][callee].loaded) {
                    selected[calleeClass][callee] = _loadSpecialCallee(
                        classes[calleeClass], callee, opPC, isConstructor
                    );
                    _predecode(classes[calleeClass], selected[calleeClass][callee]);
                }
                Selected memory target = selected[calleeClass][callee];
                if (f.sp < target.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - target.argumentCount - 1;
                uint256 receiver = f.stack[base];
                uint256 handle = _payload(receiver);
                if (isConstructor) {
                    _requireKind(receiver, KIND_UNINIT, opPC);
                    _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                    uint256 allocatedClass = heapClasses[handle];
                    bool constructingThis = f.isConstructor && f.thisHandle == handle;
                    if (constructingThis) {
                        uint256 directParent = parentLinks[f.classIndex];
                        bool validThisOrSuper = symbolicClass == f.classIndex
                            || (directParent != 0 && directParent != type(uint256).max
                                && symbolicClass == directParent - 1);
                        if (!validThisOrSuper) revert ObjectError(3, opPC);
                    } else if (symbolicClass != allocatedClass) {
                        revert ObjectError(3, opPC);
                    }
                    uint16 constructorAccess = uint16(classes[calleeClass].methods[callee]);
                    if ((constructorAccess & 0x0004) != 0
                        && !_samePackage(classes[f.classIndex], classes[calleeClass])
                        && !constructingThis) revert CallError(4, opPC);
                } else {
                    _requireKind(receiver, KIND_REF, opPC);
                    if (handle == 0) _throwJava(6, frames, depth);
                    _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                    if (!_objectIsClass(heapClasses[handle], symbolicClass, parentLinks)) {
                        revert ReferenceError(2, opPC);
                    }
                    uint16 methodAccess = uint16(classes[calleeClass].methods[callee]);
                    if ((methodAccess & 0x0004) != 0 && f.classIndex != calleeClass
                        && !_samePackage(classes[f.classIndex], classes[calleeClass])
                        && !_objectIsClass(heapClasses[handle], f.classIndex, parentLinks)) {
                        revert CallError(4, opPC);
                    }
                }
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    _requireKind(argument, target.argumentKinds[i], opPC);
                    if (target.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, argument, classes[calleeClass].data,
                            target.argumentTypeOffsets[i], target.argumentTypeLengths[i], heapKinds,
                            heapClasses, nextHandle, parentLinks, opPC
                        );
                    }
                }
                if (depth == MAX_FRAMES) revert JavaException(2);
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = isConstructor && _isObjectClass(classes[calleeClass])
                    ? _packRef(uint32(handle)) : receiver;
                child.initialized[0] = true;
                child.isConstructor = isConstructor;
                child.thisHandle = handle;
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    child.locals[i + 1] = f.stack[base + 1 + i];
                    child.initialized[i + 1] = true;
                }
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb8) { // invokestatic
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 calleeClass, uint256 callee) = _resolveCall(
                    classes, f.classIndex, refIndex, opPC, referenceCaches[f.classIndex], bundleMode,
                    parentLinks, hierarchyState
                );
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                if (initializationState[calleeClass] == 0) {
                    uint256 oldDepth = depth;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, calleeClass,
                        parentLinks, hierarchyState
                    );
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                if (!selected[calleeClass][callee].loaded) {
                    selected[calleeClass][callee] = _loadCallee(classes[calleeClass], callee, opPC);
                    _predecode(classes[calleeClass], selected[calleeClass][callee]);
                }
                Selected memory target = selected[calleeClass][callee];
                if (f.sp < target.argumentCount) revert BytecodeError(3, opPC);
                uint256 base = f.sp - target.argumentCount;
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    _requireKind(f.stack[base + i], target.argumentKinds[i], opPC);
                    if (target.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, f.stack[base + i], classes[calleeClass].data,
                            target.argumentTypeOffsets[i], target.argumentTypeLengths[i],
                            heapKinds, heapClasses, nextHandle, parentLinks, opPC
                        );
                    }
                }
                if (depth == MAX_FRAMES) revert JavaException(2);
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    child.locals[i] = f.stack[base + i];
                    child.initialized[i] = true;
                }
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xac || op == 0xb0 || op == 0xb1) { // ireturn / areturn / return
                uint8 actualKind = op == 0xac ? uint8(KIND_INT)
                    : (op == 0xb0 ? uint8(KIND_REF) : uint8(0));
                uint8 descriptorKind = actualKind == 0 ? 2 : (actualKind == KIND_REF ? 3 : 1);
                if (descriptorKind != selection.returnKind) revert CallError(5, opPC);
                if ((actualKind != 0 && f.sp != 1) || (actualKind == 0 && f.sp != 0)) {
                    revert BytecodeError(4, opPC);
                }
                if (f.isConstructor && !_isObjectClass(c) && !f.isConstructorLinked) {
                    revert ObjectError(3, opPC);
                }
                uint256 value;
                if (actualKind != 0) {
                    _requireKind(f.stack[0], actualKind, opPC);
                    if (actualKind == KIND_REF) {
                        _requireAssignable(
                            classes, f.stack[0], c.data, selection.returnTypeOffset,
                            selection.returnTypeLength, heapKinds, heapClasses, nextHandle,
                            parentLinks, opPC
                        );
                    }
                    value = f.stack[0];
                }
                if (depth == 1) {
                    // The externally selected root can only return int.
                    return int32(uint32(_payload(value)));
                }
                uint256 callPC = f.callPC;
                bool completedConstructor = f.isConstructor;
                uint256 completedHandle = f.thisHandle;
                --depth;
                Frame memory caller = frames[depth - 1];
                if (completedConstructor) {
                    _initializeAliases(caller, completedHandle);
                    if (caller.isConstructor && caller.thisHandle == completedHandle) {
                        caller.isConstructorLinked = true;
                    }
                }
                if (actualKind != 0) {
                    caller.sp = _push(caller.stack, caller.sp, value, callPC);
                }
            } else if (op == 0xbc) { // newarray
                uint8 atype = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                if (atype != 10) revert ArrayError(1, opPC);
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int32 signedLength = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (signedLength < 0) _throwJava(4, frames, depth);
                uint256 length = uint256(uint32(signedLength));
                if (
                    arrayCount == MAX_ARRAYS || length > MAX_ARRAY_LENGTH
                        || length > MAX_ARRAY_ELEMENTS - totalElements
                ) _throwJava(7, frames, depth);
                if (heapKinds.length == 0) {
                    heapKinds = new uint8[](MAX_HANDLES + 1);
                    heapClasses = new uint256[](MAX_HANDLES + 1);
                    arrayHeap = new uint32[][](MAX_HANDLES + 1);
                    objectHeap = new uint256[][](MAX_HANDLES + 1);
                }
                ++arrayCount;
                ++nextHandle;
                totalElements += length;
                heapKinds[nextHandle] = HEAP_ARRAY;
                arrayHeap[nextHandle] = new uint32[](length);
                f.stack[f.sp - 1] = _packRef(uint32(nextHandle));
            } else if (op == 0xbe) { // arraylength
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                uint256 handle = _payload(f.stack[f.sp - 1]);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                f.stack[f.sp - 1] = _packInt(uint32(arrayHeap[handle].length));
            } else if (op == 0xc6 || op == 0xc7) { // ifnull / ifnonnull
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool isNull = _payload(f.stack[f.sp - 1]) == 0;
                --f.sp;
                f.pc = ((op == 0xc6) == isNull)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else {
                revert BytecodeError(6, opPC);
            }
        }
        revert BytecodeError(7, 0);
    }

    function _newFrame(uint256 classIndex, uint256 method, Selected memory s, uint256 callPC)
        private
        pure
        returns (Frame memory f)
    {
        f.classIndex = classIndex;
        f.methodIndex = method;
        f.callPC = callPC;
        f.stack = new uint256[](s.maxStack);
        f.locals = new uint256[](s.maxLocals);
        f.initialized = new bool[](s.maxLocals);
    }

    function _loadInitializer(ClassInfo memory c, uint256 method, uint256 classIndex)
        private
        pure
        returns (Selected memory s)
    {
        if (c.invalidInitializer) revert InitError(1, classIndex);
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if (
            (access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
                || _methodCodeCount(meta) != 1
        ) revert InitError(1, classIndex);
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        if (descriptorIndex == 0 || descriptorIndex >= c.cp.length || uint8(c.cp[descriptorIndex]) != 1) {
            revert InitError(1, classIndex);
        }
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.argumentKinds.length != 0 || s.returnKind != 2) revert InitError(1, classIndex);
        s.argumentCount = 0;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c.data, start, length, s)) revert InitError(1, classIndex);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS) revert InitError(1, classIndex);
        s.loaded = true;
    }

    function _initializeClass(
        ClassInfo[] memory classes,
        uint256[][] memory staticValues,
        uint8[] memory initializationState,
        Frame[] memory frames,
        uint256 depth,
        uint256 classIndex,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (uint256) {
        _validateHierarchy(classes, classIndex, parentLinks, hierarchyState);
        uint256 current = classIndex;
        while (initializationState[current] == 0) {
            initializationState[current] = 1; // step 6: mark and prepare before its parent
            ClassInfo memory c = classes[current];
            for (uint256 i = 0; i < c.fields.length; ++i) {
                if ((c.fields[i].accessFlags & 0x0008) != 0 && c.fields[i].hasConstant) {
                    staticValues[current][i] = _packInt(c.fields[i].constantValue);
                }
            }
            uint256 link = parentLinks[current];
            bool parentReady = link == type(uint256).max
                || (link != 0 && initializationState[link - 1] == 2);
            if (c.initializerPlusOne == 0 && parentReady) {
                initializationState[current] = 2;
                return depth;
            }
            if (depth == MAX_FRAMES) revert JavaException(2);
            Frame memory continuation;
            continuation.classIndex = current;
            continuation.isInitContinuation = true;
            frames[depth] = continuation;
            ++depth;
            if (link == type(uint256).max || link == 0) return depth;
            current = link - 1;
            if (initializationState[current] != 0) return depth;
        }
        return depth;
    }

    function _hasActiveInitializer(Frame[] memory frames, uint256 depth)
        private
        pure
        returns (bool)
    {
        for (uint256 i = 0; i < depth; ++i) if (frames[i].isInitializer) return true;
        return false;
    }

    function _validateHierarchy(
        ClassInfo[] memory classes,
        uint256 classIndex,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure {
        if (hierarchyState[classIndex] == 2) return;
        bool[] memory seen = new bool[](classes.length);
        uint256 current = classIndex;
        while (hierarchyState[current] != 2) {
            if (seen[current]) revert HierarchyError(2, current);
            seen[current] = true;
            ClassInfo memory child = classes[current];
            _requireSupportedClass(child, current);
            bool isObject = _equalsLiteral(
                child.data, child.thisNameOffset, child.thisNameLength, bytes("java/lang/Object")
            );
            if (isObject) {
                if (child.hasSuperclass) revert HierarchyError(4, current);
                parentLinks[current] = type(uint256).max;
                break;
            }
            if (!child.hasSuperclass) revert HierarchyError(4, current);

            bool found;
            uint256 parent;
            for (uint256 i = 0; i < classes.length; ++i) {
                if (_equalsCross(
                    child.data, child.superNameOffset, child.superNameLength,
                    classes[i].data, classes[i].thisNameOffset, classes[i].thisNameLength
                )) {
                    found = true;
                    parent = i;
                    break;
                }
            }
            if (!found) {
                if (_equalsLiteral(
                    child.data, child.superNameOffset, child.superNameLength,
                    bytes("java/lang/Object")
                )) {
                    parentLinks[current] = type(uint256).max;
                    break;
                }
                revert HierarchyError(1, current);
            }
            ClassInfo memory parentClass = classes[parent];
            if ((parentClass.accessFlags & 0x0200) != 0) revert HierarchyError(4, current);
            if ((parentClass.accessFlags & 0x0010) != 0) revert HierarchyError(3, current);
            if ((parentClass.accessFlags & 0x0001) == 0 && !_samePackage(child, parentClass)) {
                revert HierarchyError(5, current);
            }
            parentLinks[current] = parent + 1;
            current = parent;
        }
        for (uint256 i = 0; i < classes.length; ++i) {
            if (seen[i]) hierarchyState[i] = 2;
        }
    }

    function _loadSpecialCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, bool isConstructor
    ) private pure returns (Selected memory s) {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & 0x0008) != 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        if (isConstructor && s.returnKind != 2) revert CallError(4, callPC);
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c.data, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS
            || s.maxLocals < s.argumentCount + 1) revert CallError(4, callPC);
        s.loaded = true;
    }

    function _lookupExactMethod(
        ClassInfo[] memory classes, uint256 targetClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256 pc
    ) private pure returns (bool found, uint256 method) {
        ClassInfo memory target = classes[targetClass];
        uint256 foundPlusOne;
        for (uint256 i = 0; i < target.methods.length; ++i) {
            uint256 candidate = target.methods[i];
            (uint256 candidateNameOffset, uint256 candidateNameLength) =
                _utf(target.cp[(candidate >> 16) & 0xffff]);
            if (!_equalsCross(target.data, candidateNameOffset, candidateNameLength,
                nameData, nameOffset, nameLength)) continue;
            (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                _utf(target.cp[(candidate >> 32) & 0xffff]);
            if (!_equalsCross(target.data, candidateDescriptorOffset, candidateDescriptorLength,
                nameData, descriptorOffset, descriptorLength)) continue;
            if (foundPlusOne != 0) revert CallError(3, pc);
            foundPlusOne = i + 1;
        }
        if (foundPlusOne != 0) return (true, foundPlusOne - 1);
    }

    function _findExactMethod(
        ClassInfo[] memory classes, uint256 targetClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256 pc
    ) private pure returns (uint256 method) {
        (bool found, uint256 result) = _lookupExactMethod(
            classes, targetClass, nameData, nameOffset, nameLength,
            descriptorOffset, descriptorLength, pc
        );
        if (!found) revert CallError(3, pc);
        return result;
    }

    function _resolveSpecial(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 method, uint256 symbolic, bool isConstructor) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 10) {
            revert CallError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
            || uint8(caller.cp[ownerClassIndex]) != 7 || natIndex == 0
            || natIndex >= caller.cp.length || uint8(caller.cp[natIndex]) != 12) {
            revert CallError(1, pc);
        }
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert CallError(1, pc);
        (uint256 ownerOff, uint256 ownerLen) = _utf(caller.cp[ownerNameIndex]);
        (bool foundOwner, uint256 resolvedOwner) = _findClass(classes, caller.data, ownerOff, ownerLen);
        if (!foundOwner) revert LinkError(4, pc);
        symbolic = resolvedOwner;
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }
        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (uint256 nameOff, uint256 nameLen) = _utf(caller.cp[nameIndex]);
        (uint256 descriptorOff, uint256 descriptorLen) = _utf(caller.cp[descriptorIndex]);
        isConstructor = _equalsLiteral(caller.data, nameOff, nameLen, bytes("<init>"));
        if (_equalsLiteral(caller.data, nameOff, nameLen, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        owner = symbolic;
        if (isConstructor) {
            method = _findExactMethod(
                classes, owner, caller.data, nameOff, nameLen, descriptorOff, descriptorLen, pc
            );
        } else {
            while (true) {
                (bool found, uint256 resolvedMethod) = _lookupExactMethod(
                    classes, owner, caller.data, nameOff, nameLen,
                    descriptorOff, descriptorLen, pc
                );
                if (found) { method = resolvedMethod; break; }
                uint256 resolutionLink = parentLinks[owner];
                if (resolutionLink == 0 || resolutionLink == type(uint256).max) {
                    revert CallError(3, pc);
                }
                owner = resolutionLink - 1;
            }
            uint16 initiallyResolvedAccess = uint16(classes[owner].methods[method]);
            if ((initiallyResolvedAccess & 0x0002) == 0) {
                // Non-private invokespecial must name a superclass. ACC_SUPER selection begins
                // at the caller's direct superclass and cannot bypass an override there.
                if (!_objectIsClass(callerClass, symbolic, parentLinks) || callerClass == symbolic) {
                    revert ObjectError(3, pc);
                }
                if ((caller.accessFlags & 0x0020) != 0) {
                    uint256 direct = parentLinks[callerClass];
                    if (direct == 0 || direct == type(uint256).max) revert ObjectError(3, pc);
                    owner = direct - 1;
                    while (true) {
                        (bool found, uint256 selectedMethod) = _lookupExactMethod(
                            classes, owner, caller.data, nameOff, nameLen,
                            descriptorOff, descriptorLen, pc
                        );
                        if (found) { method = selectedMethod; break; }
                        uint256 link = parentLinks[owner];
                        if (link == 0 || link == type(uint256).max) revert CallError(3, pc);
                        owner = link - 1;
                    }
                }
            } else if (owner != callerClass) revert CallError(4, pc);
        }
        if (!_canAccessMember(classes, callerClass, owner,
            uint16(classes[owner].methods[method]), parentLinks, hierarchyState)) {
            revert CallError(4, pc);
        }
    }

    function _resolveCall(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 refIndex,
        uint256 pc,
        uint256[] memory cache,
        bool bundleMode,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 method) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 10) {
            revert CallError(1, pc);
        }
        if (cache[refIndex] != 0) {
            owner = (cache[refIndex] >> 128) - 1;
            method = uint128(cache[refIndex]) - 1;
            return (owner, method);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 nameAndTypeIndex = (ref >> 24) & 0xffff;
        if (
            ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
                || uint8(caller.cp[ownerClassIndex]) != 7 || nameAndTypeIndex == 0
                || nameAndTypeIndex >= caller.cp.length
                || uint8(caller.cp[nameAndTypeIndex]) != 12
        ) revert CallError(1, pc);
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (
            ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
                || uint8(caller.cp[ownerNameIndex]) != 1
        ) revert CallError(1, pc);
        (uint256 ownerOffset, uint256 ownerLength) = _utf(caller.cp[ownerNameIndex]);
        bool sameOwner = _equalsSlice(
            caller.data, ownerOffset, ownerLength, caller.thisNameOffset, caller.thisNameLength
        );
        if (sameOwner) {
            owner = callerClass;
        } else {
            if (!bundleMode) revert CallError(2, pc);
            bool foundOwner;
            for (uint256 i = 0; i < classes.length; ++i) {
                if (_equalsCross(
                    caller.data, ownerOffset, ownerLength, classes[i].data,
                    classes[i].thisNameOffset, classes[i].thisNameLength
                )) {
                    owner = i;
                    foundOwner = true;
                    break;
                }
            }
            if (!foundOwner) revert LinkError(4, pc);
        }
        _validateHierarchy(classes, owner, parentLinks, hierarchyState);
        if (owner != callerClass && !_classAccessible(caller, classes[owner])) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[nameAndTypeIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (
            nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
                || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
                || uint8(caller.cp[descriptorIndex]) != 1
        ) revert CallError(1, pc);
        (uint256 nameOffset, uint256 nameLength) = _utf(caller.cp[nameIndex]);
        (uint256 descriptorOffset, uint256 descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (
            _equalsLiteral(caller.data, nameOffset, nameLength, bytes("<clinit>"))
                || _equalsLiteral(caller.data, nameOffset, nameLength, bytes("<init>"))
        ) revert CallError(4, pc);

        uint256 declaring = owner;
        uint256 foundPlusOne;
        while (true) {
            ClassInfo memory target = classes[declaring];
            for (uint256 i = 0; i < target.methods.length; ++i) {
                uint256 candidate = target.methods[i];
                (uint256 candidateNameOffset, uint256 candidateNameLength) =
                    _utf(target.cp[(candidate >> 16) & 0xffff]);
                if (!_equalsCross(
                    target.data, candidateNameOffset, candidateNameLength,
                    caller.data, nameOffset, nameLength
                )) continue;
                (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                    _utf(target.cp[(candidate >> 32) & 0xffff]);
                if (!_equalsCross(
                    target.data, candidateDescriptorOffset, candidateDescriptorLength,
                    caller.data, descriptorOffset, descriptorLength
                )) continue;
                if (foundPlusOne != 0) revert CallError(3, pc);
                foundPlusOne = i + 1;
            }
            if (foundPlusOne != 0) break; // first declaring class with an exact match wins
            uint256 link = parentLinks[declaring];
            if (link == 0 || link == type(uint256).max) revert CallError(3, pc);
            declaring = link - 1;
        }
        owner = declaring;
        method = foundPlusOne - 1;
        if (!_canAccessMember(
            classes, callerClass, owner, uint16(classes[owner].methods[method]),
            parentLinks, hierarchyState
        )) revert CallError(4, pc);
        cache[refIndex] = ((owner + 1) << 128) | foundPlusOne;
    }

    function _resolveField(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 refIndex,
        uint256 pc,
        uint256[] memory cache,
        bool writeAccess,
        bool staticAccess,
        bool privilegedWrite,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 field, uint8 valueKind, uint256 symbolic) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 9) {
            revert FieldError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 nameAndTypeIndex = (ref >> 24) & 0xffff;
        if (
            ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
                || uint8(caller.cp[ownerClassIndex]) != 7 || nameAndTypeIndex == 0
                || nameAndTypeIndex >= caller.cp.length
                || uint8(caller.cp[nameAndTypeIndex]) != 12
        ) revert FieldError(1, pc);
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert FieldError(1, pc);
        (uint256 ownerOffset, uint256 ownerLength) = _utf(caller.cp[ownerNameIndex]);
        (bool ownerFound, uint256 symbolicOwner) = _findClass(
            classes, caller.data, ownerOffset, ownerLength
        );
        if (!ownerFound) revert LinkError(4, pc);
        symbolic = symbolicOwner;
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert FieldError(4, pc);
        }

        if (cache[refIndex] != 0) {
            owner = (cache[refIndex] >> 128) - 1;
            field = uint128(cache[refIndex]) - 1;
        } else {
            uint256 nat = caller.cp[nameAndTypeIndex];
            uint256 nameIndex = (nat >> 8) & 0xffff;
            uint256 descriptorIndex = (nat >> 24) & 0xffff;
            if (
                nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
                    || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
                    || uint8(caller.cp[descriptorIndex]) != 1
            ) revert FieldError(1, pc);
            (uint256 nameOffset, uint256 nameLength) = _utf(caller.cp[nameIndex]);
            (uint256 descriptorOffset, uint256 descriptorLength) = _utf(caller.cp[descriptorIndex]);
            uint256 declaring = symbolic;
            uint256 foundPlusOne;
            while (true) {
                ClassInfo memory target = classes[declaring];
                for (uint256 i = 0; i < target.fields.length; ++i) {
                    FieldInfo memory candidate = target.fields[i];
                    if (candidate.nameIndex == 0 || candidate.nameIndex >= target.cp.length
                        || uint8(target.cp[candidate.nameIndex]) != 1
                        || candidate.descriptorIndex == 0
                        || candidate.descriptorIndex >= target.cp.length
                        || uint8(target.cp[candidate.descriptorIndex]) != 1) continue;
                    (uint256 candidateNameOffset, uint256 candidateNameLength) =
                        _utf(target.cp[candidate.nameIndex]);
                    if (!_equalsCross(target.data, candidateNameOffset, candidateNameLength,
                        caller.data, nameOffset, nameLength)) continue;
                    (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                        _utf(target.cp[candidate.descriptorIndex]);
                    if (!_equalsCross(target.data, candidateDescriptorOffset, candidateDescriptorLength,
                        caller.data, descriptorOffset, descriptorLength)) continue;
                    if (foundPlusOne != 0) revert FieldError(2, pc);
                    foundPlusOne = i + 1;
                }
                if (foundPlusOne != 0) break;
                uint256 link = parentLinks[declaring];
                if (link == 0 || link == type(uint256).max) revert FieldError(2, pc);
                declaring = link - 1;
            }
            owner = declaring;
            field = foundPlusOne - 1;
            cache[refIndex] = ((owner + 1) << 128) | foundPlusOne;
        }

        FieldInfo memory resolved = classes[owner].fields[field];
        valueKind = _fieldKind(classes[owner], resolved);
        bool isStatic = (resolved.accessFlags & 0x0008) != 0;
        if (isStatic != staticAccess || valueKind == 0) revert FieldError(3, pc);
        if (!_canAccessMember(classes, callerClass, owner, resolved.accessFlags,
            parentLinks, hierarchyState)) revert FieldError(4, pc);
        if (writeAccess && (resolved.accessFlags & 0x0010) != 0 && !(privilegedWrite && callerClass == owner)) {
            revert FieldError(4, pc);
        }
    }

    function _fieldKind(ClassInfo memory c, FieldInfo memory field)
        private
        pure
        returns (uint8)
    {
        if (
            field.descriptorIndex == 0 || field.descriptorIndex >= c.cp.length
                || uint8(c.cp[field.descriptorIndex]) != 1
        ) return 0;
        (uint256 off, uint256 n) = _utf(c.cp[field.descriptorIndex]);
        if (_equalsLiteral(c.data, off, n, bytes("I"))) return uint8(KIND_INT);
        (bool valid, uint256 width, uint8 kind) = _descriptorType(c.data, off, off + n, false);
        return valid && width == n ? kind : 0;
    }

    function _classAccessible(ClassInfo memory caller, ClassInfo memory symbolic)
        private
        pure
        returns (bool)
    {
        return (symbolic.accessFlags & 0x0001) != 0 || _samePackage(caller, symbolic);
    }

    function _canAccessMember(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 declaringClass,
        uint16 memberAccess,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (bool) {
        if (callerClass == declaringClass) return true;
        if ((memberAccess & 0x0002) != 0) return false;
        if ((memberAccess & 0x0001) != 0) return true;
        if (_samePackage(classes[callerClass], classes[declaringClass])) return true;
        if ((memberAccess & 0x0004) == 0) return false;
        _validateHierarchy(classes, callerClass, parentLinks, hierarchyState);
        uint256 current = callerClass;
        while (parentLinks[current] != 0 && parentLinks[current] != type(uint256).max) {
            current = parentLinks[current] - 1;
            if (current == declaringClass) return true;
        }
        return false;
    }

    function _requireProtectedReceiver(
        ClassInfo[] memory classes, uint256 callerClass, uint256 declaringClass, uint16 access,
        uint256 dynamicReceiverClass, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        if ((access & 0x0004) == 0 || callerClass == declaringClass
            || _samePackage(classes[callerClass], classes[declaringClass])) return;
        if (!_objectIsClass(dynamicReceiverClass, callerClass, parentLinks)) {
            revert FieldError(4, pc);
        }
    }

    function _samePackage(ClassInfo memory a, ClassInfo memory b) private pure returns (bool) {
        uint256 aSlash;
        uint256 bSlash;
        for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] == bytes1("/")) aSlash = i + 1;
        }
        for (uint256 i = 0; i < b.thisNameLength; ++i) {
            if (b.data[b.thisNameOffset + i] == bytes1("/")) bSlash = i + 1;
        }
        if (aSlash != bSlash) return false;
        for (uint256 i = 0; i < aSlash; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }
        return true;
    }

    function _equalsCross(
        bytes memory first,
        uint256 firstOffset,
        uint256 firstLength,
        bytes memory second,
        uint256 secondOffset,
        uint256 secondLength
    ) private pure returns (bool) {
        if (firstLength != secondLength) return false;
        for (uint256 i = 0; i < firstLength; ++i) {
            if (first[firstOffset + i] != second[secondOffset + i]) return false;
        }
        return true;
    }

    function _resolveNewClass(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (uint256 target) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert ObjectError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1) {
            revert ObjectError(1, pc);
        }
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (!_validInternalName(caller.data, off, n)) revert ObjectError(1, pc);
        (bool found, uint256 resolved) = _findClass(classes, caller.data, off, n);
        if (!found) revert LinkError(4, pc);
        target = resolved;
        _validateHierarchy(classes, target, parentLinks, hierarchyState);
        ClassInfo memory targetClass = classes[target];
        if (!_classAccessible(caller, targetClass) || (targetClass.accessFlags & 0x0400) != 0
            || (targetClass.accessFlags & 0x0200) != 0) revert ObjectError(2, pc);
    }

    function _validInternalName(bytes memory data, uint256 off, uint256 n)
        private pure returns (bool)
    {
        if (n == 0 || uint8(data[off]) == 0x5b || data[off] == bytes1("/")
            || data[off + n - 1] == bytes1("/")) return false;
        bool slash;
        for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")) return false;
            if (ch == bytes1("/")) {
                if (slash) return false;
                slash = true;
            } else slash = false;
        }
        return true;
    }

    function _instanceFieldCount(
        ClassInfo[] memory classes, uint256 classIndex, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 count) {
        uint256 current = classIndex;
        while (true) {
            ClassInfo memory c = classes[current];
            for (uint256 i = 0; i < c.fields.length; ++i) {
                if ((c.fields[i].accessFlags & 0x0008) == 0) {
                    if (_fieldKind(c, c.fields[i]) == 0) revert ObjectError(2, pc);
                    ++count;
                }
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
    }

    function _instanceFieldOffset(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 declaringClass, uint256 field,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 offset) {
        // Count declarations base-first by counting every ancestor declaration that precedes owner.
        uint256 current = dynamicClass;
        bool found;
        while (true) {
            if (current == declaringClass) { found = true; break; }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
        if (!found) revert ReferenceError(2, pc);
        current = dynamicClass;
        while (current != declaringClass) {
            uint256 link = parentLinks[current];
            current = link - 1;
        }
        // Fields of all ancestors of declaring class precede its own fields.
        uint256 ancestor = declaringClass;
        while (parentLinks[ancestor] != 0 && parentLinks[ancestor] != type(uint256).max) {
            ancestor = parentLinks[ancestor] - 1;
            ClassInfo memory a = classes[ancestor];
            for (uint256 i = 0; i < a.fields.length; ++i) {
                if ((a.fields[i].accessFlags & 0x0008) == 0) ++offset;
            }
        }
        // The loop above counts nearest-to-root in any order; only the count matters.
        ClassInfo memory declaring = classes[declaringClass];
        for (uint256 i = 0; i < field; ++i) {
            if ((declaring.fields[i].accessFlags & 0x0008) == 0) ++offset;
        }
    }

    function _objectFieldDefaults(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 fieldCount,
        uint256[] memory parentLinks
    ) private pure returns (uint256[] memory values) {
        values = new uint256[](fieldCount);
        // Layout is base-first. Walking child-to-root and each declaration in reverse lets a
        // single descending cursor fill those offsets without an O(fields^2) offset lookup.
        uint256 cursor = values.length;
        uint256 current = dynamicClass;
        while (true) {
            ClassInfo memory c = classes[current];
            for (uint256 i = c.fields.length; i != 0; --i) {
                FieldInfo memory field = c.fields[i - 1];
                if ((field.accessFlags & 0x0008) == 0) {
                    --cursor;
                    uint8 kind = _fieldKind(c, field);
                    // _instanceFieldCount already rejected unsupported instance descriptors.
                    values[cursor] = kind == KIND_INT ? _packInt(0) : _packRef(0);
                }
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
    }

    function _objectIsClass(
        uint256 dynamicClass, uint256 wantedClass, uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 current = dynamicClass;
        while (true) {
            if (current == wantedClass) return true;
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return false;
            current = link - 1;
        }
    }

    function _requireAssignable(
        ClassInfo[] memory classes, uint256 value, bytes memory descriptorData,
        uint256 descriptorOffset, uint256 descriptorLength, uint8[] memory heapKinds,
        uint256[] memory heapClasses, uint256 nextHandle, uint256[] memory parentLinks,
        uint256 pc
    ) private pure {
        _requireKind(value, KIND_REF, pc);
        uint256 handle = _payload(value);
        if (handle == 0) return;
        if (handle > nextHandle || heapKinds[handle] == 0) revert ReferenceError(1, pc);
        if (_equalsLiteral(descriptorData, descriptorOffset, descriptorLength, bytes("[I"))) {
            if (heapKinds[handle] != HEAP_ARRAY) revert ReferenceError(1, pc);
            return;
        }
        if (descriptorLength < 3 || uint8(descriptorData[descriptorOffset]) != 0x4c
            || uint8(descriptorData[descriptorOffset + descriptorLength - 1]) != 0x3b) {
            revert ReferenceError(2, pc);
        }
        uint256 nameOffset = descriptorOffset + 1;
        uint256 nameLength = descriptorLength - 2;
        if (_equalsLiteral(descriptorData, nameOffset, nameLength, bytes("java/lang/Object"))) {
            return; // both supported array and ordinary object values are Objects
        }
        if (heapKinds[handle] != HEAP_OBJECT) revert ReferenceError(1, pc);
        (bool found, uint256 wantedClass) = _findClass(classes, descriptorData, nameOffset, nameLength);
        if (!found) revert LinkError(4, pc);
        if (!_objectIsClass(heapClasses[handle], wantedClass, parentLinks)) {
            revert ReferenceError(2, pc);
        }
    }

    function _predecode(ClassInfo memory c, Selected memory s)
        private
        pure
        returns (bool[] memory starts)
    {
        starts = new bool[](s.codeLength);
        uint256 pc;
        while (pc < s.codeLength) {
            starts[pc] = true;
            uint8 op = uint8(c.data[s.codeOffset + pc]);
            uint256 width = _instructionWidth(op, pc);
            if (width > s.codeLength - pc) revert BytecodeError(2, pc);
            if (
                (op == 0xac && s.returnKind != 1) || (op == 0xb1 && s.returnKind != 2)
                    || (op == 0xb0 && s.returnKind != 3)
            ) revert CallError(5, pc);
            if (op == 0xbc && uint8(c.data[s.codeOffset + pc + 1]) != 10) {
                revert ArrayError(1, pc);
            }
            if (op == 0x12 || op == 0x13) {
                uint256 index = op == 0x12
                    ? uint8(c.data[s.codeOffset + pc + 1])
                    : _unsigned16(c.data, s.codeOffset + pc + 1);
                if (index == 0 || index >= c.cp.length || uint8(c.cp[index]) != 3) {
                    revert BytecodeError(13, pc);
                }
            }
            pc += width;
        }
        pc = 0;
        while (pc < s.codeLength) {
            uint8 op = uint8(c.data[s.codeOffset + pc]);
            uint256 width = _instructionWidth(op, pc);
            if ((op >= 0x99 && op <= 0xa7) || op == 0xc6 || op == 0xc7) {
                uint256 target = _decodedTarget(c.data, s.codeOffset, pc);
                if (target >= s.codeLength || !starts[target]) revert BytecodeError(12, pc);
            }
            pc += width;
        }
    }

    function _instructionWidth(uint8 op, uint256 pc) private pure returns (uint256) {
        if (
            op <= 0x01 || (op >= 0x02 && op <= 0x08) || (op >= 0x1a && op <= 0x1d)
                || (op >= 0x2a && op <= 0x2e) || (op >= 0x3b && op <= 0x3e)
                || (op >= 0x4b && op <= 0x4f) || (op >= 0x57 && op <= 0x60)
                || op == 0x64 || op == 0x68 || op == 0x6c || op == 0x70 || op == 0x74
                || op == 0x78 || op == 0x7a || op == 0x7c || op == 0x7e || op == 0x80
                || op == 0x82 || (op >= 0x91 && op <= 0x93) || op == 0xac
                || op == 0xb0 || op == 0xb1 || op == 0xbe
        ) return 1;
        if (op == 0x10 || op == 0x12 || op == 0x15 || op == 0x19 || op == 0x36
            || op == 0x3a || op == 0xbc) return 2;
        if (
            op == 0x11 || op == 0x13 || op == 0x84 || (op >= 0x99 && op <= 0xa7)
                || op == 0xb2 || op == 0xb3 || op == 0xb4 || op == 0xb5
                || op == 0xb7 || op == 0xb8 || op == 0xbb || op == 0xc6 || op == 0xc7
        ) return 3;
        revert BytecodeError(6, pc);
    }

    function _readCode(bytes memory data, uint256 start, uint256 length, Selected memory s)
        private
        pure
    {
        if (start > type(uint256).max - length || start + length > data.length) {
            revert ClassError(6, start);
        }
        Reader memory r = Reader(data, start);
        uint256 end = start + length;
        s.maxStack = _u2Bounded(r, end);
        s.maxLocals = _u2Bounded(r, end);
        uint256 codeLength = _u4Bounded(r, end);
        if (codeLength == 0 || codeLength > MAX_CODE || codeLength > end - r.pos) {
            revert ClassError(7, r.pos);
        }
        s.codeOffset = r.pos;
        s.codeLength = codeLength;
        r.pos += codeLength;
        uint256 exceptionCount = _u2Bounded(r, end);
        if (exceptionCount != 0) revert MethodError(8);
        uint256 nestedCount = _u2Bounded(r, end);
        for (uint256 i = 0; i < nestedCount; ++i) {
            _u2Bounded(r, end);
            uint256 n = _u4Bounded(r, end);
            if (n > end - r.pos) revert ClassError(8, r.pos);
            r.pos += n;
        }
        if (r.pos != end) revert ClassError(9, r.pos);
    }

    function _readCallCode(bytes memory data, uint256 start, uint256 length, Selected memory s)
        private
        pure
        returns (bool)
    {
        if (start > data.length || length > data.length - start || length < 8) return false;
        uint256 end = start + length;
        uint256 p = start;
        s.maxStack = _unsigned16(data, p); p += 2;
        s.maxLocals = _unsigned16(data, p); p += 2;
        uint256 codeLength = _unsigned32(data, p); p += 4;
        if (codeLength == 0 || codeLength > MAX_CODE || codeLength > end - p) return false;
        s.codeOffset = p;
        s.codeLength = codeLength;
        p += codeLength;
        if (end - p < 2) return false;
        uint256 exceptionCount = _unsigned16(data, p); p += 2;
        if (exceptionCount != 0 || end - p < 2) return false;
        uint256 nestedCount = _unsigned16(data, p); p += 2;
        for (uint256 i = 0; i < nestedCount; ++i) {
            if (end - p < 6) return false;
            p += 2;
            uint256 n = _unsigned32(data, p); p += 4;
            if (n > end - p) return false;
            p += n;
        }
        return p == end;
    }

    function _descriptor(bytes memory data, uint256 off, uint256 n, Selected memory s)
        private
        pure
        returns (bool)
    {
        if (n < 3 || off > data.length || n > data.length - off || uint8(data[off]) != 0x28) {
            return false;
        }
        uint256 i = 1;
        uint256 count;
        while (i < n && uint8(data[off + i]) != 0x29) {
            (bool ok, uint256 width,) = _descriptorType(data, off + i, off + n, false);
            if (!ok) return false;
            i += width;
            ++count;
        }
        if (i >= n || uint8(data[off + i]) != 0x29) return false;
        uint256 close = i;
        s.argumentKinds = new uint8[](count);
        s.argumentTypeOffsets = new uint256[](count);
        s.argumentTypeLengths = new uint256[](count);
        i = 1;
        uint256 at;
        while (i < close) {
            (bool ok, uint256 width, uint8 kind) = _descriptorType(data, off + i, off + close, false);
            if (!ok) return false;
            s.argumentKinds[at] = kind;
            s.argumentTypeOffsets[at] = off + i;
            s.argumentTypeLengths[at] = width;
            i += width;
            ++at;
        }
        uint256 resultOff = off + close + 1;
        if (resultOff >= off + n) return false;
        if (resultOff + 1 == off + n && uint8(data[resultOff]) == 0x49) s.returnKind = 1;
        else if (resultOff + 1 == off + n && uint8(data[resultOff]) == 0x56) s.returnKind = 2;
        else {
            (bool ok, uint256 width, uint8 kind) = _descriptorType(data, resultOff, off + n, false);
            if (!ok || kind != KIND_REF || resultOff + width != off + n) return false;
            s.returnKind = 3;
            s.returnTypeOffset = resultOff;
            s.returnTypeLength = width;
        }
        return true;
    }

    function _descriptorType(bytes memory data, uint256 off, uint256 end, bool allowVoid)
        private
        pure
        returns (bool ok, uint256 width, uint8 kind)
    {
        if (off >= end) return (false, 0, 0);
        uint8 b = uint8(data[off]);
        if (b == 0x49) return (true, 1, uint8(KIND_INT));
        if (allowVoid && b == 0x56) return (true, 1, 0);
        if (b == 0x5b && off + 2 <= end && uint8(data[off + 1]) == 0x49) {
            return (true, 2, uint8(KIND_REF));
        }
        if (b == 0x4c) {
            uint256 i = off + 1;
            while (i < end && uint8(data[i]) != 0x3b) {
                uint8 ch = uint8(data[i]);
                if (ch == 0x2e || ch == 0x5b || ch == 0x3b || ch == 0) return (false, 0, 0);
                ++i;
            }
            if (i == off + 1 || i >= end) return (false, 0, 0);
            return (true, i - off + 1, uint8(KIND_REF));
        }
        return (false, 0, 0);
    }

    function _className(ClassInfo memory c, uint256 classIndex, uint256 at)
        private
        pure
        returns (uint256, uint256)
    {
        if (classIndex == 0 || classIndex >= c.cp.length || uint8(c.cp[classIndex]) != 7) {
            revert ClassError(10, at);
        }
        uint256 nameIndex = (c.cp[classIndex] >> 8) & 0xffff;
        _validUtf8(nameIndex, c.cp, at);
        return _utf(c.cp[nameIndex]);
    }

    function _methodCodeCount(uint256 meta) private pure returns (uint256) {
        return meta >> 144;
    }

    function _utf(uint256 packed) private pure returns (uint256 off, uint256 n) {
        off = (packed >> 8) & 0xffffffffffffffff;
        n = (packed >> 72) & 0xffffffffffffffff;
    }

    function _validUtf8(uint256 index, uint256[] memory cp, uint256 at) private pure {
        if (index == 0 || index >= cp.length || uint8(cp[index]) != 1) revert ClassError(10, at);
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

    function _unsigned32(bytes memory data, uint256 off) private pure returns (uint32) {
        return (uint32(uint8(data[off])) << 24) | (uint32(uint8(data[off + 1])) << 16)
            | (uint32(uint8(data[off + 2])) << 8) | uint32(uint8(data[off + 3]));
    }

    function _packInt(uint32 value) private pure returns (uint256) {
        return (KIND_INT << KIND_SHIFT) | uint256(value);
    }

    function _packRef(uint32 handle) private pure returns (uint256) {
        return (KIND_REF << KIND_SHIFT) | uint256(handle);
    }

    function _payload(uint256 value) private pure returns (uint256) {
        return uint32(value);
    }

    function _valueKind(uint256 value) private pure returns (uint256) {
        return value >> KIND_SHIFT;
    }

    function _requireKind(uint256 value, uint256 wanted, uint256 pc) private pure {
        if (_valueKind(value) != wanted) revert BytecodeError(14, pc);
    }

    function _requireIntPair(uint256[] memory stack, uint256 sp, uint256 pc) private pure {
        _requireKind(stack[sp - 2], KIND_INT, pc);
        _requireKind(stack[sp - 1], KIND_INT, pc);
    }

    function _requireHeapKind(
        uint256 handle, uint8[] memory heapKinds, uint256 nextHandle, uint8 wanted, uint256 pc
    ) private pure {
        if (handle == 0 || handle > nextHandle || heapKinds[handle] != wanted) {
            revert ReferenceError(1, pc);
        }
    }

    function _validatePackedRef(
        uint256 value, uint8[] memory heapKinds, uint256 nextHandle, uint256 pc
    ) private pure {
        _requireKind(value, KIND_REF, pc);
        uint256 handle = _payload(value);
        if (handle != 0 && (handle > nextHandle || heapKinds[handle] == 0)) {
            revert ReferenceError(1, pc);
        }
    }

    function _throwJava(uint256 kind, Frame[] memory frames, uint256 depth) private pure {
        if (kind != 2 && kind != 7 && _hasActiveInitializer(frames, depth)) {
            revert JavaException(3);
        }
        revert JavaException(kind);
    }

    function _push(uint256[] memory stack, uint256 sp, uint256 value, uint256 pc)
        private
        pure
        returns (uint256)
    {
        if (sp >= stack.length) revert BytecodeError(9, pc);
        stack[sp] = value;
        return sp + 1;
    }

    function _loadKind(
        uint256[] memory stack,
        uint256 sp,
        uint256[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 wantedKind,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], wantedKind, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeKind(
        uint256[] memory stack,
        uint256 sp,
        uint256[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 wantedKind,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        _requireKind(stack[sp - 1], wantedKind, pc);
        locals[local] = stack[sp - 1];
        initialized[local] = true;
        return sp - 1;
    }

    function _loadReference(
        uint256[] memory stack, uint256 sp, uint256[] memory locals, bool[] memory initialized,
        uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        uint256 kind = _valueKind(locals[local]);
        if (kind != KIND_REF && kind != KIND_UNINIT) revert BytecodeError(14, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeReference(
        uint256[] memory stack, uint256 sp, uint256[] memory locals, bool[] memory initialized,
        uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        uint256 kind = _valueKind(stack[sp - 1]);
        if (kind != KIND_REF && kind != KIND_UNINIT) revert BytecodeError(14, pc);
        locals[local] = stack[sp - 1];
        initialized[local] = true;
        return sp - 1;
    }

    function _initializeAliases(Frame memory f, uint256 handle) private pure {
        uint256 uninitialized = (KIND_UNINIT << KIND_SHIFT) | handle;
        uint256 initializedRef = _packRef(uint32(handle));
        for (uint256 i = 0; i < f.sp; ++i) {
            if (f.stack[i] == uninitialized) f.stack[i] = initializedRef;
        }
        for (uint256 i = 0; i < f.locals.length; ++i) {
            if (f.initialized[i] && f.locals[i] == uninitialized) f.locals[i] = initializedRef;
        }
    }

    function _permuteCategory1(uint256[] memory stack, uint256 sp, uint8 op, uint256 pc)
        private
        pure
        returns (uint256)
    {
        if (op == 0x58) { // pop2
            if (sp < 2) revert BytecodeError(3, pc);
            return sp - 2;
        }
        if (op == 0x59) { // dup
            if (sp == 0) revert BytecodeError(3, pc);
            return _push(stack, sp, stack[sp - 1], pc);
        }
        uint256 need = (op == 0x5a || op == 0x5c || op == 0x5f) ? 2
            : (op == 0x5b || op == 0x5d ? 3 : 4);
        if (sp < need) revert BytecodeError(3, pc);
        if (op == 0x5f) { // swap
            (stack[sp - 2], stack[sp - 1]) = (stack[sp - 1], stack[sp - 2]);
            return sp;
        }
        uint256 extra = op == 0x5a || op == 0x5b ? 1 : 2;
        if (extra > stack.length - sp) revert BytecodeError(9, pc);
        if (op == 0x5a) { // dup_x1: ..., v2, v1 -> ..., v1, v2, v1
            uint256 v1 = stack[sp - 1];
            stack[sp] = v1;
            stack[sp - 1] = stack[sp - 2];
            stack[sp - 2] = v1;
        } else if (op == 0x5b) { // dup_x2: ..., v3, v2, v1 -> ..., v1, v3, v2, v1
            uint256 v1 = stack[sp - 1];
            stack[sp] = v1;
            stack[sp - 1] = stack[sp - 2];
            stack[sp - 2] = stack[sp - 3];
            stack[sp - 3] = v1;
        } else if (op == 0x5c) { // dup2
            stack[sp] = stack[sp - 2];
            stack[sp + 1] = stack[sp - 1];
        } else if (op == 0x5d) { // dup2_x1
            uint256 v2 = stack[sp - 2];
            uint256 v1 = stack[sp - 1];
            stack[sp + 1] = v1;
            stack[sp] = v2;
            stack[sp - 1] = stack[sp - 3];
            stack[sp - 2] = v1;
            stack[sp - 3] = v2;
        } else { // dup2_x2
            uint256 v2 = stack[sp - 2];
            uint256 v1 = stack[sp - 1];
            stack[sp + 1] = v1;
            stack[sp] = v2;
            stack[sp - 1] = stack[sp - 3];
            stack[sp - 2] = stack[sp - 4];
            stack[sp - 3] = v1;
            stack[sp - 4] = v2;
        }
        return sp + extra;
    }

    function _unaryCondition(uint8 op, int32 value) private pure returns (bool) {
        if (op == 0x99) return value == 0;
        if (op == 0x9a) return value != 0;
        if (op == 0x9b) return value < 0;
        if (op == 0x9c) return value >= 0;
        if (op == 0x9d) return value > 0;
        return value <= 0;
    }

    function _binaryCondition(uint8 op, int32 left, int32 right) private pure returns (bool) {
        if (op == 0x9f) return left == right;
        if (op == 0xa0) return left != right;
        if (op == 0xa1) return left < right;
        if (op == 0xa2) return left >= right;
        if (op == 0xa3) return left > right;
        return left <= right;
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

    function _equalsSlice(
        bytes memory data,
        uint256 firstOffset,
        uint256 firstLength,
        uint256 secondOffset,
        uint256 secondLength
    ) private pure returns (bool) {
        if (firstLength != secondLength) return false;
        for (uint256 i = 0; i < firstLength; ++i) {
            if (data[firstOffset + i] != data[secondOffset + i]) return false;
        }
        return true;
    }

    function _equalsLiteral(bytes memory data, uint256 off, uint256 n, bytes memory literal)
        private
        pure
        returns (bool)
    {
        return _equals(data, off, n, literal);
    }

    function _readFields(Reader memory r, ClassInfo memory c)
        private
        pure
        returns (FieldInfo[] memory fields)
    {
        uint256 count = _u2(r);
        fields = new FieldInfo[](count);
        for (uint256 i = 0; i < count; ++i) {
            uint16 access = _u2(r);
            uint16 nameIndex = _u2(r);
            uint16 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            FieldInfo memory field;
            field.accessFlags = access;
            field.nameIndex = nameIndex;
            field.descriptorIndex = descriptorIndex;
            uint8 supportedKind;
            if (
                (access & 0x0008) != 0 && descriptorIndex != 0
                    && descriptorIndex < c.cp.length && uint8(c.cp[descriptorIndex]) == 1
            ) {
                (uint256 descriptorOffset, uint256 descriptorLength) = _utf(c.cp[descriptorIndex]);
                if (_equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("I"))) {
                    supportedKind = uint8(KIND_INT);
                } else {
                    (bool valid, uint256 width, uint8 kind) = _descriptorType(
                        c.data, descriptorOffset, descriptorOffset + descriptorLength, false
                    );
                    if (valid && width == descriptorLength) supportedKind = kind;
                }
            }
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                bool isConstantValue;
                if (
                    attributeNameIndex != 0 && attributeNameIndex < c.cp.length
                        && uint8(c.cp[attributeNameIndex]) == 1
                ) {
                    (uint256 attributeNameOffset, uint256 attributeNameLength) =
                        _utf(c.cp[attributeNameIndex]);
                    isConstantValue = _equalsLiteral(
                        c.data, attributeNameOffset, attributeNameLength, bytes("ConstantValue")
                    );
                }
                if (supportedKind != 0 && isConstantValue) {
                    if (supportedKind != KIND_INT || field.hasConstant || attributeLength != 2) {
                        revert FieldError(5, i);
                    }
                    uint256 constantIndex = _u2(r);
                    if (
                        constantIndex == 0 || constantIndex >= c.cp.length
                            || uint8(c.cp[constantIndex]) != 3
                    ) revert FieldError(5, i);
                    field.hasConstant = true;
                    field.constantValue = uint32(c.cp[constantIndex] >> 8);
                } else {
                    _skip(r, attributeLength);
                }
            }
            fields[i] = field;
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

    function _checkedMul2(uint256 n, uint256 at) private pure returns (uint256) {
        if (n > type(uint256).max / 2) revert ClassError(11, at);
        return n * 2;
    }

    function _skip(Reader memory r, uint256 n) private pure {
        if (r.pos > r.data.length || n > r.data.length - r.pos) revert ClassError(12, r.pos);
        r.pos += n;
    }

    function _u1(Reader memory r) private pure returns (uint8 v) {
        if (r.pos >= r.data.length) revert ClassError(12, r.pos);
        v = uint8(r.data[r.pos]);
        ++r.pos;
    }

    function _u2(Reader memory r) private pure returns (uint16 v) {
        if (r.pos > r.data.length || r.data.length - r.pos < 2) revert ClassError(12, r.pos);
        v = (uint16(uint8(r.data[r.pos])) << 8) | uint16(uint8(r.data[r.pos + 1]));
        r.pos += 2;
    }

    function _u4(Reader memory r) private pure returns (uint32 v) {
        if (r.pos > r.data.length || r.data.length - r.pos < 4) revert ClassError(12, r.pos);
        v = _unsigned32(r.data, r.pos);
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

    function _bootstrapObject() private pure returns (bytes memory) {
        return hex"cafebabe0000003400060700020100106a6176612f6c616e672f4f626a6563740100063c696e69743e010003282956010004436f6465002100010000000000000001000100030004000100050000000d0000000100000001b1000000000000";
    }
}
