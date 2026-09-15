#!/usr/bin/env python3
"""Strict source-only verifier for bounded TreeMap construction.

It consumes only the accepted parent-fe370c161 source evidence and this stage's
Java-8-produced TreeMap input. It never opens an original server artifact,
class, resource, checkpoint, or world.
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
parent = stage.parent / "parent-fe370c161"

PARENT_FILES = {
    "pins.json": "3627fbb4be073e42960bc231f348f5250309c024064c3f99baa4038fb547f044",
    "artifacts/engine/MCEntryInterpreter.sol": "d199330dd9917e14ef6d892ce24c8fd5981702e3a7244e1594d7d5faf62cd050",
    "artifacts/coordinator/MCEntryCoordinator.sol": "1d8eaa51943dd4ab6ef361313aca85c2f222b8a193c3f1c5de85c577fe9d6d51",
    "executed-driver.go.txt": "af1ad7ecfc1b119ad62a9500248096917279695fa4ed440e37c17799e151fcc8",
    "checkpoint_frames.py": "13fe08107dba926f0134dbd1c1b5b958987149b78c947df2ae30054f8141629b",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-STRING-LAST-INDEX-P2"
DOMAIN = "MC-TREE-MAP-P1"
PARENT_ENGINE = "4d432d535452494e472d4c415354494e44455832"
ENGINE = "4d432d545245452d4d41502d5031000000000000"
PARENT_OWNER = "4d432d535452494e472d4c415354494e44455850"
OWNER = "4d432d545245452d4d41502d4f31000000000000"
PARENT_RUNTIME_SHA = "5b4148b1164fdc4187c9d28e9788bd60386de53a61eedb25da5bca61dac73db6"
PARENT_RUNTIME_KECCAK = "bb9e01713554271c07b5f8037626466f3766f4b69141ed36e378eb28bec7237d"
PARENT_COORDINATOR_KECCAK = "c919a4fd1b39415dd1a303ff8cf70a22380f08f999eb0e04aa58410ece2f00ef"
TREE_MAP_SHA = "c203bc1cf3e4f7d9901b49f0415e10e0aa6331eb99c366e24f68b6fc2a60e067"
LIMITS_COMMITMENT = "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_images(text):
    pattern = r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";"
    return dict(re.findall(pattern, text))


def expected_engine(parent_engine, image_hex):
    """Apply the sole append-only TreeMap source delta to the accepted parent."""
    assert parent_engine.count(PARENT_DOMAIN) == 9
    text = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
    assert text.count("new bytes32[](85)") == 1
    text = text.replace("new bytes32[](85)", "new bytes32[](86)")
    old = '''        // StringBuilder appends only after the complete 84-image System.err tail.
        h[84] = keccak256(_bootstrapStringBuilder());
        return keccak256(abi.encode(DBOOT, h));'''
    new = '''        // StringBuilder appends only after the complete 84-image System.err tail.
        h[84] = keccak256(_bootstrapStringBuilder());
        // TreeMap appends only after all 85 accepted images.
        h[85] = keccak256(_bootstrapTreeMap());
        return keccak256(abi.encode(DBOOT, h));'''
    assert text.count(old) == 1
    text = text.replace(old, new)
    assert text.count("uint256 count = inputCount + 79 +") == 1
    text = text.replace("uint256 count = inputCount + 79 +", "uint256 count = inputCount + 80 +")
    old = '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"));'''
    new = '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"))
            || _isNamedClass(c, bytes("java/util/TreeMap"));'''
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = '''    function _appendStringBuilderBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapStringBuilder();
    }

    // Keep the immutable post-VFS tail in one helper.'''
    new = '''    function _appendStringBuilderBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapStringBuilder();
    }

    // TreeMap is an append-only constructor image. It deliberately has no
    // SortedMap/NavigableMap or mutation surface before a measured use.
    function _appendTreeMapBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at].data = _bootstrapTreeMap();
    }

    // Keep the immutable post-VFS tail in one helper.'''
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = '''        // Bounded StringBuilder appends after every prior immutable bootstrap.
        _appendStringBuilderBootstrap(p.classes, classSlot + 45);
        p.classClass = classSlot;'''
    new = '''        // Bounded StringBuilder appends after every prior immutable bootstrap.
        _appendStringBuilderBootstrap(p.classes, classSlot + 45);
        // TreeMap remains a constructor-only Object subclass at appended slot 85.
        _appendTreeMapBootstrap(p.classes, classSlot + 46);
        p.classClass = classSlot;'''
    assert text.count(old) == 1
    text = text.replace(old, new)
    marker = '    function _bootstrapStringBuilder() private pure returns (bytes memory) { return hex"'
    at = text.index(marker)
    end = text.index("\n", at)
    text = text[:end] + '''

    // Java 8 javac -source 8 -target 8 -g:none: public Object subclass with
    // exactly the public no-arg constructor. No Map/SortedMap interface or API.
    function _bootstrapTreeMap() private pure returns (bytes memory) { return hex"%s"; }''' % image_hex + text[end:]
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-fe370c161", "parentEvidence": "parent-fe370c161", "sha256": inputs,
}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["bootstrapCount"] == 85
assert parent_pins["diagnosticClassBound"] == 115
assert parent_pins["engine"]["bytes"] == 386525
assert parent_pins["engine"]["runtimeSHA256"] == PARENT_RUNTIME_SHA
assert parent_pins["engine"]["runtimeKeccak256"] == PARENT_RUNTIME_KECCAK
assert parent_pins["coordinator"]["runtimeKeccak256"] == PARENT_COORDINATOR_KECCAK
assert parent_pins["limitsCommitment"] == LIMITS_COMMITMENT
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20

EXPECTED_SOURCE = """package java.util;
public class TreeMap {
  public TreeMap() {}
}
"""
source = (stage / "bootstrap/java/util/TreeMap.java").read_text()
assert source == EXPECTED_SOURCE
pins = json.loads((stage / "bootstrap/pins.json").read_text())
assert pins == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "TreeMap": {
        "source": "java/util/TreeMap.java", "classHex": "java/util/TreeMap.class.hex",
        "bytes": 132, "sha256": TREE_MAP_SHA,
        "surface": "public constructor-only Object subclass; no interfaces, fields, or methods beyond <init>()V",
        "omitted": "SortedMap/NavigableMap/Map, comparator, ordering, mutation, get/put/entrySet/lastKey, serialization, clone",
    },
}

# Compilation is Java-8 provenance only. The resulting image is consumed by
# Solidity and later executed by EVM, never by a host Java execution path.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="tree-map-constructor-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/util/TreeMap.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = tmp / "out"
    out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/util/TreeMap.class").read_bytes()
assert len(image) == 132 and hashlib.sha256(image).hexdigest() == TREE_MAP_SHA
assert image.hex() == (stage / "bootstrap/java/util/TreeMap.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert image.count(b"java/util/TreeMap") == 1
assert image.count(b"java/lang/Object") == 1
assert image.count(b"<init>") == 1 and image.count(b"()V") == 1
for forbidden in (b"java/util/Map", b"java/util/SortedMap", b"java/util/NavigableMap",
                  b"put", b"get", b"entrySet", b"lastKey", b"comparator", b"clone",
                  b"Serializable"):
    assert forbidden not in image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(parent_engine, image.hex())
parent_images = bootstrap_images(parent_engine)
images = bootstrap_images(engine)
assert len(parent_images) == 85 and len(images) == 86
assert set(images) == set(parent_images) | {"_bootstrapTreeMap"}
for name, value in parent_images.items():
    assert images[name] == value, name
assert images["_bootstrapTreeMap"] == image.hex()
assert engine.count("h[85] = keccak256(_bootstrapTreeMap());") == 1
assert engine.count("new bytes32[](86)") == 1
assert engine.count("uint256 count = inputCount + 80 +") == 1
assert engine.count('bytes("java/util/TreeMap")') == 1
assert engine.count("function _appendTreeMapBootstrap") == 1
assert engine.count("_appendTreeMapBootstrap(p.classes, classSlot + 46);") == 1
assert engine.count("function _appendTailBootstraps(Program memory p, uint256 at, bool suppliedRunnable) private pure") == 1
assert engine.count("_appendStringBuilderBootstrap(p.classes, classSlot + 45);") == 1
for fixed in (
    "MAX_RAW_CLASSES = 30;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 12;", "uint32[11] memory limits",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
assert coordinator == expected_coordinator
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[30]") == 4 and coordinator.count("n > 30") == 1 and "262144" in coordinator

driver_parent = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)
assert driver == expected_driver
assert driver.count(DOMAIN) == 5 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert PARENT_RUNTIME_SHA in driver and ("0x" + PARENT_RUNTIME_KECCAK) in driver
assert ("0x" + PARENT_COORDINATOR_KECCAK) in driver and driver.count("386525") == 2
assert (stage / "tools/checkpoint_frames.py").read_text() == (parent / "checkpoint_frames.py").read_text().replace("classes<=115", "classes<=116")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

print(json.dumps({
    "acceptedParent": "parent-fe370c161", "parentInputsVerified": len(inputs),
    "parentEngineSourceSHA256": PARENT_FILES["artifacts/engine/MCEntryInterpreter.sol"],
    "parentRuntimeSHA256": PARENT_RUNTIME_SHA, "parentRuntimeKeccak256": PARENT_RUNTIME_KECCAK,
    "domain": DOMAIN, "bootstrapImages": 86, "treeMapSlot": 85,
    "soleBootstrapAppend": "java/util/TreeMap", "rawLimits": [30, 262144],
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 116,
    "treeMap": {"bytes": len(image), "sha256": TREE_MAP_SHA, "method": "<init>()V",
                "super": "java/lang/Object", "interfaces": 0},
    "limitsCommitment": LIMITS_COMMITMENT,
}, indent=2))
