#!/usr/bin/env python3
"""Strict derivation checks for bounded Java8 ``java.lang.Math`` int min/max.

The runtime delta is only one owned bootstrap append, reservation, and the
corresponding read-only diagnostic count.  It never opens an original artifact,
JAR, resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-396d5b062"
fixture_parent = stage.parent / "thread-local-constructor-preflight"

PARENT_FILES = {
    "pins.json": "6e3177f7d97e719bec74bfc0d3b7018998681164beb905f32f8bfef2bc172483",
    "artifacts/engine/MCEntryInterpreter.sol": "406169b6b3e54972ebad9b83c43903da4eafadc11c008ef3ed6615a52d270898",
    "artifacts/coordinator/MCEntryCoordinator.sol": "c8ab0461adb8108da774ff7e55655f9707fd2d0fb6214a86bbf96c7ede24a670",
    "executed-driver.go.txt": "d275ec151eb5939eba28f4ef869ed06627f8d21184e0e81b7357a909349743a9",
    "checkpoint_diagnostic.py": "7aa688af71521e67743349a5da7ceab0c0e05881960c4e619ec2e042e6800bec",
    "checkpoint_frames.py": "7aa688af71521e67743349a5da7ceab0c0e05881960c4e619ec2e042e6800bec",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
FIXTURE_PARENT_FILES = {
    "tools/generate_fixtures.py": "2ba4e427738d8f8f1e88c42268a488477b8283d0778c2748a1c563dea408d904",
    "tools/gate.py": "36e5e7590fe4f611fc78c1b1f7490bb5df0c949bfac849f1d2cf69e463e44304",
}
PARENT_DOMAIN = "MC-THREAD-LOCAL-CONSTRUCTOR-P2"
DOMAIN = "MC-MATH-INT-MIN-MAX-P1"
PARENT_ENGINE = "4d432d544c4f43414c2d43544f522d4532000000"
ENGINE = "4d432d4d4154482d494e542d4d494e2d4d415845"
PARENT_OWNER = "4d432d544c4f43414c2d43544f522d4f32000000"
OWNER = "4d432d4d4154482d494e542d4d494e2d4d41584f"
MATH_SHA256 = "e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356"
MATH_KECCAK256 = "dbb6f1d4402cef41ec516276bf659206c1c62c913983f7de441e5c3dab998931"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_engine(text, image_hex):
    assert text.count(PARENT_DOMAIN) == 9
    result = text.replace(PARENT_DOMAIN, DOMAIN)
    assert result.count("new bytes32[](89)") == 1
    result = result.replace("new bytes32[](89)", "new bytes32[](90)")
    root_marker = '    // Iterable root commitment is constant-folded; its image remains appended below.\n'
    assert result.count(root_marker) == 1
    result = result.replace(root_marker, root_marker + '    // Math root commitment is its exact append image hash; the image stays materialized once below.\n    bytes32 private constant DBOOT_MATH = hex"%s";\n' % MATH_KECCAK256)
    old_root = '''        // Iterable remains at its accepted slot87. ThreadLocal appends at88.
        h[87] = DBOOT_ITERABLE;
        h[88] = keccak256(_bootstrapThreadLocal());
        return keccak256(abi.encode(DBOOT, h));'''
    new_root = '''        // Iterable and ThreadLocal remain at accepted slots87/88; Math appends at89.
        h[87] = DBOOT_ITERABLE;
        h[88] = keccak256(_bootstrapThreadLocal());
        h[89] = DBOOT_MATH;
        return keccak256(abi.encode(DBOOT, h));'''
    assert result.count(old_root) == 1
    result = result.replace(old_root, new_root)
    assert result.count("uint256 count = inputCount + 83 +") == 1
    result = result.replace("uint256 count = inputCount + 83 +", "uint256 count = inputCount + 84 +")
    old_reserved = '''    function _isReservedThreadClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Thread"))
            || _isNamedClass(c, bytes("java/lang/ThreadLocal"));
    }'''
    new_reserved = '''    function _isReservedThreadClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Thread"))
            || _isNamedClass(c, bytes("java/lang/ThreadLocal"))
            || _isNamedClass(c, bytes("java/lang/Math"));
    }'''
    assert result.count(old_reserved) == 1
    result = result.replace(old_reserved, new_reserved)
    old_append = '''    function _appendWeakReferenceAndIterable(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapWeakReference();
        classes[at + 1].data = _bootstrapIterable();
        classes[at + 2].data = _bootstrapThreadLocal();
    }'''
    new_append = '''    function _appendWeakReferenceAndIterable(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapWeakReference();
        classes[at + 1].data = _bootstrapIterable();
        classes[at + 2].data = _bootstrapThreadLocal();
    }'''
    assert result.count(old_append) == 1
    result = result.replace(old_append, new_append)
    old_tail = '''        // TreeMap remains at slot85; the outlined helper preserves WeakReference
        // at86 and Iterable at87, then appends constructor-only ThreadLocal at88.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        _appendWeakReferenceAndIterable(p.classes, classSlot + 47);
        p.classClass = classSlot;
        p.loaderClass = classSlot + 12;'''
    new_tail = '''        // TreeMap remains at slot85; the outlined helper preserves WeakReference
        // at86, Iterable at87, ThreadLocal at88, then appends Math at89.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        _appendWeakReferenceAndIterable(p.classes, classSlot + 47);
        p.classClass = classSlot;
        p.loaderClass = classSlot + 12;
        // Math remains the final append-only slot89; isolate its image materialization
        // after pinned metadata assignments to retain the fixed LOCAL384 code layout.
        p.classes[classSlot + 50].data = _bootstrapMath();'''
    assert result.count(old_tail) == 1
    result = result.replace(old_tail, new_tail)
    needle = '    function _bootstrapThreadLocal() private pure returns (bytes memory) { return hex"cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100156a6176612f6c616e672f5468726561644c6f63616c0100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"; }\n'
    assert result.count(needle) == 1
    extra = '''\n    // Java 8 final utility class: private constructor and ordinary static int min/max only.
    // No long, floating, abs, round, random, or exact-arithmetic API is supplied.
    function _bootstrapMath() private pure returns (bytes memory) { return hex"%s"; }
''' % image_hex
    return result.replace(needle, needle + extra)


def preliminary_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    return text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)


def preliminary_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    return text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


def expected_fixtures(text):
    assert text.count("bootstrap_count=89") == 1
    assert text.count("bootstrap_count=88") == 1
    assert text.count('"bootstrapCount": 89') == 1
    result = text.replace("constructor-only ThreadLocal and retained gates", "Math int min/max and retained gates")
    result = result.replace("java-diff-mc-thread-local-constructor-fixtures-", "java-diff-mc-math-int-min-max-fixtures-")
    result = result.replace("bootstrap_count=89", "bootstrap_count=90")
    result = result.replace("bootstrap_count=88", "bootstrap_count=89")
    result = result.replace('"bootstrapCount": 89', '"bootstrapCount": 90')
    return result


def expected_gate(text):
    assert text.count("java-diff-mc-thread-local-constructor-build-") == 1
    assert text.count("java-diff-mc-thread-local-constructor-fixtures-") == 1
    assert text.count("java-diff-mc-thread-local-constructor-gate-") == 1
    result = text.replace("constructor-only ThreadLocal and retained acceptance gate", "Math int min/max and retained acceptance gate")
    result = result.replace("java-diff-mc-thread-local-constructor-build-", "java-diff-mc-math-int-min-max-build-")
    result = result.replace("java-diff-mc-thread-local-constructor-fixtures-", "java-diff-mc-math-int-min-max-fixtures-")
    result = result.replace("java-diff-mc-thread-local-constructor-gate-", "java-diff-mc-math-int-min-max-gate-")
    result = result.replace('pins["bootstrapCount"] == 89', 'pins["bootstrapCount"] == 90')
    result = result.replace('pins["diagnosticClassBound"] == 124', 'pins["diagnosticClassBound"] == 125')
    result = result.replace('def terminal(world, raw_count, bootstrap_count=89):', 'def terminal(world, raw_count, bootstrap_count=90):')
    needle = 'assert pins["bootstrapSHA256"]["ThreadLocal"] == "3b492a73fe71c60d5594f5116e813b857e248d7ca29270a8e33974143dc595d0"\n'
    assert result.count(needle) == 1
    result = result.replace(needle, needle + 'assert pins["bootstrapSHA256"]["Math"] == "e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356"\n')
    old = '''summary = {"profile": "MC-THREAD-LOCAL-CONSTRUCTOR-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only constructor-only java/lang/ThreadLocal appends at bootstrap index88 and the read-only diagnostic class bound changes 123 to 124 from accepted raw35 parent. Raw35/268379, all prior 88 image bytes/positions, natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new = '''summary = {"profile": "MC-MATH-INT-MIN-MAX-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only Java8 java/lang/Math private constructor plus ordinary static int max/min append at bootstrap index89 and the read-only diagnostic class bound changes 124 to 125 from accepted ThreadLocal parent. Raw35/268379, all prior 89 image bytes/positions, natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. No long, floating, abs, round, random, or exact-arithmetic API is supplied. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    assert result.count(old) == 1
    return result.replace(old, new)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
fixture_inputs = {name: digest(fixture_parent / name) for name in FIXTURE_PARENT_FILES}
assert fixture_inputs == FIXTURE_PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-396d5b062", "parentEvidence": "parent-396d5b062", "sha256": inputs,
    "fixtureBasis": "thread-local-constructor-preflight", "fixtureSHA256": fixture_inputs,
}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 89 and parent_pins["rawLimits"] == [35, 268379]
assert parent_pins["diagnosticClassBound"] == 124 and parent_pins["engine"]["bytes"] == 392326
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20

source = (stage / "bootstrap/java/lang/Math.java").read_text()
assert source == '''package java.lang;
public final class Math {
 private Math() {}
 public static int max(int a,int b) { if (a >= b) return a; return b; }
 public static int min(int a,int b) { if (a <= b) return a; return b; }
}
'''
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="math-int-min-max-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/Math.java"; src.parent.mkdir(parents=True); src.write_text(source)
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, src], check=True)
    image = (output / "java/lang/Math.class").read_bytes()
assert len(image) == 253 and hashlib.sha256(image).hexdigest() == MATH_SHA256
assert image.hex() == (stage / "bootstrap/java/lang/Math.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034") and image[8:10] == bytes.fromhex("000e")
for required in (b"java/lang/Math", b"java/lang/Object", b"<init>", b"max", b"min", b"(II)I"):
    assert required in image, required
for forbidden in (b"abs", b"round", b"random", b"Exact", b"(JJ)J", b"(FF)F", b"(DD)D"):
    assert forbidden not in image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(parent_engine, image.hex())
for fixed in (
    "MAX_RAW_CLASSES = 35;", "MAX_RAW_BYTES = 268379;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](90)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(35), uint32(268379)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[88] = keccak256(_bootstrapThreadLocal());",
    "h[89] = DBOOT_MATH;", "p.classes[classSlot + 50].data = _bootstrapMath();",
    'bytes("java/lang/Math")',
):
    assert engine.count(fixed) == 1, fixed
assert engine.count('bytes32 private constant DBOOT_MATH = hex"' + MATH_KECCAK256 + '";') == 1

for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == (parent / name).read_text().replace("classes<=124", "classes<=125")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == PARENT_FILES["artifacts/engine/build.js"]
assert digest(stage / "coordinator/build.js") == PARENT_FILES["artifacts/coordinator/build.js"]

fixtures_base = expected_fixtures((fixture_parent / "tools/generate_fixtures.py").read_text())
fixture_marker = 'for count in (29, 30, 31, 32, 33, 34, 35, 36): count_fixture("count-%d" % count, count)\n'
assert fixtures_base.count(fixture_marker) == 1
fixture_text = (stage / "tools/generate_fixtures.py").read_text()
left, right = fixtures_base.split(fixture_marker)
assert fixture_text.startswith(left) and fixture_text.endswith(fixture_marker + right)
fixture_added = fixture_text[len(left):len(fixture_text) - len(fixture_marker + right)]
for token in ("math-int-min-max", "math-uninitialized", "raw-math", "math-abs-omitted", "math-addexact-omitted", "Math.max", "Math.min"):
    assert token in fixture_added, token
assert "Math.abs" not in (stage / "bootstrap/java/lang/Math.java").read_text()

gate_base = expected_gate((fixture_parent / "tools/gate.py").read_text())
gate_marker = '# Exact raw35 is the focused capacity witness: all q1/q7/direct/reopen\n'
assert gate_base.count(gate_marker) == 1
gate_text = (stage / "tools/gate.py").read_text()
left, right = gate_base.split(gate_marker)
assert gate_text.startswith(left) and gate_text.endswith(gate_marker + right)
gate_added = gate_text[len(left):len(gate_text) - len(gate_marker + right)]
for token in ("q_equivalent(\"math-int-min-max\"", "math-uninitialized", "raw-math-replacement", "math-abs-omitted", "math-addexact-omitted", "raw + 89"):
    assert token in gate_added, token
assert "whole_gate_seconds <= 1200" in gate_text

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = preliminary_coordinator((parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text())
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = preliminary_driver((parent / "executed-driver.go.txt").read_text())
args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator and driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    bootstraps = dict(parent_pins["bootstrapSHA256"]); bootstraps["Math"] = MATH_SHA256
    expected_pins = {
        "basis": "parent-396d5b062", "parentEvidence": "parent-396d5b062", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 90, "bootstrapSHA256": bootstraps,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [35, 268379], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 125, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-396d5b062", "parentInputsVerified": len(inputs),
    "fixtureInputsVerified": len(fixture_inputs), "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "appendedBootstrap": "java/lang/Math", "mathSlot": 89,
    "math": {"bytes": len(image), "sha256": MATH_SHA256, "methods": ["max(II)I", "min(II)I"],
             "constructor": "private <init>()V", "super": "java/lang/Object", "interfaces": 0},
    "rawLimits": [35, 268379], "diagnosticClassBound": 125,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
