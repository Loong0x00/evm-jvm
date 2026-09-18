#!/usr/bin/env python3
"""Strict source invariants for constructor-only ``java.lang.ThreadLocal``.

Runtime inputs derive only from accepted raw35 parent ``parent-7183e57f8``.
Generated fixture/gate controls derive from the accepted raw35 capacity source
stage. This verifier never opens an original artifact, JAR, class, resource,
checkpoint, or world.
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
parent = stage.parent / "parent-7183e57f8"
fixture_parent = stage.parent / "classcount35-byte268379-preflight"

PARENT_FILES = {
    "pins.json": "62c3a1d2b3f89c1eacad3d2b79c686b8187d656de5d491ca2a3f20b3b344268c",
    "artifacts/engine/MCEntryInterpreter.sol": "1881219b3d4fd468a540bcbfbd72a84f303b46b873bb8e7d69c0399ff0807101",
    "artifacts/coordinator/MCEntryCoordinator.sol": "e9cb604457578840699fde8725a7278663bae7a6d116fe0b4dd32b1852f668cc",
    "executed-driver.go.txt": "30a838a3b83fd392c019dcf0276b06f798710360620174992cb5f720aaabd400",
    "checkpoint_diagnostic.py": "e9b4c1725f332f93489eeaaf79d64e51bb21a3ec63d278a4603292945cd0cd60",
    "checkpoint_frames.py": "e9b4c1725f332f93489eeaaf79d64e51bb21a3ec63d278a4603292945cd0cd60",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
FIXTURE_PARENT_FILES = {
    "tools/generate_fixtures.py": "18bd89bd3882f7d9554ec114503edd41fb3cd6cdb5ba7b40c8d87fcec99de749",
    "tools/gate.py": "05c585783836d15e358e058d3bae5e2fa39ac83d0e63f4b14759ed2c2b8e9b13",
}
PARENT_DOMAIN = "MC-CLASSCOUNT35-BYTE268379-P2"
DOMAIN = "MC-THREAD-LOCAL-CONSTRUCTOR-P1"
PARENT_ENGINE = "4d432d434333352d42593236383337392d454e48"
ENGINE = "4d432d544c4f43414c2d43544f522d4531000000"
PARENT_OWNER = "4d432d434333352d42593236383337392d4f574f"
OWNER = "4d432d544c4f43414c2d43544f522d4f31000000"
THREADLOCAL_SHA256 = "3b492a73fe71c60d5594f5116e813b857e248d7ca29270a8e33974143dc595d0"
ADDED_FIXTURES_SHA256 = "be3b20b36edc4e42ff7ecdbe3fbe362a7fc89f7307b9a356416cab9542499971"
ADDED_GATE_SHA256 = "0dd12f60d6dcd106260705647eafd557f2a1c7db5466eb3f9cc28ae84bca0db6"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_images(text):
    pattern = r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";"
    return dict(re.findall(pattern, text))


def expected_engine(text, image_hex):
    assert text.count(PARENT_DOMAIN) == 9
    result = text.replace(PARENT_DOMAIN, DOMAIN)
    assert result.count("new bytes32[](88)") == 1
    result = result.replace("new bytes32[](88)", "new bytes32[](89)")
    old_root = '''        // Iterable appends after the complete 87-image tail; Collection is the
        // only historical image replaced to expose this interface edge.
        h[87] = DBOOT_ITERABLE;
        return keccak256(abi.encode(DBOOT, h));'''
    new_root = '''        // Iterable remains at its accepted slot87. ThreadLocal appends at88.
        h[87] = DBOOT_ITERABLE;
        h[88] = keccak256(_bootstrapThreadLocal());
        return keccak256(abi.encode(DBOOT, h));'''
    assert result.count(old_root) == 1
    result = result.replace(old_root, new_root)
    assert result.count("uint256 count = inputCount + 82 +") == 1
    result = result.replace("uint256 count = inputCount + 82 +", "uint256 count = inputCount + 83 +")
    old_reserved = '''    function _isReservedThreadClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Thread"));
    }'''
    new_reserved = '''    function _isReservedThreadClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Thread"))
            || _isNamedClass(c, bytes("java/lang/ThreadLocal"));
    }'''
    assert result.count(old_reserved) == 1
    result = result.replace(old_reserved, new_reserved)
    old_append = '''    function _appendWeakReferenceAndIterable(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapWeakReference();
        classes[at + 1].data = _bootstrapIterable();
    }'''
    new_append = '''    function _appendWeakReferenceAndIterable(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapWeakReference();
        classes[at + 1].data = _bootstrapIterable();
        classes[at + 2].data = _bootstrapThreadLocal();
    }'''
    assert result.count(old_append) == 1
    result = result.replace(old_append, new_append)
    old_tail = '''        // TreeMap remains at slot85; the outlined helper appends WeakReference at
        // slot86 and Iterable at slot88 without moving a historical image.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        _appendWeakReferenceAndIterable(p.classes, classSlot + 47);'''
    new_tail = '''        // TreeMap remains at slot85; the outlined helper preserves WeakReference
        // at86 and Iterable at87, then appends constructor-only ThreadLocal at88.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        _appendWeakReferenceAndIterable(p.classes, classSlot + 47);'''
    assert result.count(old_tail) == 1
    result = result.replace(old_tail, new_tail)
    marker = "    function _bootstrapWeakReference() private pure returns (bytes memory) {"
    at = result.index(marker)
    end = result.index("\n", at) + 1
    append = '''
    // Java 8 direct Object subclass with only public <init>()V. No get, set,
    // remove, initialValue, withInitial, per-thread, or inheritance surface.
    function _bootstrapThreadLocal() private pure returns (bytes memory) { return hex"%s"; }
''' % image_hex
    return result[:end] + append + result[end:]


def preliminary_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    return text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)


def preliminary_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace(PARENT_OWNER, OWNER))


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
    assert text.count("raw35 / byte268379") == 1
    assert text.count("java-diff-mc-classcount35-byte268379-fixtures-") == 1
    assert text.count("bootstrap_count=88") == 1 and text.count("bootstrap_count=87") == 1 and text.count('\"bootstrapCount\": 88') == 1
    result = text.replace("Create only trusted generated Java-8 fixtures for raw35 / byte268379 and retained gates.",
                          "Create only trusted generated Java-8 fixtures for constructor-only ThreadLocal and retained gates.")
    result = result.replace("java-diff-mc-classcount35-byte268379-fixtures-",
                            "java-diff-mc-thread-local-constructor-fixtures-")
    result = (result.replace("bootstrap_count=88", "bootstrap_count=89")
                    .replace("bootstrap_count=87", "bootstrap_count=88")
                    .replace('"bootstrapCount": 88', '"bootstrapCount": 89'))
    needle = 'for count in (29, 30, 31, 32, 33, 34, 35, 36): count_fixture("count-%d" % count, count)\n'
    assert result.count(needle) == 1
    return result, needle


def expected_gate(text):
    assert text.count("One generated-only raw35 / byte268379 and retained acceptance gate.") == 1
    assert text.count("java-diff-mc-classcount35-byte268379-build-") == 1
    assert text.count("java-diff-mc-classcount35-byte268379-fixtures-") == 1
    assert text.count("java-diff-mc-classcount35-byte268379-gate-") == 1
    result = text.replace("One generated-only raw35 / byte268379 and retained acceptance gate.",
                          "One generated-only constructor-only ThreadLocal and retained acceptance gate.")
    result = result.replace("java-diff-mc-classcount35-byte268379-build-", "java-diff-mc-thread-local-constructor-build-")
    result = result.replace("java-diff-mc-classcount35-byte268379-fixtures-", "java-diff-mc-thread-local-constructor-fixtures-")
    result = result.replace("java-diff-mc-classcount35-byte268379-gate-", "java-diff-mc-thread-local-constructor-gate-")
    result = result.replace('pins["bootstrapCount"] == 88', 'pins["bootstrapCount"] == 89')
    result = result.replace('pins["diagnosticClassBound"] == 123', 'pins["diagnosticClassBound"] == 124')
    result = result.replace('def terminal(world, raw_count, bootstrap_count=88):',
                            'def terminal(world, raw_count, bootstrap_count=89):')
    old_sha = '''assert pins["bootstrapSHA256"]["Collection"] == "a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c" and pins["bootstrapSHA256"]["Iterable"] == "d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f"'''
    new_sha = '''assert pins["bootstrapSHA256"]["Collection"] == "a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c"
assert pins["bootstrapSHA256"]["Iterable"] == "d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f"
assert pins["bootstrapSHA256"]["ThreadLocal"] == "3b492a73fe71c60d5594f5116e813b857e248d7ca29270a8e33974143dc595d0"'''
    assert result.count(old_sha) == 1
    result = result.replace(old_sha, new_sha)
    old_summary = '''summary = {"profile": "MC-CLASSCOUNT35-BYTE268379-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted raw34 parent: 34 to 35, aggregate raw bytes 268053 to 268379, and checkpoint diagnostic class bound 122 to 123. All 88 bootstrap images, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new_summary = '''summary = {"profile": "MC-THREAD-LOCAL-CONSTRUCTOR-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only constructor-only java/lang/ThreadLocal appends at bootstrap index88 and the read-only diagnostic class bound changes 123 to 124 from accepted raw35 parent. Raw35/268379, all prior 88 image bytes/positions, natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    assert result.count(old_summary) == 1
    result = result.replace(old_summary, new_summary)
    needle = "# Exact raw35 is the focused capacity witness: all q1/q7/direct/reopen\n"
    assert result.count(needle) == 1
    return result, needle


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
fixture_inputs = {name: digest(fixture_parent / name) for name in FIXTURE_PARENT_FILES}
assert fixture_inputs == FIXTURE_PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-7183e57f8", "parentEvidence": "parent-7183e57f8", "sha256": inputs,
    "fixtureBasis": "classcount35-byte268379-preflight", "fixtureSHA256": fixture_inputs,
}
assert len(DOMAIN) == 30 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 88 and parent_pins["rawLimits"] == [35, 268379]
assert parent_pins["diagnosticClassBound"] == 123 and parent_pins["engine"]["bytes"] == 393060
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/ThreadLocal.java").read_text()
assert source == """package java.lang;
public class ThreadLocal {
  public ThreadLocal() {}
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="thread-local-constructor-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/ThreadLocal.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/ThreadLocal.class").read_bytes()
assert len(image) == 136 and hashlib.sha256(image).hexdigest() == THREADLOCAL_SHA256
assert image.hex() == (stage / "bootstrap/java/lang/ThreadLocal.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert image.count(b"java/lang/ThreadLocal") == image.count(b"java/lang/Object") == 1
assert image.count(b"<init>") == image.count(b"()V") == 1
for forbidden in (b"get", b"set", b"remove", b"initialValue", b"withInitial", b"InheritableThreadLocal", b"ThreadLocalMap", b"Supplier"):
    assert forbidden not in image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(parent_engine, image.hex())
parent_images = bootstrap_images(parent_engine)
images = bootstrap_images(engine)
# EnumSet is the historical multiline image constructor, so the compact literal
# extractor covers the other 87/88 functions while the root below covers all 88/89 slots.
assert len(parent_images) == 87 and len(images) == 88
assert set(images) == set(parent_images) | {"_bootstrapThreadLocal"}
for name, value in parent_images.items():
    assert images[name] == value, name
assert images["_bootstrapThreadLocal"] == image.hex()
for fixed in (
    "MAX_RAW_CLASSES = 35;", "MAX_RAW_BYTES = 268379;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](89)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(35), uint32(268379)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[87] = DBOOT_ITERABLE;",
    "h[88] = keccak256(_bootstrapThreadLocal());",
    "classes[at + 2].data = _bootstrapThreadLocal();",
    'bytes("java/lang/ThreadLocal")',
):
    assert engine.count(fixed) == 1, fixed
assert "DBOOT_THREADLOCAL" not in engine  # compact root layout avoids duplicating the image literal.
layout = json.loads((stage / "layout-recovery.json").read_text())
assert layout == {
    "scope": "runtime-layout-only measurement; no Java surface beyond constructor-only ThreadLocal",
    "basis": "parent-7183e57f8 plus the same 136-byte ThreadLocal image and all final semantic deltas",
    "runtimeCap": 393216,
    "rejectedDuplicateCommitmentLayout": {
        "root": "h[88] = DBOOT_THREADLOCAL",
        "constant": "DBOOT_THREADLOCAL = keccak256(hex<ThreadLocal image>)",
        "runtimeBytes": 393811, "overCapBytes": 595,
        "runtimeSHA256": "7dd4459738f448528229bc258f549386f07fed7fd7a8ebc617ebe79ca6dfa6fd",
    },
    "acceptedSingleLiteralLayout": {
        "root": "h[88] = keccak256(_bootstrapThreadLocal())",
        "runtimeBytes": 392326, "headroomBytes": 890,
        "runtimeSHA256": "a917fa3454e39140ab114f1211b69270c5a980b13a4976f71d7060c38edcbd71",
    },
    "reason": "The accepted root computes the same keccak256 over the exact bootstrap bytes while avoiding a second constant-literal layout. No opcode, limit, bootstrap image byte, class slot, native binding, or Java API semantics changed for this recovery.",
}

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = preliminary_coordinator((parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text())
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert coordinator.count("[35]") == 4 and coordinator.count("n > 35") == 1
assert coordinator.count("if (size == 0 || size > 268379)") == 1
assert coordinator.count("if (uint256(total) + size > 268379)") == 1

driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = preliminary_driver((parent / "executed-driver.go.txt").read_text())
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 35") == driver.count("len(parts) > 35") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == (parent / name).read_text().replace("classes<=123", "classes<=124")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == PARENT_FILES["artifacts/engine/build.js"]
assert digest(stage / "coordinator/build.js") == PARENT_FILES["artifacts/coordinator/build.js"]

fixture_base, fixture_needle = expected_fixtures((fixture_parent / "tools/generate_fixtures.py").read_text())
fixture_text = (stage / "tools/generate_fixtures.py").read_text()
left, right = fixture_base.split(fixture_needle)
assert fixture_text.startswith(left) and fixture_text.endswith(fixture_needle + right)
fixture_added = fixture_text[len(left):len(fixture_text) - len(fixture_needle + right)]
assert hashlib.sha256(fixture_added.encode()).hexdigest() == ADDED_FIXTURES_SHA256
for required in ("threadlocal-constructor", "threadlocal-uninitialized", "raw-threadlocal",
                 "threadlocal-get-omitted", "threadlocal-set-omitted", "threadlocal-remove-omitted",
                 "threadlocal-initialvalue-omitted", "threadlocal-withinitial-omitted"):
    assert fixture_added.count(required) >= 1, required
assert fixture_text.count("bootstrap_count=89") == fixture_text.count('"bootstrapCount": 89') == 1
assert fixture_text.count("bootstrap_count=88") == 1

gate_base, gate_needle = expected_gate((fixture_parent / "tools/gate.py").read_text())
gate_text = (stage / "tools/gate.py").read_text()
left, right = gate_base.split(gate_needle)
assert gate_text.startswith(left) and gate_text.endswith(gate_needle + right)
gate_added = gate_text[len(left):len(gate_text) - len(gate_needle + right)]
assert hashlib.sha256(gate_added.encode()).hexdigest() == ADDED_GATE_SHA256
for required in ("q_equivalent(\"threadlocal-constructor\"", "raw-threadlocal-replacement",
                 "threadlocal-get-omitted", "threadlocal-set-omitted", "threadlocal-remove-omitted",
                 "threadlocal-initialvalue-omitted", "threadlocal-withinitial-omitted"):
    assert required in gate_added, required
assert "whole_gate_seconds <= 1200" in gate_text

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator and driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    bootstraps = dict(parent_pins["bootstrapSHA256"]); bootstraps["ThreadLocal"] = THREADLOCAL_SHA256
    expected_pins = {
        "basis": "parent-7183e57f8", "parentEvidence": "parent-7183e57f8", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 89, "bootstrapSHA256": bootstraps,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [35, 268379], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 124, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    assert (stage / "build-pins.json").is_file() and json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-7183e57f8", "parentInputsVerified": len(inputs),
    "fixtureInputsVerified": len(fixture_inputs), "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 89, "appendedBootstrap": "java/lang/ThreadLocal", "threadLocalSlot": 88,
    "threadLocal": {"bytes": len(image), "sha256": THREADLOCAL_SHA256, "method": "<init>()V",
                    "super": "java/lang/Object", "interfaces": 0},
    "rawLimits": [35, 268379], "diagnosticClassBound": 124,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
