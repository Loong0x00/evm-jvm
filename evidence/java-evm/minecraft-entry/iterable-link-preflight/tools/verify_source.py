#!/usr/bin/env python3
"""Strict source verifier for the bounded Java-8 Iterable linkage stage.

Only accepted Integer/String parent ``parent-61fd1832a`` is consumed as source
basis. The stage adds java/lang/Iterable at append slot88 and replaces only the
existing java/util/Collection image so it extends that interface. Generated
fixtures are the only Java inputs; no original artifact, JAR, class, resource,
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
parent = stage.parent / "parent-61fd1832a"

PARENT_FILES = {
    "pins.json": "7e938ae955335594f77589ab0c86ce919f146172a71e2fdab0bff3ebec4789e2",
    "artifacts/engine/MCEntryInterpreter.sol": "bdbde4937b4d3ceffa8e5a5ac32d678edfde2e40e594175526f6cca8d38bf2c1",
    "artifacts/coordinator/MCEntryCoordinator.sol": "ea0dcaedc51a7ba723e3e6459ef13081873e73e7f5a456e20a07a33850ccda1e",
    "executed-driver.go.txt": "eb9e4b1af3b602d185e3703dda5d816aee00c320537ee5814ed71b6e1f57c5e9",
    "checkpoint_diagnostic.py": "a0936f5451b3771110ff83df6e912a2d9fc627a81aec44bad4faad8e30faa808",
    "checkpoint_frames.py": "a0936f5451b3771110ff83df6e912a2d9fc627a81aec44bad4faad8e30faa808",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-INTEGER-VALUE-OF-STRING-P2"
DOMAIN = "MC-ITERABLE-LINK-P1"
PARENT_ENGINE = "4d432d494e54454745522d535452494e472d5032"
ENGINE = "4d432d4954455241424c452d4c494e4b2d503100"
PARENT_OWNER = "4d432d494e54454745522d535452494e472d4f32"
OWNER = "4d432d4954455241424c452d4c494e4b2d4f3100"
ITERABLE_SHA256 = "d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f"
COLLECTION_SHA256 = "a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c"
PARENT_COLLECTION_SHA256 = "7ec295a5a1a6b63cf559df3952af74de966b98bd40e375710b0cd57d7f857e74"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(text, name):
    match = re.search(r"function _bootstrap" + name + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


def bootstrap_images(text):
    images = dict(re.findall(r"function (_bootstrap[A-Za-z0-9]+)\(\).*?return hex\"([0-9a-f]+)\";", text, re.S))
    assert len(images) == len(set(images)), "duplicate bootstrap function"
    return images


def initial_engine(text, iterable_hex, collection_hex):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("new bytes32[](87)") == 1
    assert text.count("uint256 count = inputCount + 81 + (suppliedObject ? 0 : 1)") == 1
    assert "_bootstrapIterable" not in text
    old_collection = bootstrap(text, "Collection")
    assert len(bytes.fromhex(old_collection)) == 317
    assert hashlib.sha256(bytes.fromhex(old_collection)).hexdigest() == PARENT_COLLECTION_SHA256
    assert text.count("_isNamedClass(c, bytes(\"java/lang/Iterable\"))") == 0
    result = text.replace(PARENT_DOMAIN, DOMAIN)
    result = result.replace("new bytes32[](87)", "new bytes32[](88)")
    iterable_constant = ("    // Iterable root commitment is constant-folded; its image remains appended below.\n"
                         "    bytes32 private constant DBOOT_ITERABLE = keccak256(hex\"" + iterable_hex + "\");\n")
    assert result.count("    bytes32 private constant DCFG =") == 1
    result = result.replace("    bytes32 private constant DCFG =", iterable_constant + "    bytes32 private constant DCFG =")
    result = result.replace(
        """        h[85] = keccak256(_bootstrapTreeMap());
        h[86] = keccak256(_bootstrapWeakReference());
        return keccak256(abi.encode(DBOOT, h));""",
        """        h[85] = keccak256(_bootstrapTreeMap());
        h[86] = keccak256(_bootstrapWeakReference());
        // Iterable appends after the complete 87-image tail; Collection is the
        // only historical image replaced to expose this interface edge.
        h[87] = DBOOT_ITERABLE;
        return keccak256(abi.encode(DBOOT, h));""",
    )
    result = result.replace(
        "uint256 count = inputCount + 81 + (suppliedObject ? 0 : 1)",
        "uint256 count = inputCount + 82 + (suppliedObject ? 0 : 1)",
    )
    tree_helper = """    // TreeMap is an append-only constructor image. It deliberately has no
    // SortedMap/NavigableMap or mutation surface before a measured use.
    function _appendTreeMapBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapTreeMap();
    }
"""
    iterable_helper = """
    function _appendWeakReferenceAndIterable(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapWeakReference();
        classes[at + 1].data = _bootstrapIterable();
    }
"""
    assert result.count(tree_helper) == 1
    result = result.replace(tree_helper, tree_helper + iterable_helper)
    result = result.replace(
        """        // Bounded StringBuilder appends after every prior immutable bootstrap.
        _appendStringBuilderBootstrap(p.classes, classSlot + 45);
        // TreeMap remains at slot85; WeakReference appends at slot86 only.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        p.classes[classSlot + 47].data = _bootstrapWeakReference();
        p.classClass = classSlot;""",
        """        // Bounded StringBuilder appends after every prior immutable bootstrap.
        _appendStringBuilderBootstrap(p.classes, classSlot + 45);
        // TreeMap remains at slot85; the outlined helper appends WeakReference at
        // slot86 and Iterable at slot88 without moving a historical image.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        _appendWeakReferenceAndIterable(p.classes, classSlot + 47);
        p.classClass = classSlot;""",
    )
    result = result.replace(
        """    function _isReservedCollectionClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes(\"java/util/Iterator\"))""",
        """    function _isReservedCollectionClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes(\"java/lang/Iterable\"))
            || _isNamedClass(c, bytes(\"java/util/Iterator\"))""",
    )
    old = re.search(r"    function _bootstrapCollection\(\) private pure returns \(bytes memory\) \{ return hex\"[0-9a-f]+\"; \}", result)
    assert old
    result = result[:old.start()] + '    function _bootstrapCollection() private pure returns (bytes memory) { return hex"' + collection_hex + '"; }' + result[old.end():]
    weak = re.search(r"    function _bootstrapWeakReference\(\) private pure returns \(bytes memory\) \{ return hex\"[0-9a-f]+\"; \}\n", result)
    assert weak
    iterable = '    function _bootstrapIterable() private pure returns (bytes memory) { return hex"' + iterable_hex + '"; }\n'
    result = result[:weak.end()] + iterable + result[weak.end():]
    assert result.count(DOMAIN) == 9
    assert result.count("new bytes32[](88)") == 1
    assert result.count("h[87] = DBOOT_ITERABLE;") == 1
    assert result.count("bytes32 private constant DBOOT_ITERABLE = keccak256(hex\"" + iterable_hex + "\");") == 1
    assert result.count("uint256 count = inputCount + 82 + (suppliedObject ? 0 : 1)") == 1
    assert result.count("_appendWeakReferenceAndIterable(p.classes, classSlot + 47);") == 1
    assert result.count("_isNamedClass(c, bytes(\"java/lang/Iterable\"))") == 1
    return result


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
    assert result.count(DOMAIN) == 4 and result.count(ENGINE) == 1
    return result


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)
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
        (r"len\(engineRun\) != 391802", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 391802", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-61fd1832a", "parentEvidence": "parent-61fd1832a", "sha256": inputs,
}
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 87
assert parent_pins["rawLimits"] == [33, 262158]
assert parent_pins["diagnosticClassBound"] == 120
assert parent_pins["engine"]["bytes"] == 391802
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

iterable_source = (stage / "bootstrap/java/lang/Iterable.java").read_text()
collection_source = (stage / "bootstrap/java/util/Collection.java").read_text()
assert iterable_source == """package java.lang;
import java.util.Iterator;
public interface Iterable<T> { Iterator<T> iterator(); }
"""
assert collection_source == """package java.util;
public interface Collection<E> extends java.lang.Iterable<E> {
  boolean add(E value);
  int size();
  Iterator<E> iterator();
  boolean isEmpty();
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="iterable-link-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    iterable = tmp / "java/lang/Iterable.java"
    collection = tmp / "java/util/Collection.java"
    iterable.parent.mkdir(parents=True); collection.parent.mkdir(parents=True)
    iterable.write_text(iterable_source); collection.write_text(collection_source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, iterable, collection], check=True)
    iterable_image = (out / "java/lang/Iterable.class").read_bytes()
    collection_image = (out / "java/util/Collection.class").read_bytes()
assert len(iterable_image) == 215 and hashlib.sha256(iterable_image).hexdigest() == ITERABLE_SHA256
assert len(collection_image) == 368 and hashlib.sha256(collection_image).hexdigest() == COLLECTION_SHA256
assert iterable_image.hex() == (stage / "bootstrap/java/lang/Iterable.class.hex").read_text().strip()
assert collection_image.hex() == (stage / "bootstrap/java/util/Collection.class.hex").read_text().strip()
assert iterable_image[:8] == collection_image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/lang/Iterable", b"java/util/Iterator", b"iterator", b"()Ljava/util/Iterator;"):
    assert required in iterable_image, required
for forbidden in (b"forEach", b"spliterator", b"java/util/function", b"java/util/Spliterator"):
    assert forbidden not in iterable_image, forbidden
for required in (b"java/util/Collection", b"java/lang/Iterable", b"java/util/Iterator", b"add", b"size", b"iterator", b"isEmpty"):
    assert required in collection_image, required
for forbidden in (b"forEach", b"spliterator", b"java/util/function", b"java/util/Spliterator"):
    assert forbidden not in collection_image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine, iterable_image.hex(), collection_image.hex())
parent_images = bootstrap_images(parent_engine)
images = bootstrap_images(engine)
assert set(images) == set(parent_images) | {"_bootstrapIterable"}
for name, image in parent_images.items():
    if name != "_bootstrapCollection":
        assert images[name] == image, name
assert hashlib.sha256(bytes.fromhex(images["_bootstrapCollection"])).hexdigest() == COLLECTION_SHA256
assert hashlib.sha256(bytes.fromhex(images["_bootstrapIterable"])).hexdigest() == ITERABLE_SHA256
assert len(images) == 88
for fixed in (
    "MAX_RAW_CLASSES = 33;", "MAX_RAW_BYTES = 262158;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](88)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(33), uint32(262158)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[70] = keccak256(_bootstrapInteger());",
    "h[86] = keccak256(_bootstrapWeakReference());", "h[87] = DBOOT_ITERABLE;",
    "p.classes[classSlot + 31].data = _bootstrapInteger();",
    "_appendWeakReferenceAndIterable(p.classes, classSlot + 47);",
):
    assert engine.count(fixed) == 1, fixed
assert engine.count("uint256 count = inputCount + 82 + (suppliedObject ? 0 : 1)") == 1

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
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_diagnostic.py").read_text().replace("classes<=120", "classes<=121")
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

expected_args = sys.argv[1:]
if expected_args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(expected_args) == 2 and expected_args[0] == "--built"
    pins = json.loads(Path(expected_args[1]).read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
    bootstrap_sha["Collection"] = COLLECTION_SHA256
    bootstrap_sha["Iterable"] = ITERABLE_SHA256
    expected_pins = {
        "basis": "parent-61fd1832a", "parentEvidence": "parent-61fd1832a", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 88,
        "bootstrapSHA256": bootstrap_sha,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [33, 262158], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 121, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
    "acceptedParent": "parent-61fd1832a", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 88,
    "replacedBootstrap": "java/util/Collection", "appendedBootstrap": "java/lang/Iterable",
    "iterable": {"bytes": len(iterable_image), "sha256": ITERABLE_SHA256, "onlyMethod": "Iterator iterator()"},
    "collection": {"bytes": len(collection_image), "sha256": COLLECTION_SHA256,
                   "preserved": "add,size,iterator,isEmpty", "addedSuperinterface": "java/lang/Iterable"},
    "rawLimits": [33, 262158], "diagnosticClassBound": 121,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
