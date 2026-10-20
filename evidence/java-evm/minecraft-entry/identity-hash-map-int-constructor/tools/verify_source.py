#!/usr/bin/env python3
"""Verify the append-only IdentityHashMap(int) bootstrap delta and Java 8 image."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
PINS = json.loads((STAGE / "pins.json").read_text())
BASE_COMMIT = PINS["baseCommit"]
BASE_STAGE = "evidence/java-evm/minecraft-entry/array-list-raw150-byte1063930"
JDK = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JDK / "bin/javac"
RTJAR = JDK / "jre/lib/rt.jar"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{BASE_STAGE}/{path}"], cwd=ROOT)


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old)
    return text.replace(old, new, 1)


assert BASE_COMMIT == "c4c85871b8cb59858ee6e58c563823626cffb2f6"
base_engine = git_blob("engine/MCEntryInterpreter.sol").decode()
engine_path = STAGE / "engine/MCEntryInterpreter.sol"
engine = engine_path.read_text()
assert sha(base_engine.encode()) == PINS["baseEngineSourceSHA256"]
expected_engine = base_engine
expected_engine = replace_once(expected_engine, "inputCount + 93 +", "inputCount + 94 +")
expected_engine = replace_once(expected_engine, "bytes32[] memory h = new bytes32[](99);",
                              "bytes32[] memory h = new bytes32[](100);")
expected_engine = replace_once(expected_engine,
    """        h[98] = keccak256(_bootstrapArrayList());
        return keccak256(abi.encode(DBOOT, h));""",
    """        h[98] = keccak256(_bootstrapArrayList());
        // IdentityHashMap is the sole new image; every prior root slot is unchanged.
        h[99] = keccak256(_bootstrapIdentityHashMap());
        return keccak256(abi.encode(DBOOT, h));""")
expected_engine = replace_once(expected_engine,
    """        p.classes[classSlot + 59].data = _bootstrapArrayList();
    }""",
    """        p.classes[classSlot + 59].data = _bootstrapArrayList();
        // IdentityHashMap appends as image100 without shifting any prior slot.
        p.classes[classSlot + 60].data = _bootstrapIdentityHashMap();
    }""")
expected_engine = replace_once(expected_engine,
    """            || _isNamedClass(c, bytes("java/util/Map$Entry"));""",
    """            || _isNamedClass(c, bytes("java/util/Map$Entry"))
            || _isNamedClass(c, bytes("java/util/IdentityHashMap"));""")
class_source = (STAGE / "bootstrap/java/util/IdentityHashMap.java").read_text()
assert "class IdentityHashMap<K, V> extends AbstractMap<K, V>" in class_source
assert "implements Map<K, V>, Cloneable, Serializable" in class_source
assert "transient Object[] table;" in class_source and "int size;" in class_source
assert "public int size() { return size; }" in class_source
assert "public boolean isEmpty() { return size == 0; }" in class_source
native_names = {
    "containsKey", "containsValue", "get", "put", "remove", "putAll", "clear",
    "keySet", "values", "entrySet", "equals", "hashCode", "toString", "clone",
    "getOrDefault", "forEach", "replaceAll", "putIfAbsent", "replace",
    "computeIfAbsent", "computeIfPresent", "compute", "merge",
}
for name in native_names:
    assert re.search(r"\bpublic native [^;{}]+\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*;", class_source), name
assert "public IdentityHashMap(int expectedMaxSize)" in class_source
assert "if (expectedMaxSize > 178956970) return 536870912;" in class_source
assert "if (expectedMaxSize <= 2) return 4;" in class_source
assert "Integer.highestOneBit(expectedMaxSize + (expectedMaxSize << 1))" in class_source
assert "table = new Object[2 * capacity];" in class_source

# Build the only new bootstrap image with the pinned local Java 8 compiler.
with tempfile.TemporaryDirectory(prefix="idmap-bootstrap-", dir=os.environ.get("TMPDIR") or None) as temp:
    temp = Path(temp)
    stripped = temp / "rt.jar"
    shutil.copyfile(RTJAR, stripped)
    subprocess.run(["zip", "-q", "-d", str(stripped), "java/util/IdentityHashMap.class"],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = temp / "classes"
    output.mkdir()
    subprocess.run([str(JAVAC), "-g:none", "-bootclasspath", str(stripped), "-source", "8", "-target", "8",
                    "-d", str(output), str(STAGE / "bootstrap/java/util/IdentityHashMap.java")],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    image = (output / "java/util/IdentityHashMap.class").read_bytes()

assert len(image) == PINS["identityHashMapBootstrapBytes"]
assert sha(image) == PINS["identityHashMapBootstrapSHA256"]
assert image[:8] == bytes.fromhex("cafebabe00000034"), "bootstrap must be Java 8 classfile version 52"
image_hex = image.hex()
function = f'    function _bootstrapIdentityHashMap() private pure returns (bytes memory) {{ return hex"{image_hex}"; }}'
expected_engine = expected_engine.replace(
    "    function _bootstrapWeakReference() private pure returns (bytes memory) {",
    "\n" + function + "\n\n    function _bootstrapWeakReference() private pure returns (bytes memory) {",  1)
assert expected_engine != base_engine
assert engine == expected_engine, "engine changes beyond exact raw150->100-image constructor/size/reserved-name delta"
assert PINS["engineSourceSHA256"] == sha(engine.encode())
assert "uint256 count = inputCount + 94 +" in engine
assert "MAX_RAW_CLASSES = 150" in engine and "MAX_RAW_BYTES = 1063930" in engine
assert "MAX_CHECKPOINT_BYTES = 1048576" in engine
assert "uint32(150), uint32(1063930)," in engine and "uint32(1048576)" in engine

# The old 99 root inputs and their order are byte-identical because the exact
# source transform above appends only h[99]/classSlot+60.
assert engine.count("h[99] = keccak256(_bootstrapIdentityHashMap());") == 1
assert engine.count("p.classes[classSlot + 60].data = _bootstrapIdentityHashMap();") == 1

base_coord = git_blob("coordinator/MCEntryCoordinator.sol").decode()
coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
assert sha(base_coord.encode()) == PINS["baseCoordinatorSourceSHA256"]
expected_coord = replace_once(base_coord, PINS["baseEngineRuntimeKeccak256"],
                              PINS["engineRuntimeKeccak256"])
assert coord == expected_coord, "coordinator changes beyond the fresh engine codehash binding"
assert PINS["coordinatorSourceSHA256"] == sha(coord.encode())

# All old ArrayList source/compiler fixtures remain byte-identical to the base.
for directory in ("bootstrap", "fixtures/src"):
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE_COMMIT, f"{BASE_STAGE}/{directory}"],
        cwd=ROOT, text=True,
    ).splitlines()
    for row in names:
        name = row.removeprefix(f"{BASE_STAGE}/")
        assert (STAGE / name).read_bytes() == git_blob(name), name

assert PINS["rawClassLimit"] == 150 and PINS["rawByteLimit"] == 1063930
assert PINS["runtimeCapBytes"] == 1048576 and PINS["checkpointCapBytes"] == 1048576
assert PINS["bootstrapCount"] == 100 and PINS["diagnosticClassMaximum"] == 250
assert PINS["globalNativeBindings"] == 21 and PINS["stringLocalBinding"] == 12
print(json.dumps({
    "profile": PINS["profile"], "baseCommit": BASE_COMMIT,
    "baseEngineSourceSHA256": sha(base_engine.encode()),
    "engineSourceSHA256": sha(engine.encode()), "coordinatorSourceSHA256": sha(coord.encode()),
    "identityHashMapBootstrapBytes": len(image), "identityHashMapBootstrapSHA256": sha(image),
    "bootstrapImages": 100, "prior99RootOrderByteIdentical": True,
    "rawClassLimit": 150, "rawByteLimit": 1063930, "diagnosticClassMaximum": 250,
    "runtimeCapBytes": 1048576, "checkpointCapBytes": 1048576,
    "newNativeBindings": 0, "unimplementedMapOperationsAreRefusalOnlyNativeDeclarations": True,
}, indent=2))
