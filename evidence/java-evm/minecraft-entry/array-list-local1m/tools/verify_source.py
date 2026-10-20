#!/usr/bin/env python3
"""Verify the bounded append against the exact parent raw75 source and Java 8 images."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/parent-raw75-byte531965/artifacts/engine/MCEntryInterpreter.sol"
ENGINE = STAGE / "engine/MCEntryInterpreter.sol"
PINS = json.loads((STAGE / "pins.json").read_text())
JAVAC = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
RTJAR = Path("/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar")


def literal_image(source, name):
    m = re.search(
        rf'function _bootstrap{name}\(\) private pure returns \(bytes memory\) \{{ return hex"([0-9a-f]+)"; \}}',
        source,
    )
    assert m, name
    return m.group(1)


def replace_once(text, old, new):
    n = text.count(old)
    assert n == 1, (n, old[:120])
    return text.replace(old, new, 1)


base = BASE.read_text()
engine = ENGINE.read_text()
assert JAVAC.is_file() and RTJAR.is_file()
version = subprocess.check_output([JAVAC, "-version"], text=True, stderr=subprocess.STDOUT).strip()
assert version == "javac 1.8.0_504", version

# Compile only stage-owned bootstrap sources. The platform ArrayList and every
# replaced parent interface are removed from the compiler bootclasspath first.
with tempfile.TemporaryDirectory(prefix="mc-array-list-images-", dir=ROOT / "build") as temp:
    temp = Path(temp)
    rt = temp / "rt.jar"
    classes = temp / "classes"
    classes.mkdir()
    shutil.copyfile(RTJAR, rt)
    subprocess.run(
        ["zip", "-q", "-d", rt,
         "java/util/AbstractCollection.class", "java/util/Collection.class",
         "java/util/List.class", "java/util/RandomAccess.class",
         "java/util/AbstractList.class", "java/util/ArrayList.class"],
        check=True,
    )
    stub = STAGE / "bootstrap/stub/java/util"
    sources = [
        stub / "Collection.java", stub / "List.java", stub / "RandomAccess.java",
        stub / "AbstractCollection.java",
        STAGE / "bootstrap/java/util/AbstractList.java",
        STAGE / "bootstrap/java/util/ArrayList.java",
    ]
    subprocess.run([JAVAC, "-g:none", "-bootclasspath", rt, "-d", classes, *sources], check=True)
    generated = {
        "AbstractList": (classes / "java/util/AbstractList.class").read_bytes(),
        "ArrayList": (classes / "java/util/ArrayList.class").read_bytes(),
    }

# The source has one root helper plus the named immutable class-image functions.
# Exact reverse-construction below proves all prior image implementations/bytes stayed fixed.
assert base.count("function _bootstrap") == 98
assert engine.count("function _bootstrap") == 100
for name, data in generated.items():
    assert bytes.fromhex(literal_image(engine, name)) == data, name

# Reconstruct the candidate from the exact base plus only the measured append.
expected = base
expected = replace_once(expected, "bytes32[] memory h = new bytes32[](97);",
                        "bytes32[] memory h = new bytes32[](99);")
expected = replace_once(
    expected,
    "        h[96] = DBOOT_RANDOM;\n        return keccak256(abi.encode(DBOOT, h));",
    "        h[96] = DBOOT_RANDOM;\n"
    "        // Append the minimal ArrayList hierarchy after all 97 accepted images.\n"
    "        h[97] = keccak256(_bootstrapAbstractList());\n"
    "        h[98] = keccak256(_bootstrapArrayList());\n"
    "        return keccak256(abi.encode(DBOOT, h));",
)
expected = replace_once(expected, "uint256 count = inputCount + 91 + (suppliedObject ? 0 : 1)",
                        "uint256 count = inputCount + 93 + (suppliedObject ? 0 : 1)")
expected = replace_once(
    expected,
    "        p.classes[classSlot + 57].data = _bootstrapRandom();",
    "        p.classes[classSlot + 57].data = _bootstrapRandom();\n"
    "        // ArrayList support appends after the exact prior97-image bootstrap tail.\n"
    "        p.classes[classSlot + 58].data = _bootstrapAbstractList();\n"
    "        p.classes[classSlot + 59].data = _bootstrapArrayList();",
)
expected = replace_once(
    expected,
    '            || _isNamedClass(c, bytes("java/util/concurrent/CopyOnWriteArrayListIterator"));',
    '            || _isNamedClass(c, bytes("java/util/concurrent/CopyOnWriteArrayListIterator"))\n'
    '            || _isNamedClass(c, bytes("java/util/AbstractList"))\n'
    '            || _isNamedClass(c, bytes("java/util/ArrayList"));',
)
new_function_block = (
    "\n\n    /// @dev Bounded Java 8 AbstractList construction/type-link parent. No List\n"
    "    /// indexing, mutation, or iteration helpers are provided by this image.\n"
    f'    function _bootstrapAbstractList() private pure returns (bytes memory) {{ return hex"{generated["AbstractList"].hex()}"; }}\n'
    "\n    /// @dev ArrayList(int): eager Object[] storage, initial size zero, size() and\n"
    "    /// inherited AbstractCollection.isEmpty(). add/iterator are unbound native\n"
    "    /// declarations only so the concrete type closes Collection; calls refuse.\n"
    f'    function _bootstrapArrayList() private pure returns (bytes memory) {{ return hex"{generated["ArrayList"].hex()}"; }}'
)
random_function = re.search(
    r'    function _bootstrapRandom\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}',
    expected,
)
assert random_function
expected = expected[:random_function.end()] + new_function_block + expected[random_function.end():]
if expected != engine:
    for i, (a, b) in enumerate(zip(expected, engine)):
        if a != b:
            print(json.dumps({"diffAt": i, "expected": expected[i-160:i+240], "actual": engine[i-160:i+240]}, indent=2))
            break
    raise AssertionError("candidate contains a change outside the append-only source patch")

assert hashlib.sha256(engine.encode()).hexdigest() == PINS["engineSourceSHA256"]
assert hashlib.sha256(base.encode()).hexdigest() == PINS["parentEngineSourceSHA256"]
for name, data in generated.items():
    assert len(data) == PINS["newBootstrapImages"][name]["bytes"]
    assert hashlib.sha256(data).hexdigest() == PINS["newBootstrapImages"][name]["sha256"]

# Explicitly pin the immutable LOCAL limits and inherited P28/raw75 profile.
for needle in (
    "MAX_RAW_CLASSES = 75", "MAX_RAW_BYTES = 531965", "new bytes32[](99)",
    "inputCount + 93 +", "classSlot + 58", "classSlot + 59",
    'bytes("java/util/AbstractList")', 'bytes("java/util/ArrayList")',
):
    assert needle in engine, needle
assert "runtime.length/2>1024*1024" in (STAGE / "engine/build.js").read_text()
assert PINS["runtimeCapBytes"] == 1048576

result = {
    "profile": "LOCAL1M P28 raw75 append-only ArrayList(int); behavior acceptance pending",
    "java8Compiler": version,
    "baseBootstrapImages": 97,
    "candidateBootstrapImages": 99,
    "oldImagesByteIdentical": True,
    "newImages": {
        name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in generated.items()
    },
    "scope": "source/image verification only; no EVM execution or original replay",
}
print(json.dumps(result, indent=2))
