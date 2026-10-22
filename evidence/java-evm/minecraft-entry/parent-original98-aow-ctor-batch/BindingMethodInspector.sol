// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;

/// @notice Read-only diagnostic over one authenticated coordinator class binding.
/// It returns bytecode/constant-pool metadata only. It never runs Java bytecode,
/// performs checkpoint continuation, mutates the package, or selects resources
/// using host-side information.
interface IBoundCoordinator {
    function classBinding(uint8 at) external view returns (
        address decoder, bytes memory rawName, bytes32 resourceRoot, uint32 classSize
    );
    function owner() external view returns (address);
    function finalIndexRoot() external view returns (bytes32);
    function packageRoot() external view returns (bytes32);
}

interface IBoundDI0 {
    function owner() external view returns (address);
    function phase() external view returns (uint8);
    function indexRoot() external view returns (bytes32);
    function plainSize() external view returns (uint32);
    function finalRoot() external view returns (bytes32);
    function read(uint32 offset, uint32 length) external view returns (bytes memory);
}

contract BindingMethodInspector {
    bytes32 private constant DI0_CODEHASH =
        hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    uint32 private constant MAX_CLASS_BYTES = 262144;
    uint16 private constant MAX_CONSTANT_POOL_ENTRIES = 8192;
    uint16 private constant MAX_CLASS_MEMBERS = 2048;
    uint16 private constant MAX_RESULTS = 128;

    address private immutable coordinator;
    bytes32 private immutable coordinatorCodeHash;
    bytes32 private immutable assertedPackageRoot;

    struct CPEntry {
        uint8 tag;
        uint32 a;
        uint32 b;
    }

    /// `kind` is a stable metadata category: 1=type/class, 2=field,
    /// 3=method/interface call, 4=invokedynamic call site, 5=ldc class literal.
    struct Reference {
        uint16 methodIndex;
        uint32 pc;
        uint8 opcode;
        uint8 kind;
        uint8 constantPoolTag;
        uint16 constantPoolIndex;
        bytes opcodeName;
        bytes provenance;
        bytes owner;
        bytes name;
        bytes descriptor;
        bytes typeName;
    }

    struct ScanResult {
        uint8 bindingIndex;
        bytes resourceName;
        bytes declaringClass;
        uint16 methodIndex;
        bytes methodName;
        bytes methodDescriptor;
        uint32 pcStart;
        uint32 pcEnd;
        uint32 codeLength;
        uint32 decodedInstructions;
        uint16 switchInstructions;
        uint16 wideInstructions;
        address coordinator;
        bytes32 coordinatorCodeHash;
        bytes32 packageRoot;
        bytes32 indexRoot;
        bytes32 resourceRoot;
        bytes32 classBytesKeccak;
        Reference[] references;
    }

    struct MethodMeta {
        bytes name;
        bytes descriptor;
        uint32 codeStart;
        uint32 codeLength;
        bool foundCode;
    }

    struct ParsedClass {
        CPEntry[] pool;
        MethodMeta method;
        bytes declaringClass;
    }

    constructor(address boundCoordinator, bytes32 expectedCoordinatorCodeHash, bytes32 expectedPackageRoot) {
        require(boundCoordinator != address(0) && boundCoordinator.codehash == expectedCoordinatorCodeHash, "coordinator codehash");
        require(IBoundCoordinator(boundCoordinator).packageRoot() == expectedPackageRoot, "package root");
        coordinator = boundCoordinator;
        coordinatorCodeHash = expectedCoordinatorCodeHash;
        assertedPackageRoot = expectedPackageRoot;
    }

    /// @param binding Exact classBinding index in the ordinary coordinator.
    /// @param methodIndex Zero-based classfile method-table index.
    /// @param pcStart Inclusive bytecode PC window start (must be an instruction boundary).
    /// @param pcEnd Exclusive bytecode PC window end (must be an instruction boundary).
    /// @param maxResults Caller-selected output ceiling, additionally capped at 128.
    function inspect(uint8 binding, uint16 methodIndex, uint32 pcStart, uint32 pcEnd, uint16 maxResults)
        external view returns (ScanResult memory result)
    {
        require(maxResults != 0 && maxResults <= MAX_RESULTS, "result bound");
        bytes memory raw;
        bytes memory resourceName;
        bytes32 resourceRoot;
        bytes32 indexRoot;
        (raw, resourceName, resourceRoot, indexRoot) = _authenticatedRead(binding);
        result.bindingIndex = binding;
        result.resourceName = resourceName;
        result.resourceRoot = resourceRoot;
        result.indexRoot = indexRoot;
        result.packageRoot = assertedPackageRoot;
        result.classBytesKeccak = keccak256(raw);
        result.coordinator = coordinator;
        result.coordinatorCodeHash = coordinatorCodeHash;

        ParsedClass memory parsed = _parseClass(raw, resourceName, methodIndex);
        result.declaringClass = parsed.declaringClass;
        result.methodIndex = methodIndex;
        result.methodName = parsed.method.name;
        result.methodDescriptor = parsed.method.descriptor;
        result.pcStart = pcStart;
        result.pcEnd = pcEnd;
        result.codeLength = parsed.method.codeLength;
        (result.references, result.decodedInstructions, result.switchInstructions, result.wideInstructions) =
            _scan(raw, parsed.pool, parsed.method, methodIndex, pcStart, pcEnd, maxResults);
    }

    struct HeaderMethod {bytes name;bytes descriptor;uint32 codeLength;bool hasCode;}
    struct ClassHeader {bytes resourceName;bytes declaringClass;bytes superName;bytes[] interfaces;HeaderMethod[] methods;bytes32 resourceRoot;bytes32 classBytesKeccak;}
    function header(uint8 binding) external view returns(ClassHeader memory result) {
        bytes memory raw;bytes32 indexRoot;(raw,result.resourceName,result.resourceRoot,indexRoot)=_authenticatedRead(binding);
        result.classBytesKeccak=keccak256(raw);
        CPEntry[] memory pool;uint256 p;(pool,p)=_constantPool(raw);_validateConstantPool(raw,pool);
        require(_u16(raw,6)>=45&&_u16(raw,6)<=70,"class version");p+=2;
        result.declaringClass=_className(raw,pool,_u16(raw,p));require(keccak256(result.declaringClass)==keccak256(_bindingClassName(result.resourceName)),"binding name");
        uint256 superIndex=_u16(raw,p+2);if(superIndex!=0)result.superName=_className(raw,pool,superIndex);p+=4;
        uint256 n=_u16(raw,p);p+=2;require(n<=MAX_CLASS_MEMBERS,"interface bound");result.interfaces=new bytes[](n);
        for(uint256 i;i<n;++i){result.interfaces[i]=_className(raw,pool,_u16(raw,p));p+=2;}
        n=_u16(raw,p);p+=2;require(n<=MAX_CLASS_MEMBERS,"field bound");for(uint256 i;i<n;++i)p=_skipMember(raw,pool,p);
        n=_u16(raw,p);p+=2;require(n<=MAX_RESULTS,"header method output bound");result.methods=new HeaderMethod[](n);
        for(uint256 i;i<n;++i){MethodMeta memory m;(m,p)=_parseMethod(raw,pool,p,true);result.methods[i]=HeaderMethod(m.name,m.descriptor,m.codeLength,m.foundCode);}
        n=_u16(raw,p);p+=2;require(n<=MAX_CLASS_MEMBERS,"class attr bound");p=_skipAttributes(raw,pool,p,n);require(p==raw.length,"class trailing bytes");
    }

    struct LiteralCall {bytes resourceName;bytes declaringClass;bytes callerName;bytes callerDescriptor;bytes literal;bytes targetClass;bytes targetName;bytes targetDescriptor;bytes32 resourceRoot;bytes32 classBytesKeccak;}
    function literalCall(uint8 binding,uint16 methodIndex,uint32 literalPC,uint32 callPC) external view returns(LiteralCall memory result){
        bytes memory raw;bytes32 unusedIndex;(raw,result.resourceName,result.resourceRoot,unusedIndex)=_authenticatedRead(binding);
        ParsedClass memory p=_parseClass(raw,result.resourceName,methodIndex);result.declaringClass=p.declaringClass;result.callerName=p.method.name;result.callerDescriptor=p.method.descriptor;result.classBytesKeccak=keccak256(raw);
        _scan(raw,p.pool,p.method,methodIndex,literalPC,callPC+3,128);
        uint256 at=uint256(p.method.codeStart)+literalPC;uint8 op=_u8(raw,at);require(op==0x12||op==0x13,"literal opcode");uint256 ci=op==0x12?_u8(raw,at+1):_u16(raw,at+1);CPEntry memory lit=_entry(p.pool,ci,8);result.literal=_utf8(raw,p.pool,lit.a);
        at=uint256(p.method.codeStart)+callPC;require(_u8(raw,at)==0xb8||_u8(raw,at)==0xb6,"call opcode");CPEntry memory ref=_entry(p.pool,_u16(raw,at+1),10);CPEntry memory nat=_entry(p.pool,ref.b,12);result.targetClass=_className(raw,p.pool,ref.a);result.targetName=_utf8(raw,p.pool,nat.a);result.targetDescriptor=_utf8(raw,p.pool,nat.b);
    }

    function _parseClass(bytes memory raw, bytes memory resourceName, uint16 methodIndex)
        private pure returns (ParsedClass memory parsed)
    {
        uint256 at;
        (parsed.pool, at) = _constantPool(raw);
        require(_u16(raw, 6) >= 45 && _u16(raw, 6) <= 70, "class version");
        _validateConstantPool(raw, parsed.pool);
        at += 2; // access_flags
        parsed.declaringClass = _className(raw, parsed.pool, _u16(raw, at));
        uint256 superClass = _u16(raw, at + 2);
        at += 4;
        if (superClass != 0) _className(raw, parsed.pool, superClass);
        require(keccak256(parsed.declaringClass) == keccak256(_bindingClassName(resourceName)), "binding class name");
        uint256 interfaceCount = _u16(raw, at);
        at += 2;
        require(interfaceCount <= MAX_CLASS_MEMBERS && interfaceCount <= (raw.length - at) / 2, "interfaces");
        for (uint256 i; i < interfaceCount; ++i) {
            _className(raw, parsed.pool, _u16(raw, at));
            at += 2;
        }
        uint256 fieldCount = _u16(raw, at);
        at += 2;
        require(fieldCount <= MAX_CLASS_MEMBERS, "field bound");
        for (uint256 i; i < fieldCount; ++i) at = _skipMember(raw, parsed.pool, at);
        (parsed.method, at) = _parseMethods(raw, parsed.pool, at, methodIndex);
        uint256 classAttrCount = _u16(raw, at);
        at += 2;
        require(classAttrCount <= MAX_CLASS_MEMBERS, "class attributes");
        at = _skipAttributes(raw, parsed.pool, at, classAttrCount);
        require(at == raw.length, "class trailing bytes");
    }

    function _parseMethods(bytes memory raw, CPEntry[] memory pool, uint256 at, uint16 methodIndex)
        private pure returns (MethodMeta memory selected, uint256 next)
    {
        uint256 count = _u16(raw, at);
        at += 2;
        require(count <= MAX_CLASS_MEMBERS && methodIndex < count, "method index/bound");
        for (uint256 i; i < count; ++i) {
            MethodMeta memory item;
            bool chosen = i == methodIndex;
            (item, at) = _parseMethod(raw, pool, at, chosen);
            if (chosen) selected = item;
        }
        require(selected.foundCode, "selected method has no Code");
        next = at;
    }

    function _parseMethod(bytes memory raw, CPEntry[] memory pool, uint256 at, bool chosen)
        private pure returns (MethodMeta memory item, uint256 next)
    {
        item.name = _utf8(raw, pool, _u16(raw, at + 2));
        item.descriptor = _utf8(raw, pool, _u16(raw, at + 4));
        uint256 attrCount = _u16(raw, at + 6);
        require(attrCount <= MAX_CLASS_MEMBERS, "method attributes");
        at += 8;
        for (uint256 a; a < attrCount; ++a) {
            uint256 attrNameIndex = _u16(raw, at);
            uint256 attrLen = _u32(raw, at + 2);
            uint256 body = at + 6;
            require(body <= raw.length && attrLen <= raw.length - body, "method attribute bounds");
            bytes memory attrName = _utf8(raw, pool, attrNameIndex);
            if (chosen && keccak256(attrName) == keccak256(bytes("Code"))) {
                require(!item.foundCode, "duplicate Code");
                (item.codeStart, item.codeLength) = _parseCode(raw, pool, body, attrLen);
                item.foundCode = true;
            }
            at = body + attrLen;
        }
        next = at;
    }

    function _authenticatedRead(uint8 binding) private view returns (
        bytes memory raw, bytes memory resourceName, bytes32 resourceRoot, bytes32 indexRoot
    ) {
        require(coordinator.codehash == coordinatorCodeHash, "coordinator code changed");
        IBoundCoordinator c = IBoundCoordinator(coordinator);
        require(c.packageRoot() == assertedPackageRoot, "package changed");
        address packageOwner = c.owner();
        indexRoot = c.finalIndexRoot();
        require(packageOwner != address(0) && indexRoot != bytes32(0), "coordinator anchors");
        address decoder;
        uint32 size;
        (decoder, resourceName, resourceRoot, size) = c.classBinding(binding);
        require(resourceName.length > 6 && resourceName.length <= 256 && resourceRoot != bytes32(0), "binding shape");
        require(decoder != address(0) && decoder.codehash == DI0_CODEHASH, "DI0 codehash");
        require(size != 0 && size <= MAX_CLASS_BYTES, "class byte bound");
        IBoundDI0 resource = IBoundDI0(decoder);
        require(resource.owner() == packageOwner, "DI0 owner");
        require(resource.phase() == 4, "DI0 phase");
        require(resource.indexRoot() == indexRoot, "DI0 index root");
        require(resource.plainSize() == size, "DI0 size");
        require(resource.finalRoot() == resourceRoot, "DI0 final root");
        require(_hasClassSuffix(resourceName), "binding suffix");

        raw = new bytes(size);
        for (uint32 offset; offset < size;) {
            uint32 length = size - offset;
            if (length > 4096) length = 4096;
            bytes memory fragment = resource.read(offset, length);
            require(fragment.length == length, "short DI0 read");
            assembly ("memory-safe") {
                mcopy(add(add(raw, 32), offset), add(fragment, 32), length)
            }
            offset += length;
        }
    }

    function _constantPool(bytes memory d) private pure returns (CPEntry[] memory pool, uint256 at) {
        require(d.length >= 10 && _u32(d, 0) == 0xcafebabe, "class magic");
        uint256 count = _u16(d, 8);
        require(count >= 2 && count <= MAX_CONSTANT_POOL_ENTRIES, "constant pool bound");
        pool = new CPEntry[](count);
        at = 10;
        for (uint256 i = 1; i < count; ++i) {
            uint8 tag = _u8(d, at);
            ++at;
            pool[i].tag = tag;
            if (tag == 1) {
                uint256 len = _u16(d, at);
                at += 2;
                require(at <= d.length && len <= d.length - at, "UTF8 bounds");
                pool[i].a = uint32(at);
                pool[i].b = uint32(len);
                at += len;
            } else if (tag == 7 || tag == 8 || tag == 16 || tag == 19 || tag == 20) {
                pool[i].a = uint32(_u16(d, at));
                at += 2;
            } else if (tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 17 || tag == 18) {
                pool[i].a = uint32(_u16(d, at));
                pool[i].b = uint32(_u16(d, at + 2));
                at += 4;
            } else if (tag == 3 || tag == 4) {
                _u32(d, at);
                at += 4;
            } else if (tag == 5 || tag == 6) {
                require(i + 1 < count, "wide constant at end");
                _u32(d, at);
                _u32(d, at + 4);
                at += 8;
                ++i;
            } else if (tag == 15) {
                uint8 kind = _u8(d, at);
                require(kind >= 1 && kind <= 9, "method handle kind");
                pool[i].a = kind;
                pool[i].b = uint32(_u16(d, at + 1));
                at += 3;
            } else {
                revert("unknown constant tag");
            }
        }
        require(at <= d.length, "constant pool truncated");
    }

    function _parseCode(bytes memory d, CPEntry[] memory pool, uint256 body, uint256 length)
        private pure returns (uint32 codeStart, uint32 codeLength)
    {
        require(length >= 12 && body <= d.length && length <= d.length - body, "Code bounds");
        uint256 n = _u32(d, body + 4);
        require(n <= 65535 && n <= length - 12, "Code length");
        uint256 at = body + 8 + n;
        uint256 exceptionCount = _u16(d, at);
        at += 2;
        require(exceptionCount <= (body + length - at) / 8, "exception table bounds");
        for (uint256 i; i < exceptionCount; ++i) {
            uint256 start = _u16(d, at);
            uint256 end = _u16(d, at + 2);
            uint256 handler = _u16(d, at + 4);
            uint256 catchType = _u16(d, at + 6);
            require(start < end && end <= n && handler < n, "exception table range");
            if (catchType != 0) _className(d, pool, catchType);
            at += 8;
        }
        uint256 nestedCount = _u16(d, at);
        at += 2;
        require(nestedCount <= MAX_CLASS_MEMBERS, "Code attributes");
        at = _skipAttributes(d, pool, at, nestedCount);
        require(at == body + length, "Code attribute trailing bytes");
        codeStart = uint32(body + 8);
        codeLength = uint32(n);
    }

    function _scan(
        bytes memory d,
        CPEntry[] memory pool,
        MethodMeta memory method,
        uint16 methodIndex,
        uint32 pcStart,
        uint32 pcEnd,
        uint16 maxResults
    ) private pure returns (Reference[] memory refs, uint32 instructions, uint16 switches, uint16 wides) {
        uint256 codeLength = method.codeLength;
        require(pcStart < pcEnd && pcEnd <= codeLength, "PC window");
        bytes memory boundaries = new bytes((codeLength + 8) / 8);
        refs = new Reference[](maxResults);
        uint256 referenceCount;
        uint256 pc;
        bool startBoundary;
        bool endBoundary;
        while (pc < codeLength) {
            _markBoundary(boundaries, pc);
            if (pc == pcStart) startBoundary = true;
            if (pc == pcEnd) endBoundary = true;
            uint8 op = _u8(d, uint256(method.codeStart) + pc);
            uint256 width = _instructionWidth(d, uint256(method.codeStart), codeLength, pc);
            if (op == 0xaa || op == 0xab) {
                if (pc >= pcStart && pc < pcEnd) ++switches;
            }
            if (op == 0xc4 && pc >= pcStart && pc < pcEnd) ++wides;
            bool inWindow = pc >= pcStart && pc < pcEnd;
            Reference memory ref;
            bool found;
            (ref, found) = _referenceAt(d, pool, method.codeStart + pc, methodIndex, uint32(pc), op, inWindow);
            if (found && inWindow) {
                require(referenceCount < maxResults, "reference output bound");
                refs[referenceCount++] = ref;
            }
            pc += width;
            ++instructions;
            if (pc > codeLength) revert("instruction overrun");
        }
        _markBoundary(boundaries, codeLength);
        if (pcStart == codeLength) startBoundary = true;
        if (pcEnd == codeLength) endBoundary = true;
        require(startBoundary && endBoundary, "PC not instruction boundary");
        _validateBranchTargets(d, uint256(method.codeStart), codeLength, boundaries);
        assembly ("memory-safe") { mstore(refs, referenceCount) }
    }

    function _referenceAt(bytes memory d, CPEntry[] memory pool, uint256 instructionAt, uint16 methodIndex, uint32 pc, uint8 op, bool includeMetadata)
        private pure returns (Reference memory r, bool found)
    {
        uint256 operandAt = instructionAt + 1;
        uint256 cpIndex;
        uint8 expectedTag;
        uint8 kind;
        if (op == 0xbb || op == 0xbd || op == 0xc0 || op == 0xc1 || op == 0xc5) {
            cpIndex = _u16(d, operandAt);
            expectedTag = 7;
            kind = 1;
        } else if (op >= 0xb2 && op <= 0xb5) {
            cpIndex = _u16(d, operandAt);
            expectedTag = 9;
            kind = 2;
        } else if (op == 0xb6) {
            cpIndex = _u16(d, operandAt);
            expectedTag = 10;
            kind = 3;
        } else if (op == 0xb7 || op == 0xb8) {
            cpIndex = _u16(d, operandAt);
            kind = 3;
            require(cpIndex != 0 && cpIndex < pool.length, "method reference index");
            expectedTag = pool[cpIndex].tag;
            require(expectedTag == 10 || expectedTag == 11, "method reference tag");
        } else if (op == 0xb9) {
            cpIndex = _u16(d, operandAt);
            expectedTag = 11;
            kind = 3;
            require(_u8(d, operandAt + 2) != 0 && _u8(d, operandAt + 3) == 0, "invokeinterface operands");
        } else if (op == 0xba) {
            cpIndex = _u16(d, operandAt);
            expectedTag = 18;
            kind = 4;
            require(_u16(d, operandAt + 2) == 0, "invokedynamic operands");
        } else if (op == 0x12 || op == 0x13) {
            cpIndex = op == 0x12 ? _u8(d, operandAt) : _u16(d, operandAt);
            require(cpIndex != 0 && cpIndex < pool.length, "ldc index");
            uint8 literalTag = pool[cpIndex].tag;
            if (literalTag == 7) {
                expectedTag = 7;
                kind = 5;
            } else {
                require(literalTag == 3 || literalTag == 4 || literalTag == 8 || literalTag == 15 || literalTag == 16 || literalTag == 17, "ldc constant tag");
                return (r, false);
            }
        } else if (op == 0x14) {
            cpIndex = _u16(d, operandAt);
            require(cpIndex != 0 && cpIndex < pool.length, "ldc2 index");
            require(pool[cpIndex].tag == 5 || pool[cpIndex].tag == 6 || pool[cpIndex].tag == 17, "ldc2 constant tag");
            return (r, false);
        } else {
            return (r, false);
        }
        require(cpIndex != 0 && cpIndex < pool.length && pool[cpIndex].tag == expectedTag, "reference constant tag");
        if (!includeMetadata) return (r, true);
        r.methodIndex = methodIndex;
        r.pc = pc;
        r.opcode = op;
        r.kind = kind;
        r.constantPoolTag = expectedTag;
        r.constantPoolIndex = uint16(cpIndex);
        r.opcodeName = _opcodeName(op);
        if (kind == 1) r.provenance = bytes("Code operand -> CONSTANT_Class");
        else if (kind == 2) r.provenance = bytes("Code operand -> CONSTANT_Fieldref");
        else if (kind == 3 && expectedTag == 10) r.provenance = bytes("Code operand -> CONSTANT_Methodref");
        else if (kind == 3) r.provenance = bytes("Code operand -> CONSTANT_InterfaceMethodref");
        else if (kind == 4) r.provenance = bytes("Code operand -> CONSTANT_InvokeDynamic/NameAndType");
        else r.provenance = bytes("ldc operand -> CONSTANT_Class");
        if (kind == 1 || kind == 5) {
            r.typeName = _className(d, pool, cpIndex);
        } else if (kind == 2 || kind == 3) {
            CPEntry memory member = pool[cpIndex];
            r.owner = _className(d, pool, member.a);
            CPEntry memory nameType = _entry(pool, member.b, 12);
            r.name = _utf8(d, pool, nameType.a);
            r.descriptor = _utf8(d, pool, nameType.b);
        } else {
            CPEntry memory dynamicCall = pool[cpIndex];
            CPEntry memory nameType = _entry(pool, dynamicCall.b, 12);
            r.name = _utf8(d, pool, nameType.a);
            r.descriptor = _utf8(d, pool, nameType.b);
        }
        found = true;
    }

    function _validateBranchTargets(bytes memory d, uint256 start, uint256 codeLength, bytes memory boundaries)
        private pure
    {
        uint256 pc;
        while (pc < codeLength) {
            uint8 op = _u8(d, start + pc);
            uint256 width = _instructionWidth(d, start, codeLength, pc);
            if ((op >= 0x99 && op <= 0xa8) || op == 0xc6 || op == 0xc7) {
                int256 relative = int16(uint16(_u16(d, start + pc + 1)));
                _requireTarget(pc, relative, codeLength, boundaries);
            } else if (op == 0xc8 || op == 0xc9) {
                int256 relative = int32(uint32(_u32(d, start + pc + 1)));
                _requireTarget(pc, relative, codeLength, boundaries);
            } else if (op == 0xaa || op == 0xab) {
                uint256 p = pc + 1 + ((4 - ((pc + 1) & 3)) & 3);
                int256 def = int32(uint32(_u32(d, start + p)));
                _requireTarget(pc, def, codeLength, boundaries);
                p += 4;
                if (op == 0xaa) {
                    int256 low = int32(uint32(_u32(d, start + p)));
                    int256 high = int32(uint32(_u32(d, start + p + 4)));
                    uint256 cases = uint256(high - low + 1);
                    p += 8;
                    for (uint256 i; i < cases; ++i) {
                        int256 relative = int32(uint32(_u32(d, start + p + i * 4)));
                        _requireTarget(pc, relative, codeLength, boundaries);
                    }
                } else {
                    int256 pairs = int32(uint32(_u32(d, start + p)));
                    p += 4;
                    for (uint256 i; i < uint256(pairs); ++i) {
                        int256 relative = int32(uint32(_u32(d, start + p + i * 8 + 4)));
                        _requireTarget(pc, relative, codeLength, boundaries);
                    }
                }
            }
            pc += width;
        }
    }

    function _requireTarget(uint256 pc, int256 relative, uint256 codeLength, bytes memory boundaries) private pure {
        int256 target = int256(pc) + relative;
        require(target >= 0 && uint256(target) < codeLength && _isBoundary(boundaries, uint256(target)), "branch target");
    }

    function _instructionWidth(bytes memory d, uint256 start, uint256 codeLength, uint256 pc)
        private pure returns (uint256 width)
    {
        uint8 op = _u8(d, start + pc);
        if (op <= 0x0f || (op >= 0x1a && op <= 0x35) || (op >= 0x3b && op <= 0x83)
            || (op >= 0x85 && op <= 0x98) || (op >= 0xac && op <= 0xb1)
            || op == 0xbe || op == 0xbf || op == 0xc2 || op == 0xc3) {
            width = 1;
        } else if (op == 0x10 || op == 0x12 || (op >= 0x15 && op <= 0x19)
            || (op >= 0x36 && op <= 0x3a) || op == 0xa9 || op == 0xbc) {
            width = 2;
        } else if (op == 0x11 || op == 0x13 || op == 0x14 || op == 0x84
            || (op >= 0x99 && op <= 0xa8) || (op >= 0xb2 && op <= 0xb8)
            || op == 0xbb || op == 0xbd || op == 0xc0 || op == 0xc1 || op == 0xc6 || op == 0xc7) {
            width = 3;
        } else if (op == 0xb9 || op == 0xba || op == 0xc8 || op == 0xc9) {
            width = 5;
        } else if (op == 0xc5) {
            width = 4;
            require(_u8(d, start + pc + 3) != 0, "multianewarray dimensions");
        } else if (op == 0xc4) {
            uint8 modified = _u8(d, start + pc + 1);
            if (modified == 0x84) width = 6;
            else {
                require((modified >= 0x15 && modified <= 0x19) || (modified >= 0x36 && modified <= 0x3a) || modified == 0xa9, "wide opcode");
                width = 4;
            }
        } else if (op == 0xaa || op == 0xab) {
            uint256 p = pc + 1 + ((4 - ((pc + 1) & 3)) & 3);
            for (uint256 pad = pc + 1; pad < p; ++pad) require(_u8(d, start + pad) == 0, "switch padding");
            _u32(d, start + p); // default
            p += 4;
            if (op == 0xaa) {
                int256 low = int32(uint32(_u32(d, start + p)));
                int256 high = int32(uint32(_u32(d, start + p + 4)));
                require(high >= low, "tableswitch range");
                uint256 cases = uint256(high - low + 1);
                require(cases <= 16384, "tableswitch bound");
                width = p + 8 + cases * 4 - pc;
            } else {
                int256 pairs = int32(uint32(_u32(d, start + p)));
                require(pairs >= 0 && pairs <= 8192, "lookupswitch bound");
                uint256 pairCount = uint256(pairs);
                p += 4;
                int32 prior;
                for (uint256 i; i < pairCount; ++i) {
                    int32 key = int32(uint32(_u32(d, start + p + i * 8)));
                    require(i == 0 || key > prior, "lookupswitch keys");
                    prior = key;
                }
                width = p + pairCount * 8 - pc;
            }
        } else {
            revert("reserved/invalid opcode");
        }
        require(pc < codeLength && width <= codeLength - pc, "truncated instruction");
    }

    function _opcodeName(uint8 op) private pure returns (bytes memory) {
        if (op == 0xbb) return bytes("new");
        if (op == 0xbd) return bytes("anewarray");
        if (op == 0xc0) return bytes("checkcast");
        if (op == 0xc1) return bytes("instanceof");
        if (op == 0xc5) return bytes("multianewarray");
        if (op == 0xb2) return bytes("getstatic");
        if (op == 0xb3) return bytes("putstatic");
        if (op == 0xb4) return bytes("getfield");
        if (op == 0xb5) return bytes("putfield");
        if (op == 0xb6) return bytes("invokevirtual");
        if (op == 0xb7) return bytes("invokespecial");
        if (op == 0xb8) return bytes("invokestatic");
        if (op == 0xb9) return bytes("invokeinterface");
        if (op == 0xba) return bytes("invokedynamic");
        if (op == 0x12) return bytes("ldc");
        if (op == 0x13) return bytes("ldc_w");
        revert("reference opcode");
    }

    function _skipMember(bytes memory d, CPEntry[] memory pool, uint256 at) private pure returns (uint256) {
        _utf8(d, pool, _u16(d, at + 2));
        _utf8(d, pool, _u16(d, at + 4));
        uint256 count = _u16(d, at + 6);
        require(count <= MAX_CLASS_MEMBERS, "member attributes");
        return _skipAttributes(d, pool, at + 8, count);
    }

    function _skipAttributes(bytes memory d, CPEntry[] memory pool, uint256 at, uint256 count)
        private pure returns (uint256)
    {
        for (uint256 i; i < count; ++i) {
            _utf8(d, pool, _u16(d, at));
            uint256 length = _u32(d, at + 2);
            uint256 body = at + 6;
            require(body <= d.length && length <= d.length - body, "attribute bounds");
            at = body + length;
        }
        return at;
    }

    function _entry(CPEntry[] memory pool, uint256 index, uint8 tag) private pure returns (CPEntry memory item) {
        require(index != 0 && index < pool.length && pool[index].tag == tag, "constant pool type");
        return pool[index];
    }

    function _validateConstantPool(bytes memory d, CPEntry[] memory pool) private pure {
        for (uint256 i = 1; i < pool.length; ++i) {
            CPEntry memory item = pool[i];
            if (item.tag == 7 || item.tag == 8 || item.tag == 16 || item.tag == 19 || item.tag == 20) {
                _utf8(d, pool, item.a);
            } else if (item.tag == 9 || item.tag == 10 || item.tag == 11) {
                _entry(pool, item.a, 7);
                _entry(pool, item.b, 12);
            } else if (item.tag == 12) {
                _utf8(d, pool, item.a);
                _utf8(d, pool, item.b);
            } else if (item.tag == 15) {
                require(item.a >= 1 && item.a <= 9, "method handle kind");
                require(item.b != 0 && item.b < pool.length, "method handle reference");
                uint8 targetTag = pool[item.b].tag;
                require(targetTag == 9 || targetTag == 10 || targetTag == 11, "method handle target");
            } else if (item.tag == 17 || item.tag == 18) {
                _entry(pool, item.b, 12);
            }
        }
    }

    function _className(bytes memory d, CPEntry[] memory pool, uint256 index) private pure returns (bytes memory) {
        CPEntry memory item = _entry(pool, index, 7);
        return _utf8(d, pool, item.a);
    }

    function _utf8(bytes memory d, CPEntry[] memory pool, uint256 index) private pure returns (bytes memory) {
        CPEntry memory item = _entry(pool, index, 1);
        return _part(d, item.a, item.b);
    }

    function _hasClassSuffix(bytes memory name) private pure returns (bool) {
        if (name.length <= 6) return false;
        bytes memory suffix = bytes(".class");
        for (uint256 i; i < 6; ++i) if (name[name.length - 6 + i] != suffix[i]) return false;
        return true;
    }

    function _bindingClassName(bytes memory name) private pure returns (bytes memory) {
        require(_hasClassSuffix(name), "class suffix");
        return _part(name, 0, name.length - 6);
    }

    function _part(bytes memory d, uint256 at, uint256 length) private pure returns (bytes memory out) {
        require(at <= d.length && length <= d.length - at, "byte slice");
        out = new bytes(length);
        assembly ("memory-safe") { mcopy(add(out, 32), add(add(d, 32), at), length) }
    }

    function _u8(bytes memory d, uint256 at) private pure returns (uint8) {
        require(at < d.length, "read u8 bounds");
        return uint8(d[at]);
    }

    function _u16(bytes memory d, uint256 at) private pure returns (uint16 value) {
        require(at <= d.length && 2 <= d.length - at, "read u16 bounds");
        value = (uint16(uint8(d[at])) << 8) | uint16(uint8(d[at + 1]));
    }

    function _u32(bytes memory d, uint256 at) private pure returns (uint32 value) {
        require(at <= d.length && 4 <= d.length - at, "read u32 bounds");
        value = (uint32(uint8(d[at])) << 24) | (uint32(uint8(d[at + 1])) << 16)
            | (uint32(uint8(d[at + 2])) << 8) | uint32(uint8(d[at + 3]));
    }

    function _markBoundary(bytes memory boundaries, uint256 pc) private pure {
        uint256 byteIndex = pc >> 3;
        uint8 mask = uint8(1 << (pc & 7));
        boundaries[byteIndex] = bytes1(uint8(boundaries[byteIndex]) | mask);
    }

    function _isBoundary(bytes memory boundaries, uint256 pc) private pure returns (bool) {
        uint256 byteIndex = pc >> 3;
        uint8 mask = uint8(1 << (pc & 7));
        return (uint8(boundaries[byteIndex]) & mask) != 0;
    }
}
