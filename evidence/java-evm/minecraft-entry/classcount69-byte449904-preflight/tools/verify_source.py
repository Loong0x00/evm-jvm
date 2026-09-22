#!/usr/bin/env python3
"""Verify the literal raw69 / byte449904 capacity delta from parent-e8569f01e."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-e8569f01e"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "d700e6142026d412fd679a8b7ae0d4e99cf28deac2e332b44a2c120d328b916f",
    "artifacts/coordinator/MCEntryCoordinator.sol": "178d392dc612b4b195060060660eaaf0347d254d389fa3a5f83dcfd49e981f44",
    "canonical-driver.go.txt": "c036c669e34b06e9d467c97f08ab4631333686be29a722afc2ee601a5cbe2618",
    "checkpoint_diagnostic.py": "83c9f0e0910b73fba041b10678f0cf068b04735641940214f7fec142c23d7150",
    "checkpoint_frames.py": "83c9f0e0910b73fba041b10678f0cf068b04735641940214f7fec142c23d7150",
    "artifacts/root-commitment.json": "fe5a889c9717490f409518790b5cec33fd1bf7b1ae5352fb9e9260a05237552f",
    "bootstrap/java/lang/String.java": "0f31c2327d872c80db88e4a6aca5a663118b8c2fa3bba5d756d6dd65b1cfe538",
    "bootstrap/java/lang/String.class.hex": "febb1d90ae7055952e5f3c22c4f4f06e647037836ac13afb2c27b42617a1d924",
    "bootstrap/java/lang/String.sha256": "b64aee12bae000c558fb3aac16de780713bb9bd7bd2f9e36b14a0422bed6affa",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
ENGINE = {
    "bytes": 377043,
    "initSHA256": "18287d88669801233c3a5eda5554ab67b6de3f63a3160f15107199d1c9fae43b",
    "runtimeSHA256": "61f08e430b18c3bf6b2f2218a93733c11b243440e8147708e11f2c0f2c5ed4eb",
    "runtimeKeccak256": "2c843a975e7947992ef13c68ef98eb0bfe37a60496b5623425fa859110b0770d",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "8624bd0e754d1ab7befef4fd909e8f25806bec3cab1f72673c0ee416f371f9c0",
    "runtimeSHA256": "add021b633aa8f2d31d521256f4d8e67c3d8c5ef9a5bc1b58c9631d10c8d3dda",
    "runtimeKeccak256": "7f07a10e95b8cf56dc795deee8c7d027c5950871622c4759f7eff08019b6baa5",
}
STRING_SHA256 = "42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec"
INTEGER_SHA256 = "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd"
MAP_ENTRY_SHA256 = "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5"
ROOT = "2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    actual = text.count(old)
    assert actual == count, (old, actual, count)
    return text.replace(old, new)


def function_image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
parent_pins = json.loads((parent / "pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
assert parent_pins["rawLimits"] == [68, 394767]
assert parent_pins["diagnosticClassBound"] == 163
assert parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["bootstrapSHA256"]["String"] == STRING_SHA256
assert parent_pins["integer"]["sha256"] == INTEGER_SHA256
assert parent_pins["mapEntry"]["sha256"] == MAP_ENTRY_SHA256
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "parent-e8569f01e",
    "parentEvidence": "parent-e8569f01e/{artifacts,bootstrap,canonical-driver,checkpoint}",
    "rawLimits": [69, 449904],
    "diagnosticClassBound": 164,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount69-byte449904",
})
assert pins == expected_pins
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 95 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14

# The accepted String.indexOf image/root, Map.Entry image95, Integer slot70,
# source order, native bindings and all non-capacity engine code stay exact.
for relative, parent_relative in (
    ("root-commitment.json", "artifacts/root-commitment.json"),
    ("bootstrap/java/lang/String.java", "bootstrap/java/lang/String.java"),
    ("bootstrap/java/lang/String.class.hex", "bootstrap/java/lang/String.class.hex"),
    ("bootstrap/java/lang/String.sha256", "bootstrap/java/lang/String.sha256"),
    ("engine/build.js", "artifacts/engine/build.js"),
    ("coordinator/build.js", "artifacts/coordinator/build.js"),
):
    assert (stage / relative).read_bytes() == (parent / parent_relative).read_bytes(), relative
parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = exact(parent_engine, "MAX_RAW_CLASSES = 68;", "MAX_RAW_CLASSES = 69;")
engine = exact(engine, "MAX_RAW_BYTES = 394767;", "MAX_RAW_BYTES = 449904;")
engine = exact(engine, "uint32(68), uint32(394767)", "uint32(69), uint32(449904)")
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == engine
assert hashlib.sha256(function_image(engine, "_bootstrapString")).hexdigest() == STRING_SHA256
assert hashlib.sha256(function_image(engine, "_bootstrapInteger")).hexdigest() == INTEGER_SHA256
assert hashlib.sha256(function_image(engine, "_bootstrapMapEntry")).hexdigest() == MAP_ENTRY_SHA256
assert len(re.findall(r"h\[\d+\] = ", engine)) == 95
assert bytes.fromhex((stage / "bootstrap/java/lang/String.class.hex").read_text().strip()) == function_image(engine, "_bootstrapString")

parent_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, "[68]", "[69]", 4)
coord = exact(coord, "n > 68", "n > 69")
coord = exact(coord, "394767", "449904", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord

parent_go = (parent / "canonical-driver.go.txt").read_text()
go = exact(parent_go, "len(m.Decoders) > 68", "len(m.Decoders) > 69")
go = exact(go, "len(parts) > 68", "len(parts) > 69")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert (stage / "tools/Go.txt").read_text() == go
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == exact((parent / name).read_text(), "classes<=163", "classes<=164")

# The fixture/gate sources admit only generated sibling inputs and carry exact
# class and byte frontiers; no original/JAR/resource fixture is tracked.
fixtures = (stage / "tools/generate_fixtures.py").read_text()
assert 'count_fixture("count-69", 69)' in fixtures
assert 'count_fixture("count-70", 70)' in fixtures
assert 'count_fixture("count-69-449904", 69, 449904)' in fixtures
assert 'count_fixture("count-69-449905", 69, 449905)' in fixtures
assert '"rawLimits": [69, 449904]' in fixtures
gate = (stage / "tools/gate.py").read_text()
for fragment in ('[69, 449904]', 'diagnosticClassBound"] == 164', 'q_equivalent("count-69")',
                 '"count-70.zip"', 'count-69-449904', 'count-69-449905', '"1", "70"'):
    assert fragment in gate, fragment
assert "<= 1200" in gate and 'actualDI0ReadSizes"]) == 449904' in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": ROOT,
    "stringSHA256": STRING_SHA256, "mapEntrySHA256": MAP_ENTRY_SHA256,
    "integerSHA256": INTEGER_SHA256,
    "verification": "literal-capacity-only-source-delta+accepted-string-root+generated-input-only",
}, indent=2))
