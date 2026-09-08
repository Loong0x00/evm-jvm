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
    error TypeError(uint256 code, uint256 pc);
    error InterfaceError(uint256 code, uint256 location);

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
    // A runtime value is a 64-bit payload plus an internal kind. Category-2 longs
    // remain one indivisible EVM value, while stack/local capacity is charged in
    // JVM words by the helpers below.
    uint256 private constant KIND_SHIFT = 64;
    uint256 private constant KIND_INT = 1;
    uint256 private constant KIND_REF = 2;
    uint256 private constant KIND_UNINIT = 3;
    uint256 private constant KIND_LONG = 4;
    uint256 private constant KIND_LONG_TAIL = 5;
    uint256 private constant KIND_FLOAT = 6;
    uint256 private constant KIND_DOUBLE = 7;
    uint256 private constant KIND_DOUBLE_TAIL = 8;
    uint8 private constant HEAP_ARRAY = 1;
    uint8 private constant HEAP_OBJECT = 2;
    uint8 private constant PRIMITIVE_BYTE = 0x42; // B
    uint8 private constant PRIMITIVE_CHAR = 0x43; // C
    uint8 private constant PRIMITIVE_DOUBLE = 0x44; // D
    uint8 private constant PRIMITIVE_FLOAT = 0x46; // F
    uint8 private constant PRIMITIVE_INT = 0x49; // I
    uint8 private constant PRIMITIVE_LONG = 0x4a; // J
    uint8 private constant PRIMITIVE_SHORT = 0x53; // S
    uint8 private constant PRIMITIVE_BOOLEAN = 0x5a; // Z
    // Primitive array leaves use their descriptor byte. Reference leaves are kept
    // in a disjoint namespace so no zero/default class id can alias int[].
    uint256 private constant ARRAY_CLASS_BASE = 0x100;

    // Array types are represented without synthetic host classes: rank 1..255 and an
    // explicit ultimate primitive descriptor or ARRAY_CLASS_BASE + class index.
    struct ArrayType {
        uint8 rank;
        uint256 leafType;
    }

    struct MultiArrayPlan {
        uint256[] counts;
        uint256 arrays;
        uint256 elements;
    }

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
        uint256 argumentWords;
        uint8[] argumentKinds;
        uint256[] argumentTypeOffsets;
        uint256[] argumentTypeLengths;
        uint8 returnKind; // 1=int, 2=void, 3=reference, 4=long, 5=float, 6=double
        uint8 returnSubtype; // exact I/Z/B/C/S descriptor for computational-int returns
        uint256 returnTypeOffset;
        uint256 returnTypeLength;
    }

    struct FieldInfo {
        uint16 accessFlags;
        uint16 nameIndex;
        uint16 descriptorIndex;
        bool hasConstant;
        uint64 constantValue;
    }

    struct ClassInfo {
        bytes data;
        // One packed word per CP slot. Low byte is the tag. Utf8 stores offset/length,
        // Integer stores its 32 bits, and reference entries store their u2 operands.
        uint256[] cp;
        FieldInfo[] fields;
        // One packed word per method: flags/name/descriptor and lazy Code attribute location.
        uint256[] methods;
        // Constant-pool Class indices for direct interfaces, in classfile order.
        uint16[] interfaces;
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
        uint256[] stack; // low 64 bits payload, kind above it; long is one value/two words
        uint256[] locals;
        bool[] initialized;
        bool isInitializer;
        bool isInitContinuation;
        bool isConstructor;
        bool isConstructorLinked;
        uint256 thisHandle;
    }

    struct VirtualResolution {
        uint256 owner;
        uint256 method;
        uint256 symbolic;
        uint256 referenceClass;
        uint256 nameOffset;
        uint256 nameLength;
        uint256 descriptorOffset;
        uint256 descriptorLength;
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
        if ((classAccess & 0x0200) == 0 && (classAccess & 0xe000) != 0) {
            c.unsupportedSemantics = true;
        }
        uint256 thisClass = _u2(r);
        uint256 superClass = _u2(r);
        (c.thisNameOffset, c.thisNameLength) = _className(c, thisClass, r.pos);
        if (superClass != 0) {
            (c.superNameOffset, c.superNameLength) = _className(c, superClass, r.pos);
            c.hasSuperclass = true;
        }

        uint256 interfacesCount = _u2(r);
        c.interfaces = new uint16[](interfacesCount);
        for (uint256 i = 0; i < interfacesCount; ++i) c.interfaces[i] = _u2(r);
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
        if (!_isExactIntRoot(c, selected[root])) revert MethodError(11);
        if (args.length != selected[root].argumentCount) revert MethodError(9);
        if (selected[root].maxLocals < selected[root].argumentWords) revert MethodError(10);

        // CP ref -> resolved class/method avoids repeated scans during recursion. A real minimal
        // Object classfile is appended and parsed normally unless this input is Object itself.
        uint256[] memory referenceCache = new uint256[](c.cp.length);
        _predecode(c, selected[root]);
        bool suppliedObject = _isObjectClass(c);
        bool suppliedCloneable = _isNamedClass(c, bytes("java/lang/Cloneable"));
        bool suppliedSerializable = _isNamedClass(c, bytes("java/io/Serializable"));
        bool suppliedFloat = _isNamedClass(c, bytes("java/lang/Float"));
        bool suppliedDouble = _isNamedClass(c, bytes("java/lang/Double"));
        uint256 classCount = 1 + (suppliedObject ? 0 : 1)
            + (suppliedCloneable ? 0 : 1) + (suppliedSerializable ? 0 : 1)
            + (suppliedFloat ? 0 : 1) + (suppliedDouble ? 0 : 1);
        ClassInfo[] memory classes = new ClassInfo[](classCount);
        classes[0] = c;
        uint256 bootstrapAt = 1;
        if (!suppliedObject) classes[bootstrapAt++] = _parseBundleClass(_bootstrapObject());
        if (!suppliedCloneable) classes[bootstrapAt++] = _parseBundleClass(_bootstrapCloneable());
        if (!suppliedSerializable) classes[bootstrapAt++] = _parseBundleClass(_bootstrapSerializable());
        if (!suppliedFloat) classes[bootstrapAt++] = _parseBundleClass(_bootstrapFloat());
        if (!suppliedDouble) classes[bootstrapAt] = _parseBundleClass(_bootstrapDouble());
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
        bool suppliedCloneable;
        bool suppliedSerializable;
        bool suppliedFloat;
        bool suppliedDouble;
        bytes memory wantedClass = bytes(entryClass);
        for (uint256 i = 0; i < inputCount; ++i) {
            users[i] = _parseBundleClass(rawClasses[i]);
            for (uint256 j = 0; j < i; ++j) {
                if (_sameClassName(users[i], users[j])) revert LinkError(2, i);
            }
            if (_isObjectClass(users[i])) suppliedObject = true;
            if (_isNamedClass(users[i], bytes("java/lang/Cloneable"))) suppliedCloneable = true;
            if (_isNamedClass(users[i], bytes("java/io/Serializable"))) suppliedSerializable = true;
            if (_isNamedClass(users[i], bytes("java/lang/Float"))) suppliedFloat = true;
            if (_isNamedClass(users[i], bytes("java/lang/Double"))) suppliedDouble = true;
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
        uint256 count = inputCount + (suppliedObject ? 0 : 1)
            + (suppliedCloneable ? 0 : 1) + (suppliedSerializable ? 0 : 1)
            + (suppliedFloat ? 0 : 1) + (suppliedDouble ? 0 : 1);
        ClassInfo[] memory classes = new ClassInfo[](count);
        for (uint256 i = 0; i < inputCount; ++i) classes[i] = users[i];
        uint256 bootstrapAt = inputCount;
        if (!suppliedObject) classes[bootstrapAt++] = _parseBundleClass(_bootstrapObject());
        if (!suppliedCloneable) classes[bootstrapAt++] = _parseBundleClass(_bootstrapCloneable());
        if (!suppliedSerializable) classes[bootstrapAt++] = _parseBundleClass(_bootstrapSerializable());
        if (!suppliedFloat) classes[bootstrapAt++] = _parseBundleClass(_bootstrapFloat());
        if (!suppliedDouble) classes[bootstrapAt] = _parseBundleClass(_bootstrapDouble());
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
        if (!_isExactIntRoot(classes[rootClass], rootSelection)) revert MethodError(11);
        if (args.length != rootSelection.argumentCount) revert MethodError(9);
        if (rootSelection.maxLocals < rootSelection.argumentWords) revert MethodError(10);
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
        if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xe000) != 0) {
            c.unsupportedSemantics = true;
        }

        uint256 interfacesCount = _u2(r);
        c.interfaces = new uint16[](interfacesCount);
        for (uint256 i = 0; i < interfacesCount; ++i) c.interfaces[i] = _u2(r);
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

    function _isNamedClass(ClassInfo memory c, bytes memory name) private pure returns (bool) {
        return _equalsLiteral(c.data, c.thisNameOffset, c.thisNameLength, name);
    }

    function _isInterface(ClassInfo memory c) private pure returns (bool) {
        return (c.accessFlags & 0x0200) != 0;
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
                cp[i] = uint256(tag) | (high << 40) | (low << 8);
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
            || !_isExactIntRoot(c, s)) revert MethodError(11);
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
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS || s.maxLocals < s.argumentWords) {
            revert CallError(4, callPC);
        }
        s.loaded = true;
    }

    function _nativeBinding(ClassInfo memory c, uint256 method)
        private pure returns (uint8)
    {
        uint256 meta = c.methods[method];
        if ((uint16(meta) & 0x0100) == 0) return 0; // ordinary Code always wins
        (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 descriptorOffset, uint256 descriptorLength) =
            _utf(c.cp[(meta >> 32) & 0xffff]);
        if (_isNamedClass(c, bytes("java/lang/Float"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("intBitsToFloat"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(I)F"))) {
                return 1;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("floatToRawIntBits"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(F)I"))) {
                return 2;
            }
        } else if (_isNamedClass(c, bytes("java/lang/Double"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("longBitsToDouble"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(J)D"))) {
                return 3;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("doubleToRawLongBits"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)J"))) {
                return 4;
            }
        }
        return 0;
    }

    function _validateNativeBinding(ClassInfo memory c, uint256 method, uint256 callPC)
        private pure
    {
        uint16 access = uint16(c.methods[method]);
        if ((access & 0x0109) != 0x0109 || (access & (0x0002 | 0x0004 | 0x0020 | 0x0400)) != 0
            || _methodCodeCount(c.methods[method]) != 0) revert CallError(4, callPC);
    }

    function _loadNativeCallee(ClassInfo memory c, uint256 method, uint256 callPC)
        private pure returns (Selected memory s)
    {
        _validateNativeBinding(c, method, callPC);
        uint256 meta = c.methods[method];
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.argumentKinds.length != 1 || s.argumentWords > MAX_LOCALS) {
            revert CallError(4, callPC);
        }
        s.argumentCount = 1;
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
                else if (fieldKind == KIND_LONG) staticValues[i][j] = _packLong(0);
                else if (fieldKind == KIND_FLOAT) staticValues[i][j] = _packFloat(0);
                else if (fieldKind == KIND_DOUBLE) staticValues[i][j] = _packDouble(0);
            }
        }
        // Arrays and objects share one one-based, unforgeable handle namespace. The independent
        // logical limits still apply, while the outer tables remain lazy for scalar-only programs.
        // Full-width discriminated cells: primitive long arrays use all 64 bits;
        // metadata prevents int/reference cells from being reinterpreted as longs.
        uint64[][] memory arrayHeap;
        uint256[][] memory objectHeap;
        uint8[] memory heapKinds;
        uint256[] memory heapClasses;
        uint8[] memory arrayRanks;
        uint256[] memory arrayLeafTypes;
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
                // JVMS 5.5 initializes default-declaring superinterfaces only as
                // prerequisites of an ordinary class. The traversal is repeated after
                // each prerequisite returns; initializationState both deduplicates
                // diamonds and makes reentrant requests harmless.
                if (!_isInterface(initializing)) {
                    (bool hasDefaultPrerequisite, uint256 defaultPrerequisite) =
                        _nextDefaultInterface(classes, initializingClass, initializationState);
                    if (hasDefaultPrerequisite) {
                        depth = _initializeClass(
                            classes, staticValues, initializationState, frames, depth,
                            defaultPrerequisite, parentLinks, hierarchyState
                        );
                        continue;
                    }
                }
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
            // Keep the common compiler-emitted local increment near dispatch entry.
            // This is still one ordinary JVM instruction per interpreter iteration;
            // it only avoids traversing unrelated arithmetic dispatch branches.
            if (op == 0x84) { // iinc
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
            } else if (op == 0x00) { // nop
                continue;
            } else if (op == 0x01) { // aconst_null
                f.sp = _push(f.stack, f.sp, _packRef(0), opPC);
            } else if (op >= 0x02 && op <= 0x08) { // iconst_m1 ... iconst_5
                uint32 value = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                f.sp = _push(f.stack, f.sp, _packInt(value), opPC);
            } else if (op == 0x09 || op == 0x0a) { // lconst_0, lconst_1
                f.sp = _push(f.stack, f.sp, _packLong(uint64(op - 0x09)), opPC);
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
            } else if (op == 0x12 || op == 0x13) { // ldc / ldc_w, Integer or Float
                uint256 index;
                if (op == 0x12) {
                    index = uint8(c.data[selection.codeOffset + f.pc]);
                    ++f.pc;
                } else {
                    index = _unsigned16(c.data, selection.codeOffset + f.pc);
                    f.pc += 2;
                }
                if (index == 0 || index >= c.cp.length) revert BytecodeError(13, opPC);
                uint8 tag = uint8(c.cp[index]);
                if (tag != 3 && tag != 4) revert BytecodeError(13, opPC);
                f.sp = _push(f.stack, f.sp, tag == 3
                    ? _packInt(uint32(c.cp[index] >> 8))
                    : _packFloat(uint32(c.cp[index] >> 8)), opPC);
            } else if (op == 0x14) { // ldc2_w (CONSTANT_Long or Double)
                uint256 index = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                if (index == 0 || index >= c.cp.length) revert BytecodeError(13, opPC);
                uint8 tag = uint8(c.cp[index]);
                if (tag != 5 && tag != 6) revert BytecodeError(13, opPC);
                f.sp = _push(f.stack, f.sp, tag == 5
                    ? _packLong(uint64(c.cp[index] >> 8))
                    : _packDouble(uint64(c.cp[index] >> 8)), opPC);
            } else if (op >= 0x15 && op <= 0x19) { // iload / lload / fload / dload / aload
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                if (op == 0x19) f.sp = _loadReference(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x16) f.sp = _loadLong(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x18) f.sp = _loadDouble(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, local,
                    op == 0x17 ? KIND_FLOAT : KIND_INT, opPC
                );
            } else if (op >= 0x1a && op <= 0x1d) { // iload_0..3
                f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x1a, KIND_INT, opPC
                );
            } else if (op >= 0x1e && op <= 0x21) { // lload_0..3
                f.sp = _loadLong(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x1e, opPC
                );
            } else if (op >= 0x2a && op <= 0x2d) { // aload_0..3
                f.sp = _loadReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x2a, opPC
                );
            } else if (op == 0x2e || op == 0x2f || (op >= 0x32 && op <= 0x35)) {
                // iaload / laload / aaload / baload / caload / saload
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint256 handle = _payload(f.stack[f.sp - 2]);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                uint8 rank = arrayRanks[handle];
                uint256 leafType = arrayLeafTypes[handle];
                bool referenceComponents = _arrayHasReferenceComponents(rank, leafType);
                bool matching = (op == 0x32 && referenceComponents)
                    || (op == 0x2e && rank == 1 && leafType == PRIMITIVE_INT)
                    || (op == 0x2f && rank == 1 && leafType == PRIMITIVE_LONG)
                    || (op == 0x33 && rank == 1
                        && (leafType == PRIMITIVE_BYTE || leafType == PRIMITIVE_BOOLEAN))
                    || (op == 0x34 && rank == 1 && leafType == PRIMITIVE_CHAR)
                    || (op == 0x35 && rank == 1 && leafType == PRIMITIVE_SHORT);
                if (!matching) revert ReferenceError(1, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    _throwJava(5, frames, depth);
                }
                uint64 cell = arrayHeap[handle][uint256(uint32(index))];
                f.stack[f.sp - 2] = op == 0x2f ? _packLong(cell)
                    : (referenceComponents
                        ? _packRef(uint32(cell))
                        : _packInt(_normalizeInt(uint32(cell), uint8(leafType))));
                --f.sp;
            } else if (op >= 0x36 && op <= 0x3a) { // istore/lstore/fstore/dstore/astore
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                if (op == 0x3a) f.sp = _storeReference(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x37) f.sp = _storeLong(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x39) f.sp = _storeDouble(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, local,
                    op == 0x38 ? KIND_FLOAT : KIND_INT, opPC
                );
            } else if (op >= 0x3b && op <= 0x3e) { // istore_0..3
                f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x3b, KIND_INT, opPC
                );
            } else if (op >= 0x3f && op <= 0x42) { // lstore_0..3
                f.sp = _storeLong(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x3f, opPC
                );
            } else if (op >= 0x4b && op <= 0x4e) { // astore_0..3
                f.sp = _storeReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x4b, opPC
                );
            } else if (op == 0x4f || op == 0x50 || (op >= 0x53 && op <= 0x56)) {
                // iastore / lastore / aastore / bastore / castore / sastore
                if (f.sp < 3) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 3], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_INT, opPC);
                _requireKind(
                    f.stack[f.sp - 1],
                    op == 0x53 ? KIND_REF : (op == 0x50 ? KIND_LONG : KIND_INT), opPC
                );
                uint256 handle = _payload(f.stack[f.sp - 3]);
                if (op == 0x53) {
                    // Constructor tokens and forged references are rejected before Java's
                    // receiver/bounds/store checks; initialized null remains a valid value.
                    _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                }
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                uint8 rank = arrayRanks[handle];
                uint256 leafType = arrayLeafTypes[handle];
                bool referenceComponents = _arrayHasReferenceComponents(rank, leafType);
                bool matching = (op == 0x53 && referenceComponents)
                    || (op == 0x4f && rank == 1 && leafType == PRIMITIVE_INT)
                    || (op == 0x50 && rank == 1 && leafType == PRIMITIVE_LONG)
                    || (op == 0x54 && rank == 1
                        && (leafType == PRIMITIVE_BYTE || leafType == PRIMITIVE_BOOLEAN))
                    || (op == 0x55 && rank == 1 && leafType == PRIMITIVE_CHAR)
                    || (op == 0x56 && rank == 1 && leafType == PRIMITIVE_SHORT);
                if (!matching) revert ReferenceError(1, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 2])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    _throwJava(5, frames, depth);
                }
                if (op == 0x53 && !_valueFitsArrayComponent(
                    classes, f.stack[f.sp - 1], rank, leafType,
                    heapKinds, heapClasses, arrayRanks, arrayLeafTypes, parentLinks
                )) _throwJava(9, frames, depth);
                uint64 stored = uint64(_payload(f.stack[f.sp - 1]));
                if (op != 0x50 && !referenceComponents) {
                    stored = uint64(_normalizeInt(uint32(stored), uint8(leafType)));
                }
                arrayHeap[handle][uint256(uint32(index))] = stored;
                f.sp -= 3;
            } else if (op == 0x57) { // pop (category 1 only)
                if (f.sp == 0) revert BytecodeError(3, opPC);
                if (!_isCategory1(f.stack[f.sp - 1])) revert BytecodeError(14, opPC);
                --f.sp;
            } else if (op >= 0x58 && op <= 0x5f) {
                f.sp = _permuteStack(f.stack, f.sp, op, opPC);
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
            } else if (op == 0x61 || op == 0x65 || op == 0x69) { // ladd/lsub/lmul
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint64 right = uint64(_payload(f.stack[f.sp - 1]));
                unchecked {
                    if (op == 0x61) left += right;
                    else if (op == 0x65) left -= right;
                    else left *= right;
                }
                f.stack[f.sp - 2] = _packLong(left);
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
            } else if (op == 0x6d || op == 0x71) { // ldiv/lrem
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                int64 dividend = int64(uint64(_payload(f.stack[f.sp - 2])));
                int64 divisor = int64(uint64(_payload(f.stack[f.sp - 1])));
                if (divisor == 0) _throwJava(1, frames, depth);
                uint64 result;
                if (dividend == type(int64).min && divisor == -1) {
                    result = op == 0x6d ? uint64(0x8000000000000000) : 0;
                } else if (op == 0x6d) result = uint64(dividend / divisor);
                else result = uint64(dividend % divisor);
                f.stack[f.sp - 2] = _packLong(result);
                --f.sp;
            } else if (op == 0x74) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                unchecked {
                    f.stack[f.sp - 1] = _packInt(uint32(0) - uint32(_payload(f.stack[f.sp - 1])));
                }
            } else if (op == 0x75) { // lneg
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                unchecked {
                    f.stack[f.sp - 1] = _packLong(uint64(0) - uint64(_payload(f.stack[f.sp - 1])));
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
            } else if (op == 0x79 || op == 0x7b || op == 0x7d) { // lshl/lshr/lushr
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_LONG, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint256 shift = _payload(f.stack[f.sp - 1]) & 63;
                if (op == 0x79) left <<= shift;
                else if (op == 0x7b) left = uint64(int64(left) >> shift);
                else left >>= shift;
                f.stack[f.sp - 2] = _packLong(left);
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
            } else if (op == 0x7f || op == 0x81 || op == 0x83) { // land/lor/lxor
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint64 right = uint64(_payload(f.stack[f.sp - 1]));
                if (op == 0x7f) left &= right;
                else if (op == 0x81) left |= right;
                else left ^= right;
                f.stack[f.sp - 2] = _packLong(left);
                --f.sp;
            } else if (op == 0x85) { // i2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int64 extended = int64(int32(uint32(_payload(f.stack[f.sp - 1]))));
                f.stack[f.sp - 1] = _packLong(uint64(extended));
                if (_stackWords(f.stack, f.sp) > f.stack.length) revert BytecodeError(9, opPC);
            } else if (op == 0x88) { // l2i
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                f.stack[f.sp - 1] = _packInt(uint32(_payload(f.stack[f.sp - 1])));
            } else if (op == 0x91 || op == 0x92 || op == 0x93) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint32 value = uint32(_payload(f.stack[f.sp - 1]));
                if (op == 0x91) value = uint32(int32(int8(uint8(value))));
                else if (op == 0x92) value = uint32(uint16(value));
                else value = uint32(int32(int16(uint16(value))));
                f.stack[f.sp - 1] = _packInt(value);
            } else if (op == 0x94) { // lcmp
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                int64 left = int64(uint64(_payload(f.stack[f.sp - 2])));
                int64 right = int64(uint64(_payload(f.stack[f.sp - 1])));
                uint32 result = left == right ? 0 : (left < right ? type(uint32).max : 1);
                f.stack[f.sp - 2] = _packInt(result);
                --f.sp;
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
            } else if (op == 0xaa || op == 0xab) { // tableswitch / lookupswitch
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int32 key = int32(uint32(_payload(f.stack[f.sp - 1])));
                --f.sp;
                f.pc = _decodedSwitchTarget(
                    c.data, selection.codeOffset, opPC, key, op == 0xab
                );
            } else if (op == 0xc4) { // wide local access / iinc
                uint8 embedded = uint8(c.data[selection.codeOffset + f.pc]);
                uint256 local = _unsigned16(c.data, selection.codeOffset + f.pc + 1);
                if (embedded >= 0x15 && embedded <= 0x19) {
                    if (embedded == 0x19) f.sp = _loadReference(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x16) f.sp = _loadLong(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x18) f.sp = _loadDouble(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else f.sp = _loadKind(
                        f.stack, f.sp, f.locals, f.initialized, local,
                        embedded == 0x17 ? KIND_FLOAT : KIND_INT, opPC
                    );
                    f.pc += 3;
                } else if (embedded >= 0x36 && embedded <= 0x3a) {
                    if (embedded == 0x3a) f.sp = _storeReference(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x37) f.sp = _storeLong(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x39) f.sp = _storeDouble(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else f.sp = _storeKind(
                        f.stack, f.sp, f.locals, f.initialized, local,
                        embedded == 0x38 ? KIND_FLOAT : KIND_INT, opPC
                    );
                    f.pc += 3;
                } else { // the predecoder admits only supported wide iinc here
                    if (local >= f.locals.length) revert BytecodeError(8, opPC);
                    if (!f.initialized[local]) revert BytecodeError(11, opPC);
                    _requireKind(f.locals[local], KIND_INT, opPC);
                    int16 amount = _signed16(c.data, selection.codeOffset + f.pc + 3);
                    unchecked {
                        f.locals[local] = _packInt(
                            uint32(_payload(f.locals[local])) + uint32(int32(amount))
                        );
                    }
                    f.pc += 5;
                }
            } else if (op == 0xc8) { // goto_w
                f.pc = _decodedWideTarget(c.data, selection.codeOffset, opPC, opPC + 1);
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
                    arrayRanks = new uint8[](MAX_HANDLES + 1);
                    arrayLeafTypes = new uint256[](MAX_HANDLES + 1);
                    arrayHeap = new uint64[][](MAX_HANDLES + 1);
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
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                    uint256 stored = f.stack[f.sp - 1];
                    if (fieldKind == KIND_INT) {
                        stored = _normalizePackedInt(
                            stored, _fieldSubtype(classes[fieldClass], classes[fieldClass].fields[field])
                        );
                    }
                    staticValues[fieldClass][field] = stored;
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
                    if (_isCategory2Kind(fieldKind)) _requireExtraWords(f.stack, f.sp, 1, opPC);
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
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                    if (fieldKind == KIND_INT) {
                        fieldValue = _normalizePackedInt(
                            fieldValue, _fieldSubtype(classes[fieldClass], classes[fieldClass].fields[field])
                        );
                    }
                    objectHeap[handle][objectOffset] = fieldValue;
                    f.sp -= 2;
                }
            } else if (op == 0xb6) { // invokevirtual
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                VirtualResolution memory resolved = _resolveVirtual(
                    classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                );
                Selected memory signature = _loadVirtualSignature(
                    classes[resolved.owner], resolved.method, opPC
                );
                if (f.sp < signature.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - signature.argumentCount - 1;
                uint256 receiver = f.stack[base];
                _requireKind(receiver, KIND_REF, opPC);
                for (uint256 i = 0; i < signature.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    _requireKind(argument, signature.argumentKinds[i], opPC);
                    if (signature.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, argument, classes[resolved.owner].data,
                            signature.argumentTypeOffsets[i], signature.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                }
                uint256 handle = _payload(receiver);
                if (handle == 0) _throwJava(6, frames, depth);
                _validatePackedRef(receiver, heapKinds, nextHandle, opPC);
                if (heapKinds[handle] == HEAP_ARRAY) {
                    // A valid array receiver is deliberately deferred after symbolic
                    // method resolution, before ordinary-object assignability/selection.
                    revert CallError(4, opPC);
                }
                if (heapKinds[handle] != HEAP_OBJECT) revert ReferenceError(1, opPC);
                uint256 dynamicClass = heapClasses[handle];
                if (!_objectIsClass(dynamicClass, resolved.symbolic, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                _requireProtectedMethodReceiver(
                    classes, f.classIndex, resolved.owner,
                    uint16(classes[resolved.owner].methods[resolved.method]), dynamicClass,
                    parentLinks, opPC
                );
                (uint256 calleeClass, uint256 callee) = _selectVirtual(
                    classes, dynamicClass, resolved, parentLinks, opPC
                );
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                if (!selected[calleeClass][callee].loaded) {
                    selected[calleeClass][callee] = _loadVirtualCallee(
                        classes[calleeClass], callee, opPC
                    );
                    _predecode(classes[calleeClass], selected[calleeClass][callee]);
                }
                Selected memory target = selected[calleeClass][callee];
                if (!_sameMethodDescriptor(classes[resolved.owner], resolved.method,
                    classes[calleeClass], callee)) revert CallError(4, opPC);
                if (depth == MAX_FRAMES) revert JavaException(2);
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = receiver;
                child.initialized[0] = true;
                _copyArguments(child, target, f.stack, base + 1, 1);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb7) { // invokespecial
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                bool interfaceSpecial = refIndex != 0 && refIndex < c.cp.length
                    && uint8(c.cp[refIndex]) == 11;
                if (interfaceSpecial) {
                    VirtualResolution memory interfaceResolved = _resolveInterfaceSpecial(
                        classes, f.classIndex, f.methodIndex, refIndex, opPC,
                        parentLinks, hierarchyState
                    );
                    Selected memory interfaceSignature = _loadVirtualSignature(
                        classes[interfaceResolved.owner], interfaceResolved.method, opPC
                    );
                    if (f.sp < interfaceSignature.argumentCount + 1) {
                        revert BytecodeError(3, opPC);
                    }
                    uint256 interfaceBase = f.sp - interfaceSignature.argumentCount - 1;
                    uint256 interfaceReceiver = f.stack[interfaceBase];
                    _requireKind(interfaceReceiver, KIND_REF, opPC);
                    if (f.locals.length == 0 || !f.initialized[0]) revert CallError(4, opPC);
                    _requireKind(f.locals[0], KIND_REF, opPC);
                    for (uint256 i = 0; i < interfaceSignature.argumentCount; ++i) {
                        uint256 argument = f.stack[interfaceBase + 1 + i];
                        _requireKind(argument, interfaceSignature.argumentKinds[i], opPC);
                        if (interfaceSignature.argumentKinds[i] == KIND_REF) {
                            _requireAssignable(
                                classes, argument, classes[interfaceResolved.owner].data,
                                interfaceSignature.argumentTypeOffsets[i],
                                interfaceSignature.argumentTypeLengths[i], heapKinds, heapClasses,
                                arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                            );
                        }
                    }
                    uint256 interfaceHandle = _payload(interfaceReceiver);
                    if (interfaceHandle == 0) _throwJava(6, frames, depth);
                    if (interfaceReceiver != f.locals[0]) revert CallError(4, opPC);
                    _requireHeapKind(
                        interfaceHandle, heapKinds, nextHandle, HEAP_OBJECT, opPC
                    );
                    uint256 interfaceClass = interfaceResolved.owner;
                    uint256 interfaceMethod = interfaceResolved.method;
                    if (selected[interfaceClass].length == 0) {
                        selected[interfaceClass] =
                            new Selected[](classes[interfaceClass].methods.length);
                        referenceCaches[interfaceClass] = new uint256[](classes[interfaceClass].cp.length);
                        fieldCaches[interfaceClass] = new uint256[](classes[interfaceClass].cp.length);
                    }
                    if (!selected[interfaceClass][interfaceMethod].loaded) {
                        selected[interfaceClass][interfaceMethod] = _loadVirtualCallee(
                            classes[interfaceClass], interfaceMethod, opPC
                        );
                        _predecode(classes[interfaceClass], selected[interfaceClass][interfaceMethod]);
                    }
                    Selected memory interfaceTarget = selected[interfaceClass][interfaceMethod];
                    if (depth == MAX_FRAMES) revert JavaException(2);
                    Frame memory interfaceChild = _newFrame(
                        interfaceClass, interfaceMethod, interfaceTarget, opPC
                    );
                    interfaceChild.locals[0] = interfaceReceiver;
                    interfaceChild.initialized[0] = true;
                    _copyArguments(
                        interfaceChild, interfaceTarget, f.stack, interfaceBase + 1, 1
                    );
                    f.sp = interfaceBase;
                    frames[depth] = interfaceChild;
                    ++depth;
                    continue;
                }
                (uint256 calleeClass, uint256 callee, uint256 symbolicClass, bool isConstructor) =
                    _resolveSpecial(
                        classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                    );
                _validateSpecialCalleeMetadata(
                    classes[calleeClass], callee, opPC, isConstructor
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
                if (isConstructor && target.returnKind != 2) revert CallError(4, opPC);
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
                            target.argumentTypeOffsets[i], target.argumentTypeLengths[i], heapKinds, heapClasses, arrayRanks, arrayLeafTypes,
                            nextHandle, parentLinks, opPC
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
                _copyArguments(child, target, f.stack, base + 1, 1);
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
                uint8 nativeBinding = _nativeBinding(classes[calleeClass], callee);
                if (nativeBinding == 0) _validateStaticCalleeMetadata(
                    classes[calleeClass], callee, opPC
                );
                else _validateNativeBinding(classes[calleeClass], callee, opPC);
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                // Finish selected-method descriptor/Code/native validation before an
                // active-use initialization can produce unrelated side effects.
                if (!selected[calleeClass][callee].loaded) {
                    selected[calleeClass][callee] = nativeBinding == 0
                        ? _loadCallee(classes[calleeClass], callee, opPC)
                        : _loadNativeCallee(classes[calleeClass], callee, opPC);
                    if (nativeBinding == 0) {
                        _predecode(classes[calleeClass], selected[calleeClass][callee]);
                    }
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
                Selected memory target = selected[calleeClass][callee];
                if (f.sp < target.argumentCount) revert BytecodeError(3, opPC);
                uint256 base = f.sp - target.argumentCount;
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    _requireKind(f.stack[base + i], target.argumentKinds[i], opPC);
                    if (target.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, f.stack[base + i], classes[calleeClass].data,
                            target.argumentTypeOffsets[i], target.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                }
                if (depth == MAX_FRAMES) revert JavaException(2);
                if (nativeBinding != 0) {
                    uint64 raw = uint64(_payload(f.stack[base]));
                    if (nativeBinding == 1) f.stack[base] = _packFloat(uint32(raw));
                    else if (nativeBinding == 2) f.stack[base] = _packInt(uint32(raw));
                    else if (nativeBinding == 3) f.stack[base] = _packDouble(raw);
                    else f.stack[base] = _packLong(raw);
                    f.sp = base + 1;
                    continue;
                }
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                _copyArguments(child, target, f.stack, base, 0);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb9) { // invokeinterface
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                uint8 count = uint8(c.data[selection.codeOffset + f.pc + 2]);
                uint8 trailing = uint8(c.data[selection.codeOffset + f.pc + 3]);
                f.pc += 4;
                VirtualResolution memory resolved = _resolveInterfaceCall(
                    classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                );
                Selected memory signature = _loadVirtualSignature(
                    classes[resolved.owner], resolved.method, opPC
                );
                if (count == 0 || trailing != 0 || signature.argumentWords + 1 != count) {
                    revert CallError(1, opPC);
                }
                if (f.sp < signature.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - signature.argumentCount - 1;
                uint256 receiver = f.stack[base];
                _requireKind(receiver, KIND_REF, opPC);
                for (uint256 i = 0; i < signature.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    _requireKind(argument, signature.argumentKinds[i], opPC);
                    if (signature.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, argument, classes[resolved.owner].data,
                            signature.argumentTypeOffsets[i], signature.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes,
                            nextHandle, parentLinks, opPC
                        );
                    }
                }
                uint256 handle = _payload(receiver);
                if (handle == 0) _throwJava(6, frames, depth);
                _validatePackedRef(receiver, heapKinds, nextHandle, opPC);
                if (heapKinds[handle] == HEAP_ARRAY) {
                    if (!_arrayImplementsClass(classes, resolved.symbolic)) {
                        revert ReferenceError(2, opPC);
                    }
                    revert CallError(4, opPC);
                }
                if (heapKinds[handle] != HEAP_OBJECT) revert ReferenceError(1, opPC);
                uint256 dynamicClass = heapClasses[handle];
                if (!_classImplements(classes, dynamicClass, resolved.symbolic, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                (uint256 calleeClass, uint256 callee) = _selectInterfaceImplementation(
                    classes, dynamicClass, c.data, resolved.nameOffset, resolved.nameLength,
                    resolved.descriptorOffset, resolved.descriptorLength, parentLinks, opPC
                );
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                if (!selected[calleeClass][callee].loaded) {
                    selected[calleeClass][callee] = _loadVirtualCallee(
                        classes[calleeClass], callee, opPC
                    );
                    _predecode(classes[calleeClass], selected[calleeClass][callee]);
                }
                Selected memory target = selected[calleeClass][callee];
                if (!_sameMethodDescriptor(classes[resolved.owner], resolved.method,
                    classes[calleeClass], callee)) revert CallError(4, opPC);
                if (depth == MAX_FRAMES) revert JavaException(2);
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = receiver;
                child.initialized[0] = true;
                _copyArguments(child, target, f.stack, base + 1, 1);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op >= 0xac && op <= 0xb1) {
                // ireturn / lreturn / freturn / dreturn / areturn / return
                uint8 actualKind = op == 0xac ? uint8(KIND_INT)
                    : (op == 0xad ? uint8(KIND_LONG)
                        : (op == 0xae ? uint8(KIND_FLOAT)
                            : (op == 0xaf ? uint8(KIND_DOUBLE)
                                : (op == 0xb0 ? uint8(KIND_REF) : uint8(0)))));
                uint8 descriptorKind = actualKind == 0 ? 2
                    : (actualKind == KIND_REF ? 3
                        : (actualKind == KIND_LONG ? 4
                            : (actualKind == KIND_FLOAT ? 5
                                : (actualKind == KIND_DOUBLE ? 6 : 1))));
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
                            selection.returnTypeLength, heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle,
                            parentLinks, opPC
                        );
                    }
                    value = actualKind == KIND_INT
                        ? _normalizePackedInt(f.stack[0], selection.returnSubtype)
                        : f.stack[0];
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
            } else if (op == 0xbc || op == 0xbd) { // newarray / anewarray
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                ArrayType memory allocatedType;
                if (op == 0xbc) {
                    uint8 atype = uint8(c.data[selection.codeOffset + f.pc]);
                    ++f.pc;
                    allocatedType.rank = 1;
                    allocatedType.leafType = _newArrayPrimitive(atype);
                    if (allocatedType.leafType == 0) revert ArrayError(1, opPC);
                } else {
                    uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                    f.pc += 2;
                    allocatedType = _resolveANewArrayType(
                        classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                    );
                }
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
                    arrayRanks = new uint8[](MAX_HANDLES + 1);
                    arrayLeafTypes = new uint256[](MAX_HANDLES + 1);
                    arrayHeap = new uint64[][](MAX_HANDLES + 1);
                    objectHeap = new uint256[][](MAX_HANDLES + 1);
                }
                ++arrayCount;
                ++nextHandle;
                totalElements += length;
                heapKinds[nextHandle] = HEAP_ARRAY;
                arrayRanks[nextHandle] = allocatedType.rank;
                arrayLeafTypes[nextHandle] = allocatedType.leafType;
                arrayHeap[nextHandle] = new uint64[](length);
                f.stack[f.sp - 1] = _packRef(uint32(nextHandle));
            } else if (op == 0xc5) { // multianewarray
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                uint8 dimensions = uint8(c.data[selection.codeOffset + f.pc + 2]);
                f.pc += 3;
                ArrayType memory allocatedType = _resolveMultiArrayType(
                    classes, f.classIndex, refIndex, dimensions, opPC,
                    parentLinks, hierarchyState
                );
                if (f.sp < dimensions) revert BytecodeError(3, opPC);
                uint256 base = f.sp - dimensions;
                MultiArrayPlan memory plan;
                plan.counts = new uint256[](dimensions);
                bool negative;
                for (uint256 i = 0; i < dimensions; ++i) {
                    _requireKind(f.stack[base + i], KIND_INT, opPC);
                    int32 signedCount = int32(uint32(_payload(f.stack[base + i])));
                    if (signedCount < 0) negative = true;
                    else plan.counts[i] = uint256(uint32(signedCount));
                }
                // Every count is type-checked and inspected before either quota planning or
                // allocation. In particular, a zero outer dimension does not hide a later
                // negative dimension, and an over-cap positive count does not win over NASE.
                if (negative) _throwJava(4, frames, depth);
                (plan.arrays, plan.elements) = _planMultiArray(
                    plan.counts, arrayCount, totalElements
                );
                if (plan.arrays == 0) _throwJava(7, frames, depth);
                if (heapKinds.length == 0) {
                    heapKinds = new uint8[](MAX_HANDLES + 1);
                    heapClasses = new uint256[](MAX_HANDLES + 1);
                    arrayRanks = new uint8[](MAX_HANDLES + 1);
                    arrayLeafTypes = new uint256[](MAX_HANDLES + 1);
                    arrayHeap = new uint64[][](MAX_HANDLES + 1);
                    objectHeap = new uint256[][](MAX_HANDLES + 1);
                }
                uint256 rootHandle = nextHandle + 1;
                nextHandle = _allocateMultiArray(
                    arrayHeap, heapKinds, arrayRanks, arrayLeafTypes,
                    nextHandle, allocatedType, plan.counts
                );
                arrayCount += plan.arrays;
                totalElements += plan.elements;
                f.sp = base + 1;
                f.stack[base] = _packRef(uint32(rootHandle));
            } else if (op == 0xbe) { // arraylength
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                uint256 handle = _payload(f.stack[f.sp - 1]);
                if (handle == 0) _throwJava(6, frames, depth);
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                f.stack[f.sp - 1] = _packInt(uint32(arrayHeap[handle].length));
            } else if (op == 0xc0 || op == 0xc1) { // checkcast / instanceof
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint8 targetKind, uint256 targetOffset, uint256 targetLength) =
                    _validateCastTarget(c, refIndex, opPC);
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 value = f.stack[f.sp - 1];
                _requireKind(value, KIND_REF, opPC);
                uint256 handle = _payload(value);
                if (handle == 0) {
                    if (op == 0xc1) f.stack[f.sp - 1] = _packInt(0);
                    continue;
                }
                _validatePackedRef(value, heapKinds, nextHandle, opPC);
                bool assignable;
                if (targetKind == 2) {
                    ArrayType memory wantedArray = _resolveArrayClassType(
                        classes, f.classIndex, c.data, targetOffset, targetLength, opPC,
                        parentLinks, hierarchyState
                    );
                    assignable = heapKinds[handle] == HEAP_ARRAY && _arrayTypeAssignable(
                        classes, arrayRanks[handle], arrayLeafTypes[handle],
                        wantedArray.rank, wantedArray.leafType, parentLinks
                    );
                } else {
                    if (targetKind != 1) revert TypeError(2, opPC);
                    (bool foundTarget, uint256 targetClass) = _findClass(
                        classes, c.data, targetOffset, targetLength
                    );
                    if (!foundTarget) revert LinkError(4, opPC);
                    ClassInfo memory castClass = classes[targetClass];
                    if (targetClass != f.classIndex && !_classAccessible(c, castClass)) {
                        revert TypeError(2, opPC);
                    }
                    _validateHierarchy(classes, targetClass, parentLinks, hierarchyState);
                    if (heapKinds[handle] == HEAP_ARRAY) {
                        assignable = _arrayImplementsClass(classes, targetClass);
                    } else if (heapKinds[handle] == HEAP_OBJECT) {
                        assignable = _typeAssignable(
                            classes, heapClasses[handle], targetClass, parentLinks
                        );
                    }
                }
                if (op == 0xc1) {
                    f.stack[f.sp - 1] = _packInt(assignable ? 1 : 0);
                } else if (!assignable) {
                    _throwJava(8, frames, depth);
                }
            } else if (op == 0xc6 || op == 0xc7) { // ifnull / ifnonnull
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool isNull = _payload(f.stack[f.sp - 1]) == 0;
                --f.sp;
                f.pc = ((op == 0xc6) == isNull)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0x76 || op == 0x77) { // fneg / dneg: sign flip only
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 wanted = op == 0x76 ? KIND_FLOAT : KIND_DOUBLE;
                _requireKind(f.stack[f.sp - 1], wanted, opPC);
                uint64 sign = op == 0x76 ? uint64(0x80000000) : uint64(0x8000000000000000);
                uint64 bits = uint64(_payload(f.stack[f.sp - 1])) ^ sign;
                f.stack[f.sp - 1] = op == 0x76 ? _packFloat(uint32(bits)) : _packDouble(bits);
            } else if (op == 0x86 || op == 0x87) { // i2f / i2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint32 raw = uint32(_payload(f.stack[f.sp - 1]));
                f.stack[f.sp - 1] = op == 0x86
                    ? _packFloat(uint32(_signedIntegerToIEEE(uint64(raw), 32, 24, 127, 23)))
                    : _packDouble(_signedIntegerToIEEE(uint64(raw), 32, 53, 1023, 52));
                if (op == 0x87 && _stackWords(f.stack, f.sp) > f.stack.length) {
                    revert BytecodeError(9, opPC);
                }
            } else if (op == 0x89 || op == 0x8a) { // l2f / l2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                uint64 raw = uint64(_payload(f.stack[f.sp - 1]));
                f.stack[f.sp - 1] = op == 0x89
                    ? _packFloat(uint32(_signedIntegerToIEEE(raw, 64, 24, 127, 23)))
                    : _packDouble(_signedIntegerToIEEE(raw, 64, 53, 1023, 52));
            } else if (op == 0x8b || op == 0x8c) { // f2i / f2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_FLOAT, opPC);
                uint64 converted = _ieeeToSignedInteger(
                    uint64(uint32(_payload(f.stack[f.sp - 1]))), 8, 23, op == 0x8b ? 32 : 64
                );
                f.stack[f.sp - 1] = op == 0x8b
                    ? _packInt(uint32(converted)) : _packLong(converted);
                if (op == 0x8c && _stackWords(f.stack, f.sp) > f.stack.length) {
                    revert BytecodeError(9, opPC);
                }
            } else if (op == 0x8d) { // f2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_FLOAT, opPC);
                f.stack[f.sp - 1] = _packDouble(_floatToDoubleBits(
                    uint32(_payload(f.stack[f.sp - 1]))
                ));
                if (_stackWords(f.stack, f.sp) > f.stack.length) revert BytecodeError(9, opPC);
            } else if (op == 0x8e || op == 0x8f) { // d2i / d2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_DOUBLE, opPC);
                uint64 converted = _ieeeToSignedInteger(
                    uint64(_payload(f.stack[f.sp - 1])), 11, 52, op == 0x8e ? 32 : 64
                );
                f.stack[f.sp - 1] = op == 0x8e
                    ? _packInt(uint32(converted)) : _packLong(converted);
            } else if (op == 0x90) { // d2f
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_DOUBLE, opPC);
                f.stack[f.sp - 1] = _packFloat(_doubleToFloatBits(
                    uint64(_payload(f.stack[f.sp - 1]))
                ));
            } else if (op >= 0x95 && op <= 0x98) { // fcmp*/dcmp*
                if (f.sp < 2) revert BytecodeError(3, opPC);
                bool doubles = op >= 0x97;
                uint256 wanted = doubles ? KIND_DOUBLE : KIND_FLOAT;
                _requireKind(f.stack[f.sp - 2], wanted, opPC);
                _requireKind(f.stack[f.sp - 1], wanted, opPC);
                int8 compared = _compareIEEE(
                    uint64(_payload(f.stack[f.sp - 2])),
                    uint64(_payload(f.stack[f.sp - 1])), doubles ? 11 : 8,
                    doubles ? 52 : 23, op == 0x95 || op == 0x97
                );
                f.stack[f.sp - 2] = _packInt(uint32(int32(compared)));
                --f.sp;
            } else if (op >= 0x0b && op <= 0x0d) { // fconst_0..2
                uint32 value = op == 0x0b ? 0 : (op == 0x0c ? 0x3f800000 : 0x40000000);
                f.sp = _push(f.stack, f.sp, _packFloat(value), opPC);
            } else if (op == 0x0e || op == 0x0f) { // dconst_0, dconst_1
                f.sp = _push(f.stack, f.sp,
                    _packDouble(op == 0x0e ? uint64(0) : uint64(0x3ff0000000000000)), opPC);
            } else if (op >= 0x22 && op <= 0x25) { // fload_0..3
                f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x22, KIND_FLOAT, opPC
                );
            } else if (op >= 0x26 && op <= 0x29) { // dload_0..3
                f.sp = _loadDouble(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x26, opPC
                );
            } else if (op >= 0x43 && op <= 0x46) { // fstore_0..3
                f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x43, KIND_FLOAT, opPC
                );
            } else if (op >= 0x47 && op <= 0x4a) { // dstore_0..3
                f.sp = _storeDouble(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x47, opPC
                );
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
            // Mark C active before requesting its superclass. This is observable by
            // reentrant initialization reached through a superclass or interface.
            initializationState[current] = 1;
            ClassInfo memory c = classes[current];
            for (uint256 i = 0; i < c.fields.length; ++i) {
                if ((c.fields[i].accessFlags & 0x0008) != 0 && c.fields[i].hasConstant) {
                    uint8 constantKind = _fieldKind(c, c.fields[i]);
                    staticValues[current][i] = constantKind == KIND_LONG
                        ? _packLong(c.fields[i].constantValue)
                        : (constantKind == KIND_DOUBLE
                            ? _packDouble(c.fields[i].constantValue)
                            : (constantKind == KIND_FLOAT
                                ? _packFloat(uint32(c.fields[i].constantValue))
                                : _packInt(uint32(c.fields[i].constantValue))));
                }
            }
            uint256 link = parentLinks[current];
            bool parentReady = _isInterface(c) || link == type(uint256).max
                || (link != 0 && initializationState[link - 1] != 0);
            (bool hasDefaultPrerequisite,) = _isInterface(c)
                ? (false, uint256(0))
                : _nextDefaultInterface(classes, current, initializationState);
            if (c.initializerPlusOne == 0 && parentReady && !hasDefaultPrerequisite) {
                initializationState[current] = 2;
                return depth;
            }
            if (depth == MAX_FRAMES) revert JavaException(2);
            Frame memory continuation;
            continuation.classIndex = current;
            continuation.isInitContinuation = true;
            frames[depth] = continuation;
            ++depth;
            // Interfaces initialize themselves only; their parent traversal belongs to
            // the enclosing ordinary-class prerequisite calculation.
            if (_isInterface(c) || link == type(uint256).max || link == 0) return depth;
            current = link - 1;
            if (initializationState[current] != 0) return depth;
        }
        return depth;
    }

    function _declaresDefault(ClassInfo memory c) private pure returns (bool) {
        for (uint256 i = 0; i < c.methods.length; ++i) {
            uint256 meta = c.methods[i];
            uint16 access = uint16(meta);
            if ((access & (0x0008 | 0x0400)) == 0 && _methodCodeCount(meta) == 1) return true;
        }
        return false;
    }

    function _nextDefaultInterface(
        ClassInfo[] memory classes, uint256 classIndex, uint8[] memory initializationState
    ) private pure returns (bool found, uint256 target) {
        bool[] memory seen = new bool[](classes.length);
        uint256[] memory nodes = new uint256[](classes.length);
        uint256[] memory edges = new uint256[](classes.length);
        ClassInfo memory c = classes[classIndex];
        for (uint256 root = 0; root < c.interfaces.length; ++root) {
            uint256 direct = _resolveInterfaceEdge(classes, classIndex, root);
            if (seen[direct]) continue;
            uint256 size = 1;
            nodes[0] = direct;
            seen[direct] = true;
            while (size != 0) {
                uint256 at = size - 1;
                uint256 node = nodes[at];
                if (edges[at] < classes[node].interfaces.length) {
                    uint256 edge = edges[at]++;
                    uint256 parent = _resolveInterfaceEdge(classes, node, edge);
                    if (!seen[parent]) {
                        seen[parent] = true;
                        nodes[size] = parent;
                        edges[size] = 0;
                        ++size;
                    }
                    continue;
                }
                --size; // postorder: parents before the declaring descendant
                if (initializationState[node] == 0 && _declaresDefault(classes[node])) {
                    return (true, node);
                }
            }
        }
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
        if (_isInterface(classes[classIndex])) {
            _validateInterfaceClosure(classes, classIndex, parentLinks);
            return;
        }
        if (hierarchyState[classIndex] != 2) {
            bool[] memory seen = new bool[](classes.length);
            uint256 current = classIndex;
            while (hierarchyState[current] != 2) {
                if (seen[current]) revert HierarchyError(2, current);
                seen[current] = true;
                ClassInfo memory child = classes[current];
                _requireSupportedClass(child, current);
                bool isObject = _isObjectClass(child);
                if (isObject) {
                    if (child.hasSuperclass) revert HierarchyError(4, current);
                    parentLinks[current] = type(uint256).max;
                    break;
                }
                if (!child.hasSuperclass) revert HierarchyError(4, current);

                (bool found, uint256 parent) = _findClass(
                    classes, child.data, child.superNameOffset, child.superNameLength
                );
                if (!found) revert HierarchyError(1, current);
                ClassInfo memory parentClass = classes[parent];
                if (_isInterface(parentClass)) revert HierarchyError(4, current);
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
        _validateInterfaceClosure(classes, classIndex, parentLinks);
    }

    function _validateInterfaceClosure(
        ClassInfo[] memory classes, uint256 start, uint256[] memory parentLinks
    ) private pure {
        bool[] memory reachable = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        if (_isInterface(classes[start])) {
            queue[tail++] = start;
            reachable[start] = true;
        } else {
            uint256 current = start;
            while (true) {
                ClassInfo memory owner = classes[current];
                for (uint256 i = 0; i < owner.interfaces.length; ++i) {
                    uint256 target = _resolveInterfaceEdge(classes, current, i);
                    for (uint256 j = 0; j < i; ++j) {
                        if (_resolveInterfaceEdge(classes, current, j) == target) {
                            revert InterfaceError(1, current);
                        }
                    }
                    if (!reachable[target]) {
                        reachable[target] = true;
                        queue[tail++] = target;
                    }
                }
                uint256 link = parentLinks[current];
                if (link == 0 || link == type(uint256).max) break;
                current = link - 1;
            }
        }
        while (head < tail) {
            uint256 ownerIndex = queue[head++];
            _validateInterfaceHeaderAndMethods(classes[ownerIndex], ownerIndex);
            ClassInfo memory owner = classes[ownerIndex];
            for (uint256 i = 0; i < owner.interfaces.length; ++i) {
                uint256 target = _resolveInterfaceEdge(classes, ownerIndex, i);
                for (uint256 j = 0; j < i; ++j) {
                    if (_resolveInterfaceEdge(classes, ownerIndex, j) == target) {
                        revert InterfaceError(1, ownerIndex);
                    }
                }
                if (!reachable[target]) {
                    reachable[target] = true;
                    queue[tail++] = target;
                }
            }
        }
        if (tail == 0) return;
        uint256[] memory indegree = new uint256[](classes.length);
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!reachable[i]) continue;
            for (uint256 j = 0; j < classes[i].interfaces.length; ++j) {
                uint256 target = _resolveInterfaceEdge(classes, i, j);
                ++indegree[target];
            }
        }
        head = 0;
        uint256 processed;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (reachable[i] && indegree[i] == 0) queue[head++] = i;
        }
        uint256 at;
        while (at < head) {
            uint256 owner = queue[at++];
            ++processed;
            for (uint256 j = 0; j < classes[owner].interfaces.length; ++j) {
                uint256 target = _resolveInterfaceEdge(classes, owner, j);
                if (--indegree[target] == 0) queue[head++] = target;
            }
        }
        if (processed != tail) {
            for (uint256 i = 0; i < classes.length; ++i) {
                if (reachable[i] && indegree[i] != 0) revert InterfaceError(2, i);
            }
        }
    }

    function _validateInterfaceHeaderAndMethods(ClassInfo memory c, uint256 classIndex)
        private pure
    {
        if (!_isInterface(c) || (c.accessFlags & 0x0400) == 0
            || (c.accessFlags & 0xe010) != 0 || !c.hasSuperclass
            || !_equalsLiteral(c.data, c.superNameOffset, c.superNameLength, bytes("java/lang/Object"))) {
            revert InterfaceError(1, classIndex);
        }
        for (uint256 i = 0; i < c.fields.length; ++i) {
            if ((c.fields[i].accessFlags & 0x0019) != 0x0019) {
                revert InterfaceError(1, classIndex);
            }
        }
        for (uint256 i = 0; i < c.methods.length; ++i) {
            uint256 meta = c.methods[i];
            uint16 access = uint16(meta);
            if ((access & 0x0008) != 0) continue; // static metadata is deferred to M4f-c
            uint256 codeCount = _methodCodeCount(meta);
            bool isAbstract = (access & 0x0400) != 0;
            // Java 8 public defaults, including ACC_BRIDGE|ACC_SYNTHETIC
            // compiler bridges, are admitted. Private/native/synchronized forms
            // and abstract/Code inconsistencies remain unsupported shapes.
            if ((access & 0x0001) == 0
                || (access & ~(uint16(0x0001 | 0x0040 | 0x0080 | 0x0400 | 0x0800 | 0x1000))) != 0
                || (isAbstract ? codeCount != 0 : codeCount != 1)) {
                revert InterfaceError(4, classIndex);
            }
            if (!isAbstract) {
                uint256 descriptorIndex = (meta >> 32) & 0xffff;
                if (descriptorIndex == 0 || descriptorIndex >= c.cp.length
                    || uint8(c.cp[descriptorIndex]) != 1) revert InterfaceError(4, classIndex);
                (uint256 descriptorOffset, uint256 descriptorLength) = _utf(c.cp[descriptorIndex]);
                Selected memory signature;
                if (!_descriptor(c.data, descriptorOffset, descriptorLength, signature)) {
                    revert InterfaceError(4, classIndex);
                }
            }
        }
    }

    function _resolveInterfaceEdge(
        ClassInfo[] memory classes, uint256 ownerIndex, uint256 edge
    ) private pure returns (uint256 target) {
        ClassInfo memory owner = classes[ownerIndex];
        uint256 cpIndex = owner.interfaces[edge];
        if (cpIndex == 0 || cpIndex >= owner.cp.length || uint8(owner.cp[cpIndex]) != 7) {
            revert InterfaceError(1, ownerIndex);
        }
        uint256 nameIndex = (owner.cp[cpIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= owner.cp.length || uint8(owner.cp[nameIndex]) != 1) {
            revert InterfaceError(1, ownerIndex);
        }
        (uint256 off, uint256 n) = _utf(owner.cp[nameIndex]);
        if (!_validInternalName(owner.data, off, n)) revert InterfaceError(1, ownerIndex);
        (bool found, uint256 resolved) = _findClass(classes, owner.data, off, n);
        if (!found) revert LinkError(4, ownerIndex);
        if (!_isInterface(classes[resolved])) revert InterfaceError(1, ownerIndex);
        if (resolved != ownerIndex && !_classAccessible(owner, classes[resolved])) {
            revert InterfaceError(3, ownerIndex);
        }
        return resolved;
    }

    function _validateStaticCalleeMetadata(
        ClassInfo memory c, uint256 method, uint256 callPC
    ) private pure {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        // Java 8 interface static methods are public. Keep the accepted
        // compiler metadata flags aligned with the existing descriptor/code
        // subset, while rejecting private and malformed interface members at
        // the call site rather than treating them as inherited defaults.
        if (_isInterface(c)
            && ((access & 0x0001) == 0
                || (access & ~(uint16(0x0001 | 0x0008 | 0x0040 | 0x0080 | 0x0800 | 0x1000))) != 0)) {
            revert CallError(4, callPC);
        }
    }

    function _validateSpecialCalleeMetadata(
        ClassInfo memory c, uint256 method, uint256 callPC, bool isConstructor
    ) private pure {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & 0x0008) != 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        if (isConstructor) {
            (uint256 off, uint256 n) = _utf(c.cp[(meta >> 32) & 0xffff]);
            Selected memory signature;
            if (!_descriptor(c.data, off, n, signature) || signature.returnKind != 2) {
                revert CallError(4, callPC);
            }
        }
    }

    function _loadSpecialCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, bool isConstructor
    ) private pure returns (Selected memory s) {
        _validateSpecialCalleeMetadata(c, method, callPC, isConstructor);
        uint256 meta = c.methods[method];
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
            || s.maxLocals < s.argumentWords + 1) revert CallError(4, callPC);
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

    function _findInterfaceMethod(
        ClassInfo[] memory classes, uint256 start, bool startIsInterface,
        bytes memory nameData, uint256 nameOffset, uint256 nameLength,
        uint256 descriptorOffset, uint256 descriptorLength,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 method) {
        bool[] memory reachable = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        if (startIsInterface) {
            for (uint256 i = 0; i < classes[start].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, start, i);
                if (!reachable[direct]) { reachable[direct] = true; queue[tail++] = direct; }
            }
        } else {
            uint256 current = start;
            while (true) {
                for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                    uint256 direct = _resolveInterfaceEdge(classes, current, i);
                    if (!reachable[direct]) { reachable[direct] = true; queue[tail++] = direct; }
                }
                uint256 link = parentLinks[current];
                if (link == 0 || link == type(uint256).max) break;
                current = link - 1;
            }
        }
        while (head < tail) {
            uint256 iface = queue[head++];
            for (uint256 i = 0; i < classes[iface].interfaces.length; ++i) {
                uint256 parent = _resolveInterfaceEdge(classes, iface, i);
                if (!reachable[parent]) { reachable[parent] = true; queue[tail++] = parent; }
            }
        }
        bool[] memory declares = new bool[](classes.length);
        uint256[] memory methods = new uint256[](classes.length);
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!reachable[i]) continue;
            (bool has, uint256 candidate) = _lookupExactMethod(
                classes, i, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (has && (uint16(classes[i].methods[candidate]) & (0x0002 | 0x0008)) == 0) {
                declares[i] = true;
                methods[i] = candidate;
            }
        }
        uint256 concreteCount;
        uint256 concreteOwner;
        uint256 concreteMethod;
        uint256 abstractOwner;
        uint256 abstractMethod;
        bool hasAbstract;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!declares[i]) continue;
            bool shadowed;
            for (uint256 j = 0; j < classes.length; ++j) {
                // Any matching declaration in a strict subinterface suppresses
                // this one, including an abstract re-declaration.
                if (i != j && declares[j] && _interfaceExtends(classes, j, i)) {
                    shadowed = true;
                    break;
                }
            }
            if (shadowed) continue;
            uint256 meta = classes[i].methods[methods[i]];
            if ((uint16(meta) & 0x0400) == 0 && _methodCodeCount(meta) == 1) {
                ++concreteCount;
                concreteOwner = i;
                concreteMethod = methods[i];
            } else if (!hasAbstract) {
                hasAbstract = true;
                abstractOwner = i;
                abstractMethod = methods[i];
            }
        }
        if (concreteCount > 1) revert JavaException(10);
        if (concreteCount == 1) return (true, concreteOwner, concreteMethod);
        if (hasAbstract) return (true, abstractOwner, abstractMethod);
    }

    function _selectInterfaceImplementation(
        ClassInfo[] memory classes, uint256 dynamicClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 owner, uint256 method) {
        uint256 current = dynamicClass;
        while (true) {
            (bool found, uint256 candidate) = _lookupExactMethod(
                classes, current, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (found) {
                uint256 meta = classes[current].methods[candidate];
                uint16 access = uint16(meta);
                // A private declaration is never a public implementation; retain
                // the unsupported-access guard rather than executing it as one.
                if ((access & 0x0002) != 0) revert CallError(4, pc);
                if ((access & 0x0001) == 0 || (access & (0x0008 | 0x0020 | 0x0100)) != 0) {
                        revert CallError(4, pc);
                    }
                    if ((access & 0x0400) != 0) {
                        if (_methodCodeCount(meta) != 0) revert CallError(4, pc);
                        revert JavaException(11);
                    }
                    if (_methodCodeCount(meta) != 1) revert CallError(4, pc);
                    uint256 ancestor = current;
                    while (parentLinks[ancestor] != 0
                        && parentLinks[ancestor] != type(uint256).max) {
                        ancestor = parentLinks[ancestor] - 1;
                        (bool inherited, uint256 inheritedMethod) = _lookupExactMethod(
                            classes, ancestor, nameData, nameOffset, nameLength,
                            descriptorOffset, descriptorLength, pc
                        );
                        if (!inherited) continue;
                        uint16 inheritedAccess = uint16(classes[ancestor].methods[inheritedMethod]);
                        bool overrides = (inheritedAccess & (0x0001 | 0x0004)) != 0
                            || ((inheritedAccess & 0x0002) == 0
                                && _samePackage(classes[current], classes[ancestor]));
                        if (overrides && (inheritedAccess & 0x0010) != 0) {
                            revert CallError(4, pc);
                        }
                    }
                return (current, candidate);
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
        (bool inheritedDefault, uint256 interfaceOwner, uint256 interfaceMethod) =
            _findInterfaceMethod(
                classes, dynamicClass, false, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, parentLinks, pc
            );
        if (!inheritedDefault) revert JavaException(11);
        uint256 selectedMeta = classes[interfaceOwner].methods[interfaceMethod];
        if ((uint16(selectedMeta) & 0x0400) != 0 || _methodCodeCount(selectedMeta) == 0) {
            revert JavaException(11);
        }
        return (interfaceOwner, interfaceMethod);
    }

    function _loadVirtualSignature(ClassInfo memory c, uint256 method, uint256 callPC)
        private
        pure
        returns (Selected memory s)
    {
        uint256 meta = c.methods[method];
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        if (descriptorIndex == 0 || descriptorIndex >= c.cp.length
            || uint8(c.cp[descriptorIndex]) != 1) revert CallError(1, callPC);
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        s.argumentCount = s.argumentKinds.length;
    }

    function _loadVirtualCallee(ClassInfo memory c, uint256 method, uint256 callPC)
        private
        pure
        returns (Selected memory s)
    {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & (0x0002 | 0x0008 | 0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        s = _loadVirtualSignature(c, method, callPC);
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c.data, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS
            || s.maxLocals < s.argumentWords + 1) revert CallError(4, callPC);
        s.loaded = true;
    }

    function _resolveVirtual(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
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
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(
            classes, caller.data, ownerOff, ownerLen
        );
        if (!foundOwner) revert LinkError(4, pc);
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (_isInterface(classes[symbolic])) revert CallError(4, pc);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        bool isCtor = _equalsLiteral(
            caller.data, out.nameOffset, out.nameLength, bytes("<init>")
        );
        bool isInitializer = _equalsLiteral(
            caller.data, out.nameOffset, out.nameLength, bytes("<clinit>")
        );
        if (isCtor || isInitializer) revert CallError(4, pc);
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }

        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        out.owner = symbolic;
        bool resolvedDeclaration;
        while (true) {
            (bool found, uint256 method) = _lookupExactMethod(
                classes, out.owner, caller.data, out.nameOffset, out.nameLength,
                out.descriptorOffset, out.descriptorLength, pc
            );
            if (found) { out.method = method; resolvedDeclaration = true; break; }
            uint256 link = parentLinks[out.owner];
            if (link == 0 || link == type(uint256).max) break;
            out.owner = link - 1;
        }
        if (!resolvedDeclaration) {
            (bool foundInterface, uint256 interfaceOwner, uint256 interfaceMethod) =
                _findInterfaceMethod(
                    classes, symbolic, false, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, parentLinks, pc
                );
            if (!foundInterface) revert CallError(3, pc);
            out.owner = interfaceOwner;
            out.method = interfaceMethod;
        }
        uint16 access = uint16(classes[out.owner].methods[out.method]);
        if ((access & (0x0002 | 0x0008)) != 0) revert CallError(4, pc);
        if (!_canAccessMember(
            classes, callerClass, out.owner, access, parentLinks, hierarchyState
        )) revert CallError(4, pc);
    }

    function _resolveInterfaceCall(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 11) {
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
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(classes, caller.data, ownerOff, ownerLen);
        if (!foundOwner) revert LinkError(4, pc);
        if (!_isInterface(classes[symbolic])) revert InterfaceError(1, pc);
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
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (_equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<init>"))
            || _equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }
        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        (bool own, uint256 ownMethod) = _lookupExactMethod(
            classes, symbolic, caller.data, out.nameOffset, out.nameLength,
            out.descriptorOffset, out.descriptorLength, pc
        );
        if (own) {
            out.owner = symbolic;
            out.method = ownMethod;
        } else {
            bool objectFallback;
            for (uint256 i = 0; i < classes.length; ++i) {
                if (!_isObjectClass(classes[i])) continue;
                (bool hasObject, uint256 objectMethod) = _lookupExactMethod(
                    classes, i, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, pc
                );
                if (hasObject) {
                    uint16 access = uint16(classes[i].methods[objectMethod]);
                    if ((access & 0x0001) != 0 && (access & 0x0008) == 0) {
                        out.owner = i;
                        out.method = objectMethod;
                        objectFallback = true;
                    }
                }
                break;
            }
            if (!objectFallback) {
                (bool inherited, uint256 interfaceOwner, uint256 interfaceMethod) =
                    _findInterfaceMethod(
                        classes, symbolic, true, caller.data, out.nameOffset, out.nameLength,
                        out.descriptorOffset, out.descriptorLength, parentLinks, pc
                    );
                if (!inherited) revert CallError(3, pc);
                out.owner = interfaceOwner;
                out.method = interfaceMethod;
            }
        }
        uint16 resolvedAccess = uint16(classes[out.owner].methods[out.method]);
        if ((resolvedAccess & 0x0001) == 0
            || (resolvedAccess & (0x0002 | 0x0008 | 0x0100)) != 0) revert CallError(4, pc);
    }

    function _selectVirtual(
        ClassInfo[] memory classes, uint256 dynamicClass, VirtualResolution memory resolved,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 owner, uint256 method) {
        if (_isInterface(classes[resolved.owner])) {
            ClassInfo memory referenceClass = classes[resolved.referenceClass];
            return _selectInterfaceImplementation(
                classes, dynamicClass, referenceClass.data, resolved.nameOffset,
                resolved.nameLength, resolved.descriptorOffset, resolved.descriptorLength,
                parentLinks, pc
            );
        }
        uint256[] memory path = new uint256[](classes.length);
        uint256 count;
        uint256 current = dynamicClass;
        while (current != resolved.owner) {
            if (count == classes.length) revert ReferenceError(2, pc);
            path[count++] = current;
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) revert ReferenceError(2, pc);
            current = link - 1;
        }
        owner = resolved.owner;
        method = resolved.method;
        ClassInfo memory referenceClass = classes[resolved.referenceClass];
        while (count != 0) {
            uint256 candidateClass = path[--count];
            (bool found, uint256 candidate) = _lookupExactMethod(
                classes, candidateClass, referenceClass.data, resolved.nameOffset,
                resolved.nameLength, resolved.descriptorOffset, resolved.descriptorLength, pc
            );
            if (!found) continue;
            uint16 candidateAccess = uint16(classes[candidateClass].methods[candidate]);
            if ((candidateAccess & 0x0002) != 0) continue; // private never overrides
            uint16 selectedAccess = uint16(classes[owner].methods[method]);
            bool overrides = (selectedAccess & (0x0001 | 0x0004)) != 0
                || ((selectedAccess & 0x0002) == 0
                    && _samePackage(classes[candidateClass], classes[owner]));
            if (!overrides) continue;
            if ((selectedAccess & 0x0010) != 0 || (candidateAccess & 0x0008) != 0) {
                revert CallError(4, pc);
            }
            owner = candidateClass;
            method = candidate;
        }
        uint256 selectedMeta = classes[owner].methods[method];
        if ((uint16(selectedMeta) & 0x0400) != 0) {
            if (_methodCodeCount(selectedMeta) != 0) revert CallError(4, pc);
            revert JavaException(11);
        }
    }

    function _sameMethodDescriptor(
        ClassInfo memory first, uint256 firstMethod, ClassInfo memory second, uint256 secondMethod
    ) private pure returns (bool) {
        (uint256 firstOff, uint256 firstLen) =
            _utf(first.cp[(first.methods[firstMethod] >> 32) & 0xffff]);
        (uint256 secondOff, uint256 secondLen) =
            _utf(second.cp[(second.methods[secondMethod] >> 32) & 0xffff]);
        return _equalsCross(first.data, firstOff, firstLen, second.data, secondOff, secondLen);
    }

    function _validOrdinaryMethodName(bytes memory data, uint256 off, uint256 n)
        private
        pure
        returns (bool)
    {
        if (n == 0) return false;
        for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || ch == bytes1("/") || ch == bytes1("<") || ch == bytes1(">")
                || uint8(ch) == 0) return false;
        }
        return true;
    }

    function _resolveInterfaceSpecial(
        ClassInfo[] memory classes, uint256 callerClass, uint256 callerMethod,
        uint256 refIndex, uint256 pc, uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 11) {
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
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(
            classes, caller.data, ownerOff, ownerLen
        );
        if (!foundOwner) revert LinkError(4, pc);
        if (!_isInterface(classes[symbolic])) revert InterfaceError(1, pc);
        _validateHierarchy(classes, callerClass, parentLinks, hierarchyState);
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }
        bool direct;
        for (uint256 i = 0; i < caller.interfaces.length; ++i) {
            if (_resolveInterfaceEdge(classes, callerClass, i) == symbolic) direct = true;
        }
        if (!direct || (uint16(caller.methods[callerMethod]) & 0x0008) != 0) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (_equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<init>"))
            || _equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }
        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        (bool own, uint256 ownMethod) = _lookupExactMethod(
            classes, symbolic, caller.data, out.nameOffset, out.nameLength,
            out.descriptorOffset, out.descriptorLength, pc
        );
        if (own) {
            out.owner = symbolic;
            out.method = ownMethod;
        } else {
            (bool inherited, uint256 inheritedOwner, uint256 inheritedMethod) =
                _findInterfaceMethod(
                    classes, symbolic, true, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, parentLinks, pc
                );
            if (!inherited) revert CallError(3, pc);
            out.owner = inheritedOwner;
            out.method = inheritedMethod;
        }
        uint256 meta = classes[out.owner].methods[out.method];
        uint16 access = uint16(meta);
        if ((access & 0x0001) == 0 || (access & (0x0002 | 0x0008 | 0x0020 | 0x0100)) != 0) {
            revert CallError(4, pc);
        }
        if ((access & 0x0400) != 0 || _methodCodeCount(meta) == 0) {
            if ((access & 0x0400) != 0 && _methodCodeCount(meta) != 0) {
                revert CallError(4, pc);
            }
            revert JavaException(11);
        }
        if (_methodCodeCount(meta) != 1) revert CallError(4, pc);
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
        if (_isInterface(classes[symbolic])) revert CallError(4, pc);
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
        if (refIndex == 0 || refIndex >= caller.cp.length) revert CallError(1, pc);
        uint8 referenceTag = uint8(caller.cp[refIndex]);
        if (referenceTag != 10 && referenceTag != 11) revert CallError(1, pc);
        bool interfaceReference = referenceTag == 11;
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
        if (!_validInternalName(caller.data, ownerOffset, ownerLength)) revert CallError(1, pc);
        bool sameOwner = _equalsSlice(
            caller.data, ownerOffset, ownerLength, caller.thisNameOffset, caller.thisNameLength
        );
        if (sameOwner) {
            owner = callerClass;
        } else {
            if (!bundleMode
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/Float"))
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/Double"))) {
                revert CallError(2, pc);
            }
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
        if (interfaceReference) {
            if (!_isInterface(classes[owner])) revert InterfaceError(1, pc);
        } else if (_isInterface(classes[owner])) {
            revert CallError(4, pc);
        }
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
        if (!_validOrdinaryMethodName(caller.data, nameOffset, nameLength)) {
            revert CallError(1, pc);
        }

        if (interfaceReference) {
            // Interface static methods are never inherited: resolution is exact
            // in the symbolic interface named by CONSTANT_InterfaceMethodref.
            method = _findExactMethod(
                classes, owner, caller.data, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
        } else {
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
        }
        if (!_canAccessMember(
            classes, callerClass, owner, uint16(classes[owner].methods[method]),
            parentLinks, hierarchyState
        )) revert CallError(4, pc);
        cache[refIndex] = ((owner + 1) << 128) | (method + 1);
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
        if (!_validInternalName(caller.data, ownerOffset, ownerLength)) revert FieldError(1, pc);
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
            bool found;
            (found, owner, field) = _findResolvedField(
                classes, symbolic, caller.data, nameOffset, nameLength,
                descriptorOffset, descriptorLength, parentLinks, pc
            );
            if (!found) revert FieldError(2, pc);
            cache[refIndex] = ((owner + 1) << 128) | (field + 1);
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

    function _findResolvedField(
        ClassInfo[] memory classes,
        uint256 symbolic,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        uint256[] memory parentLinks,
        uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 field) {
        bool[] memory seenInterfaces = new bool[](classes.length);
        uint256 current = symbolic;
        while (true) {
            (found, field) = _fieldDeclaredHere(
                classes[current], nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (found) return (true, current, field);

            if (_isInterface(classes[current])) {
                seenInterfaces[current] = true;
            }
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, current, i);
                (found, owner, field) = _findInterfaceField(
                    classes, direct, nameData, nameOffset, nameLength,
                    descriptorOffset, descriptorLength, seenInterfaces, pc
                );
                if (found) return (true, owner, field);
            }
            // Interfaces have no ordinary superclass field-search path through Object.
            if (_isInterface(classes[current])) return (false, 0, 0);
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return (false, 0, 0);
            current = link - 1;
        }
    }

    function _findInterfaceField(
        ClassInfo[] memory classes,
        uint256 interfaceClass,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        bool[] memory seen,
        uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 field) {
        if (seen[interfaceClass]) return (false, 0, 0);
        seen[interfaceClass] = true;
        (found, field) = _fieldDeclaredHere(
            classes[interfaceClass], nameData, nameOffset, nameLength,
            descriptorOffset, descriptorLength, pc
        );
        if (found) return (true, interfaceClass, field);
        for (uint256 i = 0; i < classes[interfaceClass].interfaces.length; ++i) {
            uint256 parent = _resolveInterfaceEdge(classes, interfaceClass, i);
            (found, owner, field) = _findInterfaceField(
                classes, parent, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, seen, pc
            );
            if (found) return (true, owner, field);
        }
        return (false, 0, 0);
    }

    function _fieldDeclaredHere(
        ClassInfo memory target,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        uint256 pc
    ) private pure returns (bool found, uint256 field) {
        uint256 foundPlusOne;
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
                nameData, nameOffset, nameLength)) continue;
            (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                _utf(target.cp[candidate.descriptorIndex]);
            if (!_equalsCross(target.data, candidateDescriptorOffset, candidateDescriptorLength,
                nameData, descriptorOffset, descriptorLength)) continue;
            if (foundPlusOne != 0) revert FieldError(2, pc);
            foundPlusOne = i + 1;
        }
        if (foundPlusOne != 0) return (true, foundPlusOne - 1);
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
        (bool valid, uint256 width, uint8 kind) = _descriptorType(c.data, off, off + n, false);
        return valid && width == n ? kind : 0;
    }

    function _fieldSubtype(ClassInfo memory c, FieldInfo memory field)
        private pure returns (uint8)
    {
        if (field.descriptorIndex == 0 || field.descriptorIndex >= c.cp.length
            || uint8(c.cp[field.descriptorIndex]) != 1) return 0;
        (uint256 off, uint256 n) = _utf(c.cp[field.descriptorIndex]);
        if (n != 1) return 0;
        uint8 subtype = uint8(c.data[off]);
        return _isIntLike(subtype) ? subtype : 0;
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

    function _requireProtectedMethodReceiver(
        ClassInfo[] memory classes, uint256 callerClass, uint256 declaringClass, uint16 access,
        uint256 dynamicReceiverClass, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        if ((access & 0x0004) == 0 || callerClass == declaringClass
            || _samePackage(classes[callerClass], classes[declaringClass])) return;
        if (!_objectIsClass(dynamicReceiverClass, callerClass, parentLinks)) {
            revert CallError(4, pc);
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
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || uint8(ch) == 0) return false;
            if (ch == bytes1("/")) {
                if (slash) return false;
                slash = true;
            } else slash = false;
        }
        return true;
    }

    function _validateCastTarget(ClassInfo memory caller, uint256 refIndex, uint256 pc)
        private
        pure
        returns (uint8 kind, uint256 off, uint256 n)
    {
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (off, n) = _utf(caller.cp[nameIndex]);
        if (n != 0 && uint8(caller.data[off]) == 0x5b) {
            (bool structural, bool supported,,,,) = _arrayClassShape(caller.data, off, n);
            if (!structural) revert TypeError(1, pc);
            // Deferred primitive arrays retain the null shortcut and fail only for non-null.
            return (supported ? 2 : 3, off, n);
        }
        if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
        return (1, off, n);
    }

    function _arrayClassShape(bytes memory data, uint256 off, uint256 n)
        private
        pure
        returns (
            bool structural, bool supported, uint8 rank,
            uint8 primitiveLeaf, uint256 leafOffset, uint256 leafLength
        )
    {
        uint256 dimensions;
        while (dimensions < n && uint8(data[off + dimensions]) == 0x5b) {
            ++dimensions;
            if (dimensions > 255) return (false, false, 0, 0, 0, 0);
        }
        if (dimensions == 0 || dimensions >= n) return (false, false, 0, 0, 0, 0);
        rank = uint8(dimensions);
        uint8 component = uint8(data[off + dimensions]);
        if ((_isIntLike(component) || component == PRIMITIVE_LONG) && dimensions + 1 == n) {
            return (true, true, rank, component, 0, 0);
        }
        if (component == 0x4c) {
            if (dimensions + 2 >= n || uint8(data[off + n - 1]) != 0x3b) {
                return (false, false, 0, 0, 0, 0);
            }
            leafOffset = off + dimensions + 1;
            leafLength = n - dimensions - 2;
            if (!_validInternalName(data, leafOffset, leafLength)) {
                return (false, false, 0, 0, 0, 0);
            }
            return (true, true, rank, 0, leafOffset, leafLength);
        }
        if (dimensions + 1 != n) return (false, false, 0, 0, 0, 0);
        // IEEE primitive leaves remain structurally valid but unsupported.
        bool deferred = component == 0x44 || component == 0x46;
        return deferred ? (true, false, rank, 0, 0, 0)
            : (false, false, 0, 0, 0, 0);
    }

    function _resolveArrayClassType(
        ClassInfo[] memory classes, uint256 callerClass, bytes memory data,
        uint256 off, uint256 n, uint256 pc, uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        (bool structural, bool supported, uint8 rank, uint8 primitiveLeaf,
            uint256 leafOffset, uint256 leafLength) = _arrayClassShape(data, off, n);
        if (!structural) revert TypeError(1, pc);
        if (!supported) revert TypeError(2, pc);
        out.rank = rank;
        if (primitiveLeaf != 0) {
            out.leafType = primitiveLeaf;
            return out;
        }
        (bool found, uint256 leafClass) = _findClass(classes, data, leafOffset, leafLength);
        if (!found) revert LinkError(4, pc);
        ClassInfo memory leaf = classes[leafClass];
        if (leafClass != callerClass && !_classAccessible(classes[callerClass], leaf)) {
            revert TypeError(2, pc);
        }
        _validateHierarchy(classes, leafClass, parentLinks, hierarchyState);
        out.leafType = ARRAY_CLASS_BASE + leafClass;
    }

    function _resolveMultiArrayType(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint8 dimensions,
        uint256 pc, uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (n == 0 || uint8(caller.data[off]) != 0x5b) {
            if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
            revert ArrayError(3, pc);
        }
        (bool structural,, uint8 rank,,,) = _arrayClassShape(caller.data, off, n);
        if (!structural) revert TypeError(1, pc);
        if (dimensions == 0 || dimensions > rank) revert ArrayError(3, pc);
        return _resolveArrayClassType(
            classes, callerClass, caller.data, off, n, pc, parentLinks, hierarchyState
        );
    }

    function _planMultiArray(
        uint256[] memory counts, uint256 arrayCount, uint256 totalElements
    ) private pure returns (uint256 arrays, uint256 elements) {
        uint256 multiplicity = 1;
        for (uint256 level = 0; level < counts.length && multiplicity != 0; ++level) {
            // A zero return is an unambiguous OOM sentinel: every legal plan contains its root.
            if (multiplicity > MAX_ARRAYS - arrayCount - arrays) return (0, 0);
            uint256 length = counts[level];
            if (length > MAX_ARRAY_LENGTH) return (0, 0);
            uint256 remainingElements = MAX_ARRAY_ELEMENTS - totalElements - elements;
            if (length != 0 && multiplicity > remainingElements / length) return (0, 0);
            uint256 levelElements = multiplicity * length;
            arrays += multiplicity;
            elements += levelElements;
            // Only arrays reachable through actually materialized parent slots are planned.
            // Thus [0][huge] has one legal empty root while all counts were still validated.
            multiplicity = levelElements;
        }
    }

    function _allocateMultiArray(
        uint64[][] memory arrayHeap, uint8[] memory heapKinds,
        uint8[] memory arrayRanks, uint256[] memory arrayLeafTypes,
        uint256 nextHandle, ArrayType memory allocatedType, uint256[] memory counts
    ) private pure returns (uint256) {
        uint256 multiplicity = 1;
        uint256 previousStart;
        for (uint256 level = 0; level < counts.length && multiplicity != 0; ++level) {
            uint256 currentStart = nextHandle + 1;
            uint256 length = counts[level];
            for (uint256 i = 0; i < multiplicity; ++i) {
                ++nextHandle;
                heapKinds[nextHandle] = HEAP_ARRAY;
                arrayRanks[nextHandle] = allocatedType.rank - uint8(level);
                arrayLeafTypes[nextHandle] = allocatedType.leafType;
                arrayHeap[nextHandle] = new uint64[](length);
                if (level != 0) {
                    uint256 parentLength = counts[level - 1];
                    uint256 parent = previousStart + i / parentLength;
                    arrayHeap[parent][i % parentLength] = uint32(nextHandle);
                }
            }
            previousStart = currentStart;
            multiplicity *= length; // bounded by the successful quota preflight
        }
        return nextHandle;
    }

    function _resolveANewArrayType(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (n != 0 && uint8(caller.data[off]) == 0x5b) {
            ArrayType memory component = _resolveArrayClassType(
                classes, callerClass, caller.data, off, n, pc, parentLinks, hierarchyState
            );
            if (component.rank == 255) revert ArrayError(2, pc);
            out.rank = component.rank + 1;
            out.leafType = component.leafType;
            return out;
        }
        if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
        (bool found, uint256 componentClass) = _findClass(classes, caller.data, off, n);
        if (!found) revert LinkError(4, pc);
        ClassInfo memory componentClassInfo = classes[componentClass];
        if (componentClass != callerClass && !_classAccessible(caller, componentClassInfo)) {
            revert TypeError(2, pc);
        }
        _validateHierarchy(classes, componentClass, parentLinks, hierarchyState);
        out.rank = 1;
        out.leafType = ARRAY_CLASS_BASE + componentClass;
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
                    values[cursor] = kind == KIND_INT ? _packInt(0)
                        : (kind == KIND_LONG ? _packLong(0)
                            : (kind == KIND_FLOAT ? _packFloat(0)
                                : (kind == KIND_DOUBLE ? _packDouble(0) : _packRef(0))));
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

    function _interfaceExtends(
        ClassInfo[] memory classes, uint256 child, uint256 wanted
    ) private pure returns (bool) {
        bool[] memory seen = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        seen[child] = true;
        queue[tail++] = child;
        while (head < tail) {
            uint256 current = queue[head++];
            if (current == wanted) return true;
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 parent = _resolveInterfaceEdge(classes, current, i);
                if (!seen[parent]) {
                    seen[parent] = true;
                    queue[tail++] = parent;
                }
            }
        }
        return false;
    }

    function _classImplements(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 wanted,
        uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 current = dynamicClass;
        while (true) {
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, current, i);
                if (_interfaceExtends(classes, direct, wanted)) return true;
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return false;
            current = link - 1;
        }
    }

    function _typeAssignable(
        ClassInfo[] memory classes, uint256 actual, uint256 wanted,
        uint256[] memory parentLinks
    ) private pure returns (bool) {
        if (_isInterface(classes[wanted])) {
            return _isInterface(classes[actual])
                ? _interfaceExtends(classes, actual, wanted)
                : _classImplements(classes, actual, wanted, parentLinks);
        }
        if (_isInterface(classes[actual])) return _isObjectClass(classes[wanted]);
        return _objectIsClass(actual, wanted, parentLinks);
    }

    function _arrayImplementsClass(ClassInfo[] memory classes, uint256 wanted)
        private pure returns (bool)
    {
        if (_isObjectClass(classes[wanted])) return true;
        bool wantedMarker = _isNamedClass(classes[wanted], bytes("java/lang/Cloneable"))
            || _isNamedClass(classes[wanted], bytes("java/io/Serializable"));
        if (!_isInterface(classes[wanted])) {
            if (wantedMarker) revert InterfaceError(1, wanted);
            return false;
        }

        // Array classes directly implement the two canonical marker interfaces. Their
        // ordinary superinterface closure applies too when a supplied marker extends
        // another interface; checking only the two marker names loses that assignability.
        bool assignable;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!_isNamedClass(classes[i], bytes("java/lang/Cloneable"))
                && !_isNamedClass(classes[i], bytes("java/io/Serializable"))) continue;
            if (!_isInterface(classes[i])) revert InterfaceError(1, i);
            _validateInterfaceClosure(classes, i, new uint256[](classes.length));
            if (_interfaceExtends(classes, i, wanted)) assignable = true;
        }
        return assignable;
    }

    function _arrayHasReferenceComponents(uint8 rank, uint256 leafType)
        private pure returns (bool)
    {
        return rank > 1 || leafType >= ARRAY_CLASS_BASE;
    }

    function _arrayTypeAssignable(
        ClassInfo[] memory classes, uint8 actualRank, uint256 actualLeafType,
        uint8 wantedRank, uint256 wantedLeafType, uint256[] memory parentLinks
    ) private pure returns (bool) {
        if (wantedLeafType < ARRAY_CLASS_BASE) {
            return actualLeafType == wantedLeafType && actualRank == wantedRank;
        }
        if (actualRank < wantedRank) return false;
        uint256 wantedClass = wantedLeafType - ARRAY_CLASS_BASE;
        if (actualRank > wantedRank) return _arrayImplementsClass(classes, wantedClass);
        return actualLeafType >= ARRAY_CLASS_BASE
            && _typeAssignable(
                classes, actualLeafType - ARRAY_CLASS_BASE, wantedClass, parentLinks
            );
    }

    function _valueFitsArrayComponent(
        ClassInfo[] memory classes, uint256 value, uint8 arrayRank,
        uint256 arrayLeafType, uint8[] memory heapKinds,
        uint256[] memory heapClasses, uint8[] memory arrayRanks,
        uint256[] memory arrayLeafTypes, uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 handle = _payload(value);
        if (handle == 0) return true;
        if (arrayRank > 1) {
            return heapKinds[handle] == HEAP_ARRAY && _arrayTypeAssignable(
                classes, arrayRanks[handle], arrayLeafTypes[handle],
                arrayRank - 1, arrayLeafType, parentLinks
            );
        }
        // A rank-one reference array has a class or interface component.
        uint256 wantedClass = arrayLeafType - ARRAY_CLASS_BASE;
        if (heapKinds[handle] == HEAP_ARRAY) return _arrayImplementsClass(classes, wantedClass);
        return heapKinds[handle] == HEAP_OBJECT
            && _typeAssignable(classes, heapClasses[handle], wantedClass, parentLinks);
    }

    function _requireAssignable(
        ClassInfo[] memory classes, uint256 value, bytes memory descriptorData,
        uint256 descriptorOffset, uint256 descriptorLength, uint8[] memory heapKinds,
        uint256[] memory heapClasses, uint8[] memory arrayRanks,
        uint256[] memory arrayLeafTypes, uint256 nextHandle,
        uint256[] memory parentLinks, uint256 pc
    ) private pure {
        _requireKind(value, KIND_REF, pc);
        uint256 handle = _payload(value);
        if (handle == 0) return;
        if (handle > nextHandle || heapKinds[handle] == 0) revert ReferenceError(1, pc);
        if (descriptorLength != 0 && uint8(descriptorData[descriptorOffset]) == 0x5b) {
            (bool structural, bool supported, uint8 wantedRank, uint8 primitiveLeaf,
                uint256 leafOffset, uint256 leafLength) = _arrayClassShape(
                    descriptorData, descriptorOffset, descriptorLength
                );
            if (!structural || !supported) revert ReferenceError(2, pc);
            if (heapKinds[handle] != HEAP_ARRAY) revert ReferenceError(1, pc);
            uint256 wantedLeafType = primitiveLeaf;
            if (primitiveLeaf == 0) {
                (bool found, uint256 wantedLeafClass) = _findClass(
                    classes, descriptorData, leafOffset, leafLength
                );
                if (!found) revert LinkError(4, pc);
                _validateHierarchy(
                    classes, wantedLeafClass, parentLinks, new uint8[](classes.length)
                );
                wantedLeafType = ARRAY_CLASS_BASE + wantedLeafClass;
            }
            if (!_arrayTypeAssignable(
                classes, arrayRanks[handle], arrayLeafTypes[handle],
                wantedRank, wantedLeafType, parentLinks
            )) revert ReferenceError(2, pc);
            return;
        }
        if (descriptorLength < 3 || uint8(descriptorData[descriptorOffset]) != 0x4c
            || uint8(descriptorData[descriptorOffset + descriptorLength - 1]) != 0x3b) {
            revert ReferenceError(2, pc);
        }
        uint256 nameOffset = descriptorOffset + 1;
        uint256 nameLength = descriptorLength - 2;
        (bool found, uint256 wantedClass) = _findClass(classes, descriptorData, nameOffset, nameLength);
        if (!found) revert LinkError(4, pc);
        _validateHierarchy(classes, wantedClass, parentLinks, new uint8[](classes.length));
        if (heapKinds[handle] == HEAP_ARRAY) {
            if (_isObjectClass(classes[wantedClass])) return;
            if (!_isInterface(classes[wantedClass])) revert ReferenceError(1, pc);
            if (!_arrayImplementsClass(classes, wantedClass)) revert ReferenceError(2, pc);
            return;
        }
        if (heapKinds[handle] != HEAP_OBJECT) revert ReferenceError(1, pc);
        if (!_typeAssignable(classes, heapClasses[handle], wantedClass, parentLinks)) {
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
            uint256 width = _instructionWidth(c.data, s.codeOffset, s.codeLength, op, pc);
            if (width > s.codeLength - pc) revert BytecodeError(2, pc);
            if (
                (op == 0xac && s.returnKind != 1) || (op == 0xad && s.returnKind != 4)
                    || (op == 0xae && s.returnKind != 5) || (op == 0xaf && s.returnKind != 6)
                    || (op == 0xb1 && s.returnKind != 2) || (op == 0xb0 && s.returnKind != 3)
            ) revert CallError(5, pc);
            if (op == 0xbc && _newArrayPrimitive(uint8(c.data[s.codeOffset + pc + 1])) == 0) {
                revert ArrayError(1, pc);
            }
            if (op == 0x12 || op == 0x13 || op == 0x14) {
                uint256 index = op == 0x12
                    ? uint8(c.data[s.codeOffset + pc + 1])
                    : _unsigned16(c.data, s.codeOffset + pc + 1);
                uint8 tag = index < c.cp.length ? uint8(c.cp[index]) : 0;
                bool validTag = op == 0x14 ? (tag == 5 || tag == 6) : (tag == 3 || tag == 4);
                if (index == 0 || !validTag) {
                    revert BytecodeError(13, pc);
                }
            }
            pc += width;
        }
        // The first pass has already decoded and validated every instruction's
        // width. Walk its start map directly for edge validation rather than
        // decoding every instruction a second time. Operand and switch-payload
        // bytes remain untrusted, but are ignored unless the first pass marked
        // them as actual instruction starts.
        for (pc = 0; pc < s.codeLength; ++pc) {
            if (!starts[pc]) continue;
            uint8 op = uint8(c.data[s.codeOffset + pc]);
            if ((op >= 0x99 && op <= 0xa7) || op == 0xc6 || op == 0xc7) {
                _requireDecodedTarget(
                    _decodedTarget(c.data, s.codeOffset, pc), starts, s.codeLength, pc
                );
            } else if (op == 0xc8) {
                _requireDecodedTarget(
                    _decodedWideTarget(c.data, s.codeOffset, pc, pc + 1),
                    starts, s.codeLength, pc
                );
            } else if (op == 0xaa || op == 0xab) {
                _validateSwitchTargets(c.data, s.codeOffset, s.codeLength, pc, starts, op == 0xab);
            }
        }
    }

    function _instructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint8 op, uint256 pc
    ) private pure returns (uint256) {
        if (op == 0xaa || op == 0xab) {
            return _switchInstructionWidth(data, codeOffset, codeLength, pc, op == 0xab);
        }
        if (op == 0xc4) return _wideInstructionWidth(data, codeOffset, codeLength, pc);
        if (
            op <= 0x01 || (op >= 0x02 && op <= 0x0f) || (op >= 0x1a && op <= 0x2f)
                || (op >= 0x32 && op <= 0x35) || (op >= 0x3b && op <= 0x50)
                || (op >= 0x53 && op <= 0x56)
                || (op >= 0x57 && op <= 0x61) || (op >= 0x64 && op <= 0x65)
                || (op >= 0x68 && op <= 0x69) || (op >= 0x6c && op <= 0x6d)
                || (op >= 0x70 && op <= 0x71) || (op >= 0x74 && op <= 0x77)
                || (op >= 0x78 && op <= 0x83) || (op >= 0x85 && op <= 0x98)
                || (op >= 0xac && op <= 0xb1) || op == 0xbe
        ) return 1;
        if (op == 0x10 || op == 0x12 || (op >= 0x15 && op <= 0x19)
            || (op >= 0x36 && op <= 0x3a) || op == 0xbc) return 2;
        if (
            op == 0x11 || op == 0x13 || op == 0x14 || op == 0x84 || (op >= 0x99 && op <= 0xa7)
                || op == 0xb2 || op == 0xb3 || op == 0xb4 || op == 0xb5
                || op == 0xb6 || op == 0xb7 || op == 0xb8 || op == 0xbb || op == 0xbd
                || op == 0xc0 || op == 0xc1 || op == 0xc6 || op == 0xc7
        ) return 3;
        if (op == 0xc5) return 4;
        if (op == 0xb9 || op == 0xc8) return 5;
        revert BytecodeError(6, pc);
    }

    function _switchInstructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc, bool lookup
    ) private pure returns (uint256) {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 header = 1 + padding;
        uint256 fixedSize = lookup ? 8 : 12;
        uint256 remaining = codeLength - pc;
        if (header > remaining || fixedSize > remaining - header) revert BytecodeError(2, pc);
        uint256 at = codeOffset + pc + header;
        if (lookup) {
            int32 signedPairs = _signed32(data, at + 4);
            if (signedPairs < 0) revert BytecodeError(15, pc);
            uint256 pairs = uint256(uint32(signedPairs));
            uint256 payloadRemaining = remaining - header - fixedSize;
            if (pairs > payloadRemaining / 8) revert BytecodeError(2, pc);
            if (pairs != 0) {
                int32 prior = _signed32(data, at + 8);
                for (uint256 i = 1; i < pairs; ++i) {
                    int32 key = _signed32(data, at + 8 + i * 8);
                    if (key <= prior) revert BytecodeError(15, pc);
                    prior = key;
                }
            }
            return header + fixedSize + pairs * 8;
        }
        int32 low = _signed32(data, at + 4);
        int32 high = _signed32(data, at + 8);
        if (low > high) revert BytecodeError(15, pc);
        uint256 count = uint256(int256(high) - int256(low) + 1);
        uint256 payloadRemaining = remaining - header - fixedSize;
        if (count > payloadRemaining / 4) revert BytecodeError(2, pc);
        return header + fixedSize + count * 4;
    }

    function _wideInstructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc
    ) private pure returns (uint256) {
        uint256 remaining = codeLength - pc;
        if (remaining < 2) revert BytecodeError(2, pc);
        uint8 embedded = uint8(data[codeOffset + pc + 1]);
        bool supported = (embedded >= 0x15 && embedded <= 0x19)
            || (embedded >= 0x36 && embedded <= 0x3a) || embedded == 0x84;
        bool recognizedUnsupported = embedded == 0xa9;
        if (!supported && !recognizedUnsupported) revert BytecodeError(15, pc);
        uint256 width = embedded == 0x84 ? 6 : 4;
        if (width > remaining) revert BytecodeError(2, pc);
        if (recognizedUnsupported) revert BytecodeError(6, pc);
        return width;
    }

    function _validateSwitchTargets(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc,
        bool[] memory starts, bool lookup
    ) private pure {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 at = pc + 1 + padding;
        _requireDecodedTarget(
            _decodedWideTarget(data, codeOffset, pc, at), starts, codeLength, pc
        );
        if (lookup) {
            uint256 pairs = uint256(uint32(_signed32(data, codeOffset + at + 4)));
            for (uint256 i = 0; i < pairs; ++i) {
                _requireDecodedTarget(
                    _decodedWideTarget(data, codeOffset, pc, at + 12 + i * 8),
                    starts, codeLength, pc
                );
            }
        } else {
            int32 low = _signed32(data, codeOffset + at + 4);
            int32 high = _signed32(data, codeOffset + at + 8);
            uint256 count = uint256(int256(high) - int256(low) + 1);
            for (uint256 i = 0; i < count; ++i) {
                _requireDecodedTarget(
                    _decodedWideTarget(data, codeOffset, pc, at + 12 + i * 4),
                    starts, codeLength, pc
                );
            }
        }
    }

    function _requireDecodedTarget(
        uint256 target, bool[] memory starts, uint256 codeLength, uint256 pc
    ) private pure {
        if (target >= codeLength || !starts[target]) revert BytecodeError(12, pc);
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
            s.argumentWords += _isCategory2Kind(kind) ? 2 : 1;
            i += width;
            ++at;
        }
        uint256 resultOff = off + close + 1;
        if (resultOff >= off + n) return false;
        uint8 result = uint8(data[resultOff]);
        if (resultOff + 1 == off + n && _isIntLike(result)) {
            s.returnKind = 1;
            s.returnSubtype = result;
        } else if (resultOff + 1 == off + n && result == PRIMITIVE_LONG) s.returnKind = 4;
        else if (resultOff + 1 == off + n && result == PRIMITIVE_FLOAT) s.returnKind = 5;
        else if (resultOff + 1 == off + n && result == PRIMITIVE_DOUBLE) s.returnKind = 6;
        else if (resultOff + 1 == off + n && result == 0x56) s.returnKind = 2;
        else {
            (bool ok, uint256 width, uint8 kind) = _descriptorType(data, resultOff, off + n, false);
            if (!ok || kind != KIND_REF || resultOff + width != off + n) return false;
            s.returnKind = 3;
            s.returnTypeOffset = resultOff;
            s.returnTypeLength = width;
        }
        return true;
    }

    function _isExactIntRoot(ClassInfo memory c, Selected memory s)
        private pure returns (bool)
    {
        if (s.returnKind != 1 || s.returnSubtype != PRIMITIVE_INT) return false;
        for (uint256 i = 0; i < s.argumentKinds.length; ++i) {
            if (s.argumentKinds[i] != KIND_INT || s.argumentTypeLengths[i] != 1
                || uint8(c.data[s.argumentTypeOffsets[i]]) != PRIMITIVE_INT) return false;
        }
        return true;
    }

    function _isIntLike(uint8 descriptor) private pure returns (bool) {
        return descriptor == PRIMITIVE_INT || descriptor == PRIMITIVE_BOOLEAN
            || descriptor == PRIMITIVE_BYTE || descriptor == PRIMITIVE_CHAR
            || descriptor == PRIMITIVE_SHORT;
    }

    function _descriptorType(bytes memory data, uint256 off, uint256 end, bool allowVoid)
        private
        pure
        returns (bool ok, uint256 width, uint8 kind)
    {
        if (off >= end) return (false, 0, 0);
        uint8 b = uint8(data[off]);
        if (_isIntLike(b)) return (true, 1, uint8(KIND_INT));
        if (b == PRIMITIVE_LONG) return (true, 1, uint8(KIND_LONG));
        if (b == PRIMITIVE_FLOAT) return (true, 1, uint8(KIND_FLOAT));
        if (b == PRIMITIVE_DOUBLE) return (true, 1, uint8(KIND_DOUBLE));
        if (allowVoid && b == 0x56) return (true, 1, 0);
        if (b == 0x5b) {
            uint256 dimensions;
            while (off + dimensions < end && uint8(data[off + dimensions]) == 0x5b) {
                ++dimensions;
                if (dimensions > 255) return (false, 0, 0);
            }
            if (off + dimensions >= end) return (false, 0, 0);
            uint8 leaf = uint8(data[off + dimensions]);
            if (_isIntLike(leaf) || leaf == PRIMITIVE_LONG
                || leaf == PRIMITIVE_FLOAT || leaf == PRIMITIVE_DOUBLE) {
                return (true, dimensions + 1, uint8(KIND_REF));
            }
            if (leaf != 0x4c) return (false, 0, 0);
            uint256 i = off + dimensions + 1;
            while (i < end && uint8(data[i]) != 0x3b) ++i;
            if (i == off + dimensions + 1 || i >= end
                || !_validInternalName(data, off + dimensions + 1, i - off - dimensions - 1)) {
                return (false, 0, 0);
            }
            return (true, i - off + 1, uint8(KIND_REF));
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

    function _decodedWideTarget(
        bytes memory data, uint256 codeOffset, uint256 pc, uint256 offsetPC
    ) private pure returns (uint256) {
        int256 target = int256(pc) + int256(_signed32(data, codeOffset + offsetPC));
        if (target < 0 || target > int256(MAX_CODE)) revert BytecodeError(12, pc);
        return uint256(target);
    }

    function _decodedSwitchTarget(
        bytes memory data, uint256 codeOffset, uint256 pc, int32 key, bool lookup
    ) private pure returns (uint256) {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 at = pc + 1 + padding;
        uint256 offsetPC = at;
        if (lookup) {
            uint256 pairs = uint256(uint32(_signed32(data, codeOffset + at + 4)));
            for (uint256 i = 0; i < pairs; ++i) {
                int32 candidate = _signed32(data, codeOffset + at + 8 + i * 8);
                if (candidate == key) {
                    offsetPC = at + 12 + i * 8;
                    break;
                }
                if (candidate > key) break;
            }
        } else {
            int32 low = _signed32(data, codeOffset + at + 4);
            int32 high = _signed32(data, codeOffset + at + 8);
            if (key >= low && key <= high) {
                offsetPC = at + 12 + uint256(int256(key) - int256(low)) * 4;
            }
        }
        return _decodedWideTarget(data, codeOffset, pc, offsetPC);
    }

    function _signed16(bytes memory data, uint256 off) private pure returns (int16) {
        return int16(_unsigned16(data, off));
    }

    function _signed32(bytes memory data, uint256 off) private pure returns (int32) {
        return int32(_unsigned32(data, off));
    }

    function _unsigned16(bytes memory data, uint256 off) private pure returns (uint16) {
        return (uint16(uint8(data[off])) << 8) | uint16(uint8(data[off + 1]));
    }

    function _unsigned32(bytes memory data, uint256 off) private pure returns (uint32) {
        return (uint32(uint8(data[off])) << 24) | (uint32(uint8(data[off + 1])) << 16)
            | (uint32(uint8(data[off + 2])) << 8) | uint32(uint8(data[off + 3]));
    }

    function _highestBit(uint64 value) private pure returns (uint256 bit) {
        // All callers exclude zero; this loop is bounded by the 64-bit value representation.
        while (value > 1) {
            value >>= 1;
            ++bit;
        }
    }

    function _roundRightEven(uint64 value, uint256 shift) private pure returns (uint64) {
        if (shift == 0) return value;
        if (shift > 64) return 0;
        if (shift == 64) {
            uint64 half64 = uint64(1) << 63;
            return value > half64 ? 1 : 0; // an exact half rounds to the even zero
        }
        uint64 quotient = value >> shift;
        uint64 mask = (uint64(1) << shift) - 1;
        uint64 remainder = value & mask;
        uint64 half = uint64(1) << (shift - 1);
        if (remainder > half || (remainder == half && (quotient & 1) != 0)) ++quotient;
        return quotient;
    }

    function _signedIntegerToIEEE(
        uint64 raw, uint256 width, uint256 precision, uint256 bias, uint256 fractionBits
    ) private pure returns (uint64) {
        uint64 signBit = width == 32 ? uint64(1) << 31 : uint64(1) << 63;
        uint64 widthMask = width == 32 ? uint64(type(uint32).max) : type(uint64).max;
        raw &= widthMask;
        bool negative = (raw & signBit) != 0;
        uint64 magnitude;
        unchecked { magnitude = negative ? ((~raw & widthMask) + 1) : raw; }
        if (magnitude == 0) return 0;
        uint256 exponent = _highestBit(magnitude);
        uint64 significand;
        if (exponent + 1 > precision) {
            significand = _roundRightEven(magnitude, exponent + 1 - precision);
        } else {
            significand = magnitude << (precision - exponent - 1);
        }
        if (significand == (uint64(1) << precision)) {
            significand >>= 1;
            ++exponent;
        }
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint64 sign = negative ? uint64(1) << (fractionBits + (fractionBits == 23 ? 8 : 11)) : 0;
        return sign | (uint64(exponent + bias) << fractionBits) | (significand & fractionMask);
    }

    function _ieeeToSignedInteger(
        uint64 raw, uint256 exponentBits, uint256 fractionBits, uint256 targetBits
    ) private pure returns (uint64) {
        uint256 signShift = exponentBits + fractionBits;
        bool negative = ((raw >> signShift) & 1) != 0;
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint64 fraction = raw & fractionMask;
        uint256 exponentMask = (uint256(1) << exponentBits) - 1;
        uint256 encodedExponent = (uint256(raw) >> fractionBits) & exponentMask;
        uint64 minimum = uint64(1) << (targetBits - 1);
        uint64 maximum = minimum - 1;
        if (encodedExponent == exponentMask) {
            if (fraction != 0) return 0;
            return negative ? minimum : maximum;
        }
        int256 exponent = encodedExponent == 0
            ? int256(1) - int256(exponentMask >> 1)
            : int256(encodedExponent) - int256(exponentMask >> 1);
        if (exponent < 0) return 0;
        if (exponent >= int256(targetBits - 1)) return negative ? minimum : maximum;
        uint64 significand = encodedExponent == 0
            ? fraction : ((uint64(1) << fractionBits) | fraction);
        uint64 magnitude = uint256(exponent) >= fractionBits
            ? significand << (uint256(exponent) - fractionBits)
            : significand >> (fractionBits - uint256(exponent));
        if (!negative) return magnitude;
        unchecked { return ~magnitude + 1; }
    }

    function _floatToDoubleBits(uint32 raw) private pure returns (uint64) {
        uint64 sign = (uint64(raw >> 31)) << 63;
        uint256 encodedExponent = (raw >> 23) & 0xff;
        uint64 fraction = uint64(raw & 0x7fffff);
        if (encodedExponent == 0xff) {
            if (fraction != 0) return 0x7ff8000000000000;
            return sign | 0x7ff0000000000000;
        }
        if (encodedExponent == 0) {
            if (fraction == 0) return sign;
            uint256 top = _highestBit(fraction);
            int256 exponent = int256(top) - 149;
            uint64 normalized = fraction << (52 - top);
            return sign | (uint64(uint256(exponent + 1023)) << 52)
                | (normalized & 0x000fffffffffffff);
        }
        return sign | (uint64(encodedExponent - 127 + 1023) << 52) | (fraction << 29);
    }

    function _doubleToFloatBits(uint64 raw) private pure returns (uint32) {
        uint32 sign = uint32(raw >> 63) << 31;
        uint256 encodedExponent = (raw >> 52) & 0x7ff;
        uint64 fraction = raw & 0x000fffffffffffff;
        if (encodedExponent == 0x7ff) {
            if (fraction != 0) return 0x7fc00000;
            return sign | 0x7f800000;
        }
        uint64 significand;
        int256 scale;
        if (encodedExponent == 0) {
            if (fraction == 0) return sign;
            significand = fraction;
            scale = -1074;
        } else {
            significand = (uint64(1) << 52) | fraction;
            scale = int256(encodedExponent) - 1023 - 52;
        }
        uint256 top = _highestBit(significand);
        int256 exponent = int256(top) + scale;
        if (exponent >= -126) {
            uint64 rounded = top > 23
                ? _roundRightEven(significand, top - 23)
                : significand << (23 - top);
            if (rounded == (uint64(1) << 24)) {
                rounded >>= 1;
                ++exponent;
            }
            if (exponent > 127) return sign | 0x7f800000;
            return sign | (uint32(uint256(exponent + 127)) << 23)
                | uint32(rounded & 0x7fffff);
        }
        int256 subnormalShift = scale + 149;
        uint64 subnormal = subnormalShift >= 0
            ? significand << uint256(subnormalShift)
            : _roundRightEven(significand, uint256(-subnormalShift));
        if (subnormal >= (uint64(1) << 23)) return sign | 0x00800000;
        return sign | uint32(subnormal);
    }

    function _compareIEEE(
        uint64 left, uint64 right, uint256 exponentBits, uint256 fractionBits, bool nanLow
    ) private pure returns (int8) {
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint256 exponentMask = (uint256(1) << exponentBits) - 1;
        bool leftNaN = ((uint256(left) >> fractionBits) & exponentMask) == exponentMask
            && (left & fractionMask) != 0;
        bool rightNaN = ((uint256(right) >> fractionBits) & exponentMask) == exponentMask
            && (right & fractionMask) != 0;
        if (leftNaN || rightNaN) return nanLow ? int8(-1) : int8(1);
        uint64 signBit = uint64(1) << (exponentBits + fractionBits);
        uint64 magnitudeMask = signBit - 1;
        uint64 leftMagnitude = left & magnitudeMask;
        uint64 rightMagnitude = right & magnitudeMask;
        if (leftMagnitude == 0 && rightMagnitude == 0) return 0;
        if (left == right) return 0;
        bool leftNegative = (left & signBit) != 0;
        bool rightNegative = (right & signBit) != 0;
        if (leftNegative != rightNegative) return leftNegative ? int8(-1) : int8(1);
        if (!leftNegative) return leftMagnitude < rightMagnitude ? int8(-1) : int8(1);
        return leftMagnitude > rightMagnitude ? int8(-1) : int8(1);
    }

    function _newArrayPrimitive(uint8 atype) private pure returns (uint8) {
        if (atype == 4) return PRIMITIVE_BOOLEAN;
        if (atype == 5) return PRIMITIVE_CHAR;
        if (atype == 8) return PRIMITIVE_BYTE;
        if (atype == 9) return PRIMITIVE_SHORT;
        if (atype == 10) return PRIMITIVE_INT;
        if (atype == 11) return PRIMITIVE_LONG;
        return 0;
    }

    function _normalizeInt(uint32 value, uint8 subtype) private pure returns (uint32) {
        if (subtype == PRIMITIVE_BYTE) return uint32(int32(int8(uint8(value))));
        if (subtype == PRIMITIVE_CHAR) return uint32(uint16(value));
        if (subtype == PRIMITIVE_SHORT) return uint32(int32(int16(uint16(value))));
        if (subtype == PRIMITIVE_BOOLEAN) return value & 1;
        return value; // I
    }

    function _normalizePackedInt(uint256 value, uint8 subtype) private pure returns (uint256) {
        return _packInt(_normalizeInt(uint32(_payload(value)), subtype));
    }

    function _packInt(uint32 value) private pure returns (uint256) {
        return (KIND_INT << KIND_SHIFT) | uint256(value);
    }

    function _packRef(uint32 handle) private pure returns (uint256) {
        return (KIND_REF << KIND_SHIFT) | uint256(handle);
    }

    function _packLong(uint64 value) private pure returns (uint256) {
        return (KIND_LONG << KIND_SHIFT) | uint256(value);
    }

    function _packFloat(uint32 value) private pure returns (uint256) {
        return (KIND_FLOAT << KIND_SHIFT) | uint256(value);
    }

    function _packDouble(uint64 value) private pure returns (uint256) {
        return (KIND_DOUBLE << KIND_SHIFT) | uint256(value);
    }

    function _payload(uint256 value) private pure returns (uint256) {
        return uint64(value);
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

    function _requireLongPair(uint256[] memory stack, uint256 sp, uint256 pc) private pure {
        _requireKind(stack[sp - 2], KIND_LONG, pc);
        _requireKind(stack[sp - 1], KIND_LONG, pc);
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
        // JVM Error subclasses escape initialization unchanged. Ordinary runtime
        // exceptions are wrapped as ExceptionInInitializerError.
        if (kind != 2 && kind != 7 && kind != 10 && kind != 11
            && _hasActiveInitializer(frames, depth)) {
            revert JavaException(3);
        }
        revert JavaException(kind);
    }

    function _push(uint256[] memory stack, uint256 sp, uint256 value, uint256 pc)
        private
        pure
        returns (uint256)
    {
        uint256 words = _stackWords(stack, sp);
        uint256 added = _isCategory2Kind(_valueKind(value)) ? 2 : 1;
        if (words > stack.length || added > stack.length - words) revert BytecodeError(9, pc);
        stack[sp] = value;
        return sp + 1;
    }

    function _stackWords(uint256[] memory stack, uint256 sp) private pure returns (uint256 words) {
        for (uint256 i = 0; i < sp; ++i) {
            words += _isCategory2Kind(_valueKind(stack[i])) ? 2 : 1;
        }
    }

    function _isCategory1(uint256 value) private pure returns (bool) {
        uint256 kind = _valueKind(value);
        return kind == KIND_INT || kind == KIND_REF || kind == KIND_UNINIT
            || kind == KIND_FLOAT;
    }

    function _isCategory2Kind(uint256 kind) private pure returns (bool) {
        return kind == KIND_LONG || kind == KIND_DOUBLE;
    }

    function _loadLong(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], KIND_LONG, pc);
        if (!initialized[local + 1]) revert BytecodeError(11, pc);
        _requireKind(locals[local + 1], KIND_LONG_TAIL, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeLong(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        return _storeCategory2(
            stack, sp, locals, initialized, local, KIND_LONG, KIND_LONG_TAIL, pc
        );
    }

    function _loadDouble(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], KIND_DOUBLE, pc);
        if (!initialized[local + 1]) revert BytecodeError(11, pc);
        _requireKind(locals[local + 1], KIND_DOUBLE_TAIL, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeDouble(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        return _storeCategory2(
            stack, sp, locals, initialized, local, KIND_DOUBLE, KIND_DOUBLE_TAIL, pc
        );
    }

    function _storeCategory2(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 kind, uint256 tail, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        _requireKind(stack[sp - 1], kind, pc);
        _invalidateLocal(locals, initialized, local);
        _invalidateLocal(locals, initialized, local + 1);
        locals[local] = stack[sp - 1];
        locals[local + 1] = tail << KIND_SHIFT;
        initialized[local] = true;
        initialized[local + 1] = true;
        return sp - 1;
    }

    function _copyArguments(
        Frame memory child, Selected memory target, uint256[] memory stack,
        uint256 stackAt, uint256 localAt
    ) private pure {
        for (uint256 i = 0; i < target.argumentCount; ++i) {
            uint256 value = stack[stackAt + i];
            child.locals[localAt] = value;
            child.initialized[localAt] = true;
            if (_isCategory2Kind(target.argumentKinds[i])) {
                child.locals[localAt + 1] = (target.argumentKinds[i] == KIND_LONG
                    ? KIND_LONG_TAIL : KIND_DOUBLE_TAIL) << KIND_SHIFT;
                child.initialized[localAt + 1] = true;
                localAt += 2;
            } else {
                ++localAt;
            }
        }
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
        _invalidateLocal(locals, initialized, local);
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
        _invalidateLocal(locals, initialized, local);
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

    function _permuteStack(uint256[] memory stack, uint256 sp, uint8 op, uint256 pc)
        private pure returns (uint256)
    {
        if (sp == 0) revert BytecodeError(3, pc);
        uint256 v1 = stack[sp - 1];
        bool c1 = _isCategory1(v1);
        bool c2 = _isCategory2Kind(_valueKind(v1));
        if (!c1 && !c2) revert BytecodeError(14, pc);

        if (op == 0x58) { // pop2: one category-2 or two category-1 values
            if (c2) return sp - 1;
            if (sp < 2) revert BytecodeError(3, pc);
            if (!_isCategory1(stack[sp - 2])) revert BytecodeError(14, pc);
            return sp - 2;
        }
        if (op == 0x59) { // dup
            if (!c1) revert BytecodeError(14, pc);
            return _push(stack, sp, v1, pc);
        }
        if (op == 0x5a || op == 0x5f) { // dup_x1 / swap: two category-1 values
            if (!c1) revert BytecodeError(14, pc);
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (op == 0x5f) {
                stack[sp - 2] = v1;
                stack[sp - 1] = v2;
                return sp;
            }
            _requireExtraWords(stack, sp, 1, pc);
            stack[sp - 2] = v1;
            stack[sp - 1] = v2;
            stack[sp] = v1;
            return sp + 1;
        }
        if (op == 0x5b) { // dup_x2: c,b,a or A,a (bottom to top)
            if (!c1) revert BytecodeError(14, pc);
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (_isCategory2Kind(_valueKind(v2))) {
                _requireExtraWords(stack, sp, 1, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 1, pc);
            stack[sp - 3] = v1; stack[sp - 2] = v3;
            stack[sp - 1] = v2; stack[sp] = v1;
            return sp + 1;
        }
        if (op == 0x5c) { // dup2: A or b,a
            if (c2) {
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp] = v1;
                return sp + 1;
            }
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        if (op == 0x5d) { // dup2_x1: a,A or c,b,a
            if (c2) {
                if (sp < 2) revert BytecodeError(3, pc);
                uint256 v2 = stack[sp - 2];
                if (!_isCategory1(v2)) revert BytecodeError(14, pc);
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v2; stack[sp - 2] = v1; stack[sp - 1] = v3;
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        // dup2_x2, all four JVMS forms.
        if (c2) {
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (_isCategory2Kind(_valueKind(v2))) {
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v1; stack[sp - 2] = v3;
            stack[sp - 1] = v2; stack[sp] = v1;
            return sp + 1;
        }
        if (sp < 2) revert BytecodeError(3, pc);
        uint256 v2 = stack[sp - 2];
        if (!_isCategory1(v2)) revert BytecodeError(14, pc);
        if (sp < 3) revert BytecodeError(3, pc);
        uint256 v3 = stack[sp - 3];
        if (_isCategory2Kind(_valueKind(v3))) {
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v2; stack[sp - 2] = v1; stack[sp - 1] = v3;
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        if (!_isCategory1(v3)) revert BytecodeError(14, pc);
        if (sp < 4) revert BytecodeError(3, pc);
        uint256 v4 = stack[sp - 4];
        if (!_isCategory1(v4)) revert BytecodeError(14, pc);
        _requireExtraWords(stack, sp, 2, pc);
        stack[sp - 4] = v2; stack[sp - 3] = v1; stack[sp - 2] = v4;
        stack[sp - 1] = v3; stack[sp] = v2; stack[sp + 1] = v1;
        return sp + 2;
    }

    function _requireExtraWords(
        uint256[] memory stack, uint256 sp, uint256 extra, uint256 pc
    ) private pure {
        uint256 words = _stackWords(stack, sp);
        if (words > stack.length || extra > stack.length - words) revert BytecodeError(9, pc);
    }

    function _invalidateLocal(
        uint256[] memory locals, bool[] memory initialized, uint256 local
    ) private pure {
        if (initialized[local]) {
            uint256 kind = _valueKind(locals[local]);
            if (_isCategory2Kind(kind) && local + 1 < locals.length) {
                locals[local + 1] = 0;
                initialized[local + 1] = false;
            } else if ((kind == KIND_LONG_TAIL || kind == KIND_DOUBLE_TAIL) && local != 0) {
                locals[local - 1] = 0;
                initialized[local - 1] = false;
            }
        }
        locals[local] = 0;
        initialized[local] = false;
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
            uint256 descriptorOffset;
            uint256 descriptorLength;
            if (
                (access & 0x0008) != 0 && descriptorIndex != 0
                    && descriptorIndex < c.cp.length && uint8(c.cp[descriptorIndex]) == 1
            ) {
                (descriptorOffset, descriptorLength) = _utf(c.cp[descriptorIndex]);
                (bool valid, uint256 width, uint8 kind) = _descriptorType(
                    c.data, descriptorOffset, descriptorOffset + descriptorLength, false
                );
                if (valid && width == descriptorLength) supportedKind = kind;
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
                    if ((supportedKind != KIND_INT && supportedKind != KIND_LONG
                            && supportedKind != KIND_FLOAT && supportedKind != KIND_DOUBLE)
                        || field.hasConstant || attributeLength != 2) {
                        revert FieldError(5, i);
                    }
                    uint256 constantIndex = _u2(r);
                    uint8 wantedTag = supportedKind == KIND_LONG ? 5
                        : (supportedKind == KIND_DOUBLE ? 6
                            : (supportedKind == KIND_FLOAT ? 4 : 3));
                    if (
                        constantIndex == 0 || constantIndex >= c.cp.length
                            || uint8(c.cp[constantIndex]) != wantedTag
                    ) revert FieldError(5, i);
                    field.hasConstant = true;
                    field.constantValue = (supportedKind == KIND_LONG || supportedKind == KIND_DOUBLE)
                        ? uint64(c.cp[constantIndex] >> 8)
                        : (supportedKind == KIND_FLOAT
                            ? uint64(uint32(c.cp[constantIndex] >> 8))
                            : uint64(_normalizeInt(
                                uint32(c.cp[constantIndex] >> 8), uint8(c.data[descriptorOffset])
                            )));
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

    function _bootstrapCloneable() private pure returns (bytes memory) {
        return hex"cafebabe0000003400050700020100136a6176612f6c616e672f436c6f6e6561626c650700040100106a6176612f6c616e672f4f626a6563740601000100030000000000000000";
    }

    function _bootstrapSerializable() private pure returns (bytes memory) {
        return hex"cafebabe0000003400050700020100146a6176612f696f2f53657269616c697a61626c650700040100106a6176612f6c616e672f4f626a6563740601000100030000000000000000";
    }

    function _bootstrapFloat() private pure returns (bytes memory) {
        return hex"cafebabe00000034000e0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e01000328295607000801000f6a6176612f6c616e672f466c6f6174010004436f646501000e696e7442697473546f466c6f617401000428492946010011666c6f6174546f526177496e744269747301000428462949003100070002000000000003000200050006000100090000001100010001000000052ab70001b1000000000109000a000b00000109000c000d00000000";
    }

    function _bootstrapDouble() private pure returns (bytes memory) {
        return hex"cafebabe00000034000e0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e0100032829560700080100106a6176612f6c616e672f446f75626c65010004436f64650100106c6f6e6742697473546f446f75626c65010004284a2944010013646f75626c65546f5261774c6f6e67426974730100042844294a003100070002000000000003000200050006000100090000001100010001000000052ab70001b1000000000109000a000b00000109000c000d00000000";
    }
}
