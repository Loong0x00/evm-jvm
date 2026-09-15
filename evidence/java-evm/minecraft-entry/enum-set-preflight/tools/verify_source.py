#!/usr/bin/env python3
"""Strict reverse verifier for the append-only java/util/EnumSet stage.

Independently re-derives the staged engine from the accepted parent and the one
new Java8 image, then checks every fixed prior image and fixed limit.  It does
not execute the staging script.
"""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / 'parent-1ddd4f59a'
pins = json.loads((stage / 'pins.json').read_text())
domain = pins['domain']
accepted_domain = 'MC-ENUM-BOOTSTRAP-PARENT2'
image = (stage / 'bootstrap/java/util/EnumSet.class.hex').read_text().strip()


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


inputs = {k: digest(parent / k) for k in (
    'artifacts/engine/MCEntryInterpreter.sol',
    'artifacts/coordinator/MCEntryCoordinator.sol',
    'executed-driver.go.txt',
)}
assert json.loads((stage / 'parent-input.json').read_text()) == {
    'basis': pins['basis'], 'parentEvidence': pins['parentEvidence'], 'sha256': inputs
}
assert pins['basis'] == '1ddd4f59a' and pins['parentEvidence'] == 'parent-1ddd4f59a'
assert pins['phase'] == 'built' and pins['domain'] == domain
assert pins['runtimeCap'] == 393216 and pins['rawLimits'] == [29, 262144]
assert pins['externalLocalGas'] == 1000000000 and pins['reserve'] == 25000000
assert pins['globalNativeBindings'] == 12 and pins['stringLocalBinding'] == 10
assert pins['exceptionKinds'] == 14 and pins['maxFrames'] == 128
assert pins['checkpointCap'] == 1048576 and pins['headCap'] == 32768

# Recompile the one Java8 source input against an rt.jar with only EnumSet removed.
with tempfile.TemporaryDirectory(dir=root / 'build') as td:
    td = Path(td)
    api = td / 'rt-without-enumset.jar'
    shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar', api)
    subprocess.run(['zip', '-q', '-d', api, 'java/util/EnumSet.class'], check=True)
    out = td / 'classes'
    out.mkdir()
    subprocess.run([
        '/usr/lib/jvm/java-8-openjdk/bin/javac', '-source', '8', '-target', '8',
        '-g:none', '-bootclasspath', api, '-d', out,
        stage / 'bootstrap/java/util/EnumSet.java',
    ], check=True)
    enumset = (out / 'java/util/EnumSet.class').read_bytes()
assert hashlib.sha256(enumset).hexdigest() == pins['bootstrapSHA256']['EnumSet']
assert bytes.fromhex(image) == enumset and b'<clinit>' not in enumset
source = (stage / 'bootstrap/java/util/EnumSet.java').read_text()
for text in ('public class EnumSet extends HashSet',
             'EnumSet(Object[] universe)',
             'public static EnumSet allOf(Class elementType)',
             'private static native Object[] universe0(Class elementType);'):
    assert text in source, text
for forbidden in ('RegularEnumSet', 'JumboEnumSet', 'EnumSetIterator',
                  'Class.forName', 'getEnumConstants'):
    assert forbidden not in source, forbidden

# The committed image commitment must be the keccak of exactly those bytes.
keccak = subprocess.run([
    'node', '-e',
    "console.log(require('js-sha3').keccak256(Buffer.from(process.argv[1],'hex')))",
    enumset.hex(),
], check=True, capture_output=True, text=True, cwd=root,
    env=dict(os.environ, NODE_PATH=str(root / 'jvmevm/runtime/node_modules')),
).stdout.strip()
assert keccak == pins['bootstrapKeccak256']
engine = (stage / 'engine/MCEntryInterpreter.sol').read_text()
assert 'bytes32 private constant DBOOT_ENUMSET = keccak256(hex"' + image + '");' in engine
assert engine.count('_bootstrapEnumSet()') == 2  # root commitment + tail definition

# Reconstruct the exact semantic delta and assert every historical image/limit is
# untouched.  The reconstruction is intentionally independent of stage_engine.py.
e0 = (parent / 'artifacts/engine/MCEntryInterpreter.sol').read_text()
e = e0.replace(accepted_domain, domain)

def one(a, b):
    global e
    assert e.count(a) == 1, (a, e.count(a))
    e = e.replace(a, b)

one("    error ClassNewInstanceProfileError(uint256 code, uint256 pc);\n",
    "    error ClassNewInstanceProfileError(uint256 code, uint256 pc);\n"
    "    // Bounded EnumSet: only the enum class's own genuinely published\n"
    "    // constant table is read; nothing is fabricated, lazily initialized or\n"
    "    // mutated by the primitive.\n"
    "    error EnumSetProfileError(uint256 code, uint256 classIndex);\n")
one('bytes32[] memory h = new bytes32[](82);', 'bytes32[] memory h = new bytes32[](83);')
one('        h[81] = keccak256(_bootstrapEnum());\n        return keccak256(abi.encode(DBOOT, h));',
    '        h[81] = keccak256(_bootstrapEnum());\n'
    '        // Bounded EnumSet appends only after the complete 82-image Enum tail.\n'
    '        // The root commitment is folded from the exact image bytes at compile\n'
    '        // time (verify_source.py recomputes it), so the runtime carries the\n'
    '        // append-only literal once.\n'
    '        h[82] = DBOOT_ENUMSET;\n        return keccak256(abi.encode(DBOOT, h));')
one('uint256 count = inputCount + 76 + (suppliedObject ? 0 : 1)',
    'uint256 count = inputCount + 77 + (suppliedObject ? 0 : 1)')
one('        p.classes[classSlot + 42].data = _bootstrapEnum();\n        p.classClass = classSlot;',
    '        p.classes[classSlot + 42].data = _bootstrapEnum();\n'
    '        // EnumSet support appends after the complete 82-image Enum tail.\n'
    '        p.classes[classSlot + 43].data = _bootstrapEnumSet();\n'
    '        p.classClass = classSlot;')
one('    // java/lang/Enum is interpreter-owned: raw bindings may not replace it.\n'
    '    function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) {\n'
    '        return _isNamedClass(c, bytes("java/lang/Enum"));\n    }\n',
    '    // java/lang/Enum and java/util/EnumSet are interpreter-owned:\n'
    '    // raw bindings may not replace either image.\n'
    '    function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) {\n'
    '        return _isNamedClass(c, bytes("java/lang/Enum"))\n'
    '            || _isNamedClass(c, bytes("java/util/EnumSet"));\n    }\n')
one('''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("loadClass0"))
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
    }''')
one('        // Bindings7/8/9/10 are exactly owned private static native primitives.\n'
    '        // All prior bindings retain public-static validation.\n'
    '        if (binding == 7 || binding == 8 || binding == 9 || binding == 10) {',
    '        // Bindings7/8/9/10/12 are exactly owned private static native\n'
    '        // primitives.  All prior bindings retain public-static validation.\n'
    '        if (binding == 7 || binding == 8 || binding == 9 || binding == 10\n'
    '            || binding == 12) {')
one('''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && s.argumentKinds.length != 1)''',
    '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12
                && s.argumentKinds.length != 1)''')
one('''            || (binding == 11 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("Ljava/lang/Object;"))))) {''',
    '''            || (binding == 11 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("Ljava/lang/Object;"))))
            || (binding == 12 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 3))) {''')
one('''                    uint64 raw = uint64(_payload(f.stack[base]));
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
                    if (nativeBinding == 1) f.stack[base] = _packFloat(uint32(raw));''')
one('''    function _canonicalClassMirrorTarget(
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
    ) private pure returns (uint256 target) {''')
one('    bytes32 private constant DBOOT = keccak256("JVMEVM:' + domain + ':BOOTSTRAP:1");',
    '    bytes32 private constant DBOOT = keccak256("JVMEVM:' + domain + ':BOOTSTRAP:1");\n'
    '    // Append-only EnumSet image commitment; folded from the exact bytes at\n'
    '    // compile time so the runtime carries the append-only literal once.\n'
    '    bytes32 private constant DBOOT_ENUMSET = keccak256(hex"' + image + '");')
assert e.endswith('}\n')
e = e[:-2] + ('    function _bootstrapEnumSet() private pure returns (bytes memory) { return hex"'
              + image + '"; }\n\n}\n')
assert e == engine

# Every prior bootstrap image is byte-identical and in the same position.
pat = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a = re.findall(pat, e0)
b = re.findall(pat, engine)
assert len(a) == 82 and len(b) == 83 and a == b[:82] and b[82] == ('_bootstrapEnumSet', image)
assert engine.count('new bytes32[](83)') == 1 and engine.count('inputCount + 77 +') == 1
assert engine.count('_isReservedEnumClass(users[i])') == 1
assert engine.count('function _bootstrapEnumSet()') == 1
# The new primitive is a pure reader: no initializer scheduling or allocation.
branch = engine.split('if (nativeBinding == 12) {', 1)[1].split('uint64 raw = uint64', 1)[0]
for forbidden in ('_initializeClass', 'new uint64[]', 'ordinaryArrayCount', 'nextHandle = arena.nextHandle'):
    assert forbidden not in branch, forbidden
assert '_enumUniverse(' in branch
helper = engine.split('function _enumUniverse(', 1)[1].split('function _canonicalClassMirrorTarget(', 1)[0]
assert 'bytes("$VALUES")' in helper and 'revert EnumSetProfileError(2, target);' in helper
assert '_initializeClass' not in helper and 'new uint64[]' not in helper

# Coordinator carries exactly the rebased domain and the freshly measured pin.
c = (parent / 'artifacts/coordinator/MCEntryCoordinator.sol').read_text()
c = c.replace(accepted_domain, domain).replace('30abca290b7ee12f31a90427368b23a25af0ccd55a5f1913f28f69cefde29cf4',
                                              pins['engine']['runtimeKeccak256'])
assert (stage / 'coordinator/MCEntryCoordinator.sol').read_text() == c
print(json.dumps({
    'basis': pins['basis'], 'domain': domain,
    'enumSetSHA256': pins['bootstrapSHA256']['EnumSet'],
    'engine': pins['engine'], 'coordinator': pins['coordinator'],
    'runtimeCap': pins['runtimeCap'], 'headroom': pins['runtimeCap'] - pins['engine']['bytes'],
}, indent=2))
