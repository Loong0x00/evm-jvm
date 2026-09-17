#!/usr/bin/env python3
"""Strict source-only verifier for bounded ``java.lang.ref.WeakReference``.

The only accepted source basis is the accepted Integer parent ``parent-36ea2d7e6``.
This stage appends exactly one Java-8 bootstrap image after its 86 images. Generated
fixtures are the sole Java inputs; no original artifact, class, JAR, resource,
checkpoint, or world is opened.
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
parent = stage.parent / "parent-36ea2d7e6"

PARENT_FILES = {
    "pins.json": "a2ade46ee7fa768227509ac4dcfc02431bdb590c537acc7f6810ebb395bd315e",
    "artifacts/engine/MCEntryInterpreter.sol": "319a28276109ffe3f171bc563f8ba654f0eee01d05d28dee440a1c244abed6dc",
    "artifacts/coordinator/MCEntryCoordinator.sol": "f38c704a3bfa85376d3f511c7946b6cb94801554e2d3bacca1d29ae96223e739",
    "executed-driver.go.txt": "5c6734240311532a38b67e0188d54365fa813b4282e2d280f25679bde88036da",
    "checkpoint_diagnostic.py": "a7d1b2314e0349f3cb2d302bb4733d0bf8eea117e358694612af4e39607ea5f7",
    "checkpoint_frames.py": "a7d1b2314e0349f3cb2d302bb4733d0bf8eea117e358694612af4e39607ea5f7",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-INTEGER-VALUE-OF-P2"
DOMAIN = "MC-WEAK-REFERENCE-P1"
PARENT_ENGINE = "4d432d494e542d56414c55454f462d50322d4531"
ENGINE = "4d432d5745414b2d5245464552454e43452d5031"
PARENT_OWNER = "4d432d494e542d56414c55454f462d50322d4f31"
OWNER = "4d432d5745414b2d5245464552454e43452d4f31"
WEAK_REFERENCE_SHA256 = "9e3ef194b9d08f98f8e99f45fe8e192e38f6120e214e46596b8f9351351f9a36"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(text, name):
    match = re.search(r"function _bootstrap" + name + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


def initial_engine(text, image_hex):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("new bytes32[](86)") == 1
    old_root = '''        // TreeMap appends only after all 85 accepted images.
        h[85] = keccak256(_bootstrapTreeMap());
        return keccak256(abi.encode(DBOOT, h));'''
    new_root = '''        // TreeMap remains at its accepted slot; WeakReference appends after all 86 images.
        h[85] = keccak256(_bootstrapTreeMap());
        h[86] = keccak256(_bootstrapWeakReference());
        return keccak256(abi.encode(DBOOT, h));'''
    assert text.count(old_root) == 1
    result = text.replace("new bytes32[](86)", "new bytes32[](87)").replace(old_root, new_root)
    old_count = "uint256 count = inputCount + 80 + (suppliedObject ? 0 : 1)"
    assert result.count(old_count) == 1
    result = result.replace(old_count, "uint256 count = inputCount + 81 + (suppliedObject ? 0 : 1)")
    old_tail = '''        // TreeMap remains a constructor-only Object subclass at appended slot 85.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        p.classClass = classSlot;'''
    new_tail = '''        // TreeMap remains at slot85; WeakReference appends at slot86 only.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        p.classes[classSlot + 47].data = _bootstrapWeakReference();
        p.classClass = classSlot;'''
    assert result.count(old_tail) == 1
    result = result.replace(old_tail, new_tail)
    old_reserved = '''    // Ordinary guest-defined wrapper classes are nevertheless bootstrap-owned so a
    // raw bundle cannot replace Number, NumberFormatException, or Integer.
    function _isReservedIntegerClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Number"))
            || _isNamedClass(c, bytes("java/lang/NumberFormatException"))
            || _isNamedClass(c, bytes("java/lang/Integer"));
    }'''
    new_reserved = '''    // These guest-defined wrappers are nevertheless bootstrap-owned so a raw bundle
    // cannot replace Number, NumberFormatException, Integer, or WeakReference.
    function _isReservedIntegerClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Number"))
            || _isNamedClass(c, bytes("java/lang/NumberFormatException"))
            || _isNamedClass(c, bytes("java/lang/Integer"))
            || _isNamedClass(c, bytes("java/lang/ref/WeakReference"));
    }'''
    assert result.count(old_reserved) == 1
    result = result.replace(old_reserved, new_reserved)
    old_image = '''    // Java 8 javac -source 8 -target 8 -g:none: public Object subclass with
    // exactly the public no-arg constructor. No Map/SortedMap interface or API.
    function _bootstrapTreeMap() private pure returns (bytes memory) { return hex"cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100116a6176612f7574696c2f547265654d61700100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"; }

    /// @dev Exact Java 8 java.security.PrivilegedAction<T>; this interface grants no privilege.'''
    new_image = '''    // Java 8 javac -source 8 -target 8 -g:none: public Object subclass with
    // exactly the public no-arg constructor. No Map/SortedMap interface or API.
    function _bootstrapTreeMap() private pure returns (bytes memory) { return hex"cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100116a6176612f7574696c2f547265654d61700100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"; }

    // Java 8 direct Object subclass with a strong deterministic referent field;
    // no Reference hierarchy, queue, clearing, enqueue, or finalization surface.
    function _bootstrapWeakReference() private pure returns (bytes memory) { return hex"''' + image_hex + '''"; }

    /// @dev Exact Java 8 java.security.PrivilegedAction<T>; this interface grants no privilege.'''
    assert result.count(old_image) == 1
    result = result.replace(old_image, new_image).replace(PARENT_DOMAIN, DOMAIN)
    assert result.count(DOMAIN) == 9
    return result


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
    assert result.count(DOMAIN) == 4 and result.count(ENGINE) == 1
    return result


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    result = (text.replace(PARENT_DOMAIN, DOMAIN)
                  .replace(PARENT_ENGINE, ENGINE)
                  .replace(PARENT_OWNER, OWNER))
    assert result.count(DOMAIN) == 6 and result.count(ENGINE) == result.count(OWNER) == 1
    return result


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 5394", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 392454", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 392454", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-36ea2d7e6", "parentEvidence": "parent-36ea2d7e6", "sha256": inputs,
}
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [33, 262158]
assert parent_pins["diagnosticClassBound"] == 119
assert parent_pins["engine"]["bytes"] == 392454
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/ref/WeakReference.java").read_text()
assert source == """package java.lang.ref;
public class WeakReference {
  private final Object referent;
  public WeakReference(Object referent) { this.referent = referent; }
  public Object get() { return referent; }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="weak-reference-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/ref/WeakReference.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    weak_image = (out / "java/lang/ref/WeakReference.class").read_bytes()
assert len(weak_image) == 281 and hashlib.sha256(weak_image).hexdigest() == WEAK_REFERENCE_SHA256
assert weak_image.hex() == (stage / "bootstrap/java/lang/ref/WeakReference.class.hex").read_text().strip()
assert weak_image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/lang/ref/WeakReference", b"java/lang/Object", b"referent", b"<init>",
                 b"(Ljava/lang/Object;)V", b"get", b"()Ljava/lang/Object;"):
    assert required in weak_image, required
for forbidden in (b"java/lang/ref/Reference", b"ReferenceQueue", b"clear", b"enqueue", b"isEnqueued", b"finalize"):
    assert forbidden not in weak_image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine, weak_image.hex())
assert len(bytes.fromhex(bootstrap(engine, "WeakReference"))) == 281
assert hashlib.sha256(bytes.fromhex(bootstrap(engine, "WeakReference"))).hexdigest() == WEAK_REFERENCE_SHA256
for fixed in (
    "MAX_RAW_CLASSES = 33;", "MAX_RAW_BYTES = 262158;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](87)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(33), uint32(262158)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[86] = keccak256(_bootstrapWeakReference());",
    "p.classes[classSlot + 47].data = _bootstrapWeakReference();",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator(parent_coordinator)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert coordinator.count("[33]") == 4 and coordinator.count("n > 33") == 1
assert coordinator.count("if (size == 0 || size > 262158)") == 1
assert coordinator.count("if (uint256(total) + size > 262158)") == 1

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 33") == 1 and driver.count("len(parts) > 33") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    expected = (parent / name).read_text().replace("classes<=119", "classes<=120")
    assert (stage / "tools" / name).read_text() == expected
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

expected_args = sys.argv[1:]
prebuild = expected_args == ["--prebuild"]
if prebuild:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(expected_args) == 2 and expected_args[0] == "--built"
    pins = json.loads(Path(expected_args[1]).read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
    bootstrap_sha["WeakReference"] = WEAK_REFERENCE_SHA256
    expected_pins = {
        "basis": "parent-36ea2d7e6", "parentEvidence": "parent-36ea2d7e6", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 87,
        "bootstrapSHA256": bootstrap_sha,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [33, 262158], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 120, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    persistent = stage / "build-pins.json"
    assert persistent.is_file() and json.loads(persistent.read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-36ea2d7e6", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 87, "appendedBootstrap": "java/lang/ref/WeakReference",
    "weakReference": {"bytes": len(weak_image), "sha256": WEAK_REFERENCE_SHA256,
                      "constructor": "(Ljava/lang/Object;)V", "method": "get()Ljava/lang/Object;",
                      "retention": "strong deterministic referent identity; null remains null"},
    "rawLimits": [33, 262158], "diagnosticClassBound": 120,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
