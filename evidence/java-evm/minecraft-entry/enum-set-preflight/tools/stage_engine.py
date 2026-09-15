#!/usr/bin/env python3
"""One-shot staging of the append-only EnumSet engine delta.

Reads the accepted parent-1ddd4f59a engine source, applies the exact EnumSet
delta with per-edit uniqueness assertions, and writes
engine/MCEntryInterpreter.sol.  verify_source.py independently reverses this
delta and re-derives the image commitment; this script keeps the staged
artifact reproducible.
"""
from pathlib import Path

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / 'parent-1ddd4f59a'
accepted_domain = 'MC-ENUM-BOOTSTRAP-PARENT2'
domain = 'MC-ENUM-SET-PARENT1'
image = (stage / 'bootstrap/java/util/EnumSet.class.hex').read_text().strip()

e = (parent / 'artifacts/engine/MCEntryInterpreter.sol').read_text()


def one(a, b):
    global e
    assert e.count(a) == 1, (a, e.count(a))
    e = e.replace(a, b)


e = e.replace(accepted_domain, domain)

one(
    "    error ClassNewInstanceProfileError(uint256 code, uint256 pc);\n",
    "    error ClassNewInstanceProfileError(uint256 code, uint256 pc);\n"
    "    // Bounded EnumSet: only the enum class's own genuinely published\n"
    "    // constant table is read; nothing is fabricated, lazily initialized or\n"
    "    // mutated by the primitive.\n"
    "    error EnumSetProfileError(uint256 code, uint256 classIndex);\n",
)
one('bytes32[] memory h = new bytes32[](82);', 'bytes32[] memory h = new bytes32[](83);')
one(
    '        h[81] = keccak256(_bootstrapEnum());\n        return keccak256(abi.encode(DBOOT, h));',
    '        h[81] = keccak256(_bootstrapEnum());\n'
    '        // Bounded EnumSet appends only after the complete 82-image Enum tail.\n'
    '        // The root commitment is folded from the exact image bytes at compile\n'
    '        // time (verify_source.py recomputes it), so the runtime carries the\n'
    '        // append-only literal once.\n'
    '        h[82] = DBOOT_ENUMSET;\n'
    '        return keccak256(abi.encode(DBOOT, h));',
)
one(
    'uint256 count = inputCount + 76 + (suppliedObject ? 0 : 1)',
    'uint256 count = inputCount + 77 + (suppliedObject ? 0 : 1)',
)
one(
    '        p.classes[classSlot + 42].data = _bootstrapEnum();\n        p.classClass = classSlot;',
    '        p.classes[classSlot + 42].data = _bootstrapEnum();\n'
    '        // EnumSet support appends after the complete 82-image Enum tail.\n'
    '        p.classes[classSlot + 43].data = _bootstrapEnumSet();\n'
    '        p.classClass = classSlot;',
)
one(
    '    // java/lang/Enum is interpreter-owned: raw bindings may not replace it.\n'
    '    function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) {\n'
    '        return _isNamedClass(c, bytes("java/lang/Enum"));\n'
    '    }\n',
    '    // java/lang/Enum and java/util/EnumSet are interpreter-owned:\n'
    '    // raw bindings may not replace either image.\n'
    '    function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) {\n'
    '        return _isNamedClass(c, bytes("java/lang/Enum"))\n'
    '            || _isNamedClass(c, bytes("java/util/EnumSet"));\n'
    '    }\n',
)
one(
    '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("loadClass0"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/String;)Ljava/lang/Class;"))) return 8;
        }
        return 0;
    }''',
    '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("loadClass0"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/String;)Ljava/lang/Class;"))) return 8;
        } else if (_isNamedClass(c, bytes("java/util/EnumSet"))) {
            // Binding12 is the sole EnumSet primitive.  It returns the enum
            // class's already-published constant table, never a fabricated set.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("universe0"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/Class;)[Ljava/lang/Object;"))) return 12;
        }
        return 0;
    }''',
)
one(
    '        // Bindings7/8/9/10 are exactly owned private static native primitives.\n'
    '        // All prior bindings retain public-static validation.\n'
    '        if (binding == 7 || binding == 8 || binding == 9 || binding == 10) {',
    '        // Bindings7/8/9/10/12 are exactly owned private static native\n'
    '        // primitives.  All prior bindings retain public-static validation.\n'
    '        if (binding == 7 || binding == 8 || binding == 9 || binding == 10\n'
    '            || binding == 12) {',
)
one(
    '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && s.argumentKinds.length != 1)''',
    '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12
                && s.argumentKinds.length != 1)''',
)
one(
    '''            || (binding == 11 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("Ljava/lang/Object;"))))) {''',
    '''            || (binding == 11 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("Ljava/lang/Object;"))))
            || (binding == 12 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 3))) {''',
)
one(
    '''                    uint64 raw = uint64(_payload(f.stack[base]));
                    if (nativeBinding == 1) f.stack[base] = _packFloat(uint32(raw));''',
    '''                    if (nativeBinding == 12) {
                        // Inspect every operand before raising at most once.  The
                        // universe is read from a field already published by
                        // genuine guest execution, so this primitive allocates
                        // nothing, schedules no initializer and mutates no arena
                        // state.
                        uint256 kind;
                        uint256 universe;
                        if (_payload(f.stack[base]) == 0) {
                            // EnumSet.allOf(null) is an ordinary guest NPE.
                            kind = 6;
                        } else {
                            uint256 enumTarget = _canonicalClassMirrorTarget(
                                arena, classes, rawClassCount, loaderClass,
                                _payload(f.stack[base]), parentLinks, hierarchyState, opPC
                            );
                            if ((classes[enumTarget].accessFlags & 0x4000) == 0) {
                                // A non-enum operand is an ordinary guest CCE;
                                // no initializer is run for it.
                                kind = 8;
                            } else if (initializationState[enumTarget] == 3) {
                                // Erroneous active use is the ordinary guest NCDFE kind.
                                kind = 12;
                            } else {
                                universe = _enumUniverse(
                                    classes, staticValues, enumTarget
                                );
                            }
                        }
                        if (kind != 0) {
                            // Consume the argument, then unwind through the
                            // ordinary guest handler for the refusal kind.
                            f.sp = base;
                            nextHandle = _raiseJava(
                                kind, opPC, arena, classes, objectHeap, heapKinds,
                                heapClasses, arrayLeafTypes, parentLinks,
                                hierarchyState, nextHandle
                            );
                            continue;
                        }
                        f.stack[base] = _packRef(uint32(universe));
                        f.sp = base + 1;
                        continue;
                    }
                    uint64 raw = uint64(_payload(f.stack[base]));
                    if (nativeBinding == 1) f.stack[base] = _packFloat(uint32(raw));''',
)
one(
    '''    function _canonicalClassMirrorTarget(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 rawClassCount,
        uint256 loaderClass, uint256 wantedHandle, uint256[] memory parentLinks,
        uint8[] memory hierarchyState, uint256 pc
    ) private pure returns (uint256 target) {''',
    '''    /// @dev Reads the enum universe published by genuine guest execution.  A
    /// javac enum class carries one static synthetic constant-table field whose
    /// entries are exactly its ACC_ENUM constants in declaration order; this is
    /// the same table Java 8's Class.getEnumConstantsShared() returns for the
    /// measured EnumSet.allOf path.  The primitive therefore fabricates no
    /// value, runs no initializer and recovers from no failed state: an enum
    /// whose table has not genuinely been published (uninitialized or failed)
    /// is refused atomically with a typed profile error.
    function _enumUniverse(
        ClassInfo[] memory classes, uint256[][] memory staticValues, uint256 target
    ) private pure returns (uint256 handle) {
        ClassInfo memory c = classes[target];
        for (uint256 i; i < c.fields.length; ++i) {
            if ((c.fields[i].accessFlags & 0x0008) == 0) continue;
            (uint256 no, uint256 nl) = _utf(c.cp[c.fields[i].nameIndex]);
            if (!_equalsLiteral(c.data, no, nl, bytes("$VALUES"))) continue;
            uint256 value = staticValues[target][i];
            if (_valueKind(value) != KIND_REF || _payload(value) == 0) {
                revert EnumSetProfileError(2, target);
            }
            return _payload(value);
        }
        revert EnumSetProfileError(2, target);
    }

    function _canonicalClassMirrorTarget(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 rawClassCount,
        uint256 loaderClass, uint256 wantedHandle, uint256[] memory parentLinks,
        uint8[] memory hierarchyState, uint256 pc
    ) private pure returns (uint256 target) {''',
)
one(
    '    bytes32 private constant DBOOT = keccak256("JVMEVM:' + domain + ':BOOTSTRAP:1");',
    '    bytes32 private constant DBOOT = keccak256("JVMEVM:' + domain + ':BOOTSTRAP:1");\n'
    '    // Append-only EnumSet image commitment; folded from the exact bytes at\n'
    '    // compile time so the runtime carries the append-only literal once.\n'
    '    bytes32 private constant DBOOT_ENUMSET = keccak256(hex"' + image + '");',
)

assert e.endswith('}\n')
e = e[:-2] + (
    '    function _bootstrapEnumSet() private pure returns (bytes memory) { return hex"'
    + image + '"; }\n\n}\n'
)
(stage / 'engine/MCEntryInterpreter.sol').write_text(e)
print('staged engine bytes', len(e))
