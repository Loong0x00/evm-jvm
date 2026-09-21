#!/usr/bin/env python3
"""Verify raw55/355563 is an exact capacity-only delta from parent-0fd9ef7f5."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-0fd9ef7f5"
prior = stage.parent / "classcount54-byte352504-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "c28ee40de4807d3aa134f9c60da893b7a8db17499f0a6e1062bf75ccc090249f",
    "runtimeSHA256": "b5e9aa58238ec8cee7aa63c460198a17b7cefcd2a8fb3f03b00e52c2047f8723",
    "runtimeKeccak256": "dcdf1f7e8b52093533993a71f40d44681b982bf0365b16de638647e9e201a973",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "3e767703cea0198025838866d32e43d81849fa5bf98274c28f1c3a5082fb69df",
    "runtimeSHA256": "3f49625e5624c8c79bd015e6926bd759005e6ef1b80118c1bf142df1eafe9bdb",
    "runtimeKeccak256": "b1b707cfdb61f02a2180e2704a9eb5444aa477bf0a097a9c8fce09c078664ea9",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "92ce6c8f5dd32b25976056b9734be72851ff4ef9b24d1d4abbd11ff2a6576589",
    "artifacts/coordinator/MCEntryCoordinator.sol": "31ce2f252895f078ba6b861fb77602b9e87dfb4f39c252db00b984069d546cf1",
    "canonical-driver.go.txt": "18636e1db0ad351db0c6b09308f7b40631d9c08348021ca14a6808ef8e13cb1a",
    "checkpoint_diagnostic.py": "774bf46deab30aa0d42fcaa778a4b67875bb00a9ed1b431193818bac9797131c",
    "checkpoint_frames.py": "774bf46deab30aa0d42fcaa778a4b67875bb00a9ed1b431193818bac9797131c",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "e7e65f5d2d9a610f002bcdb569bec1ced1b87c4cc85fa3064533896f1e6bbfd9",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "6ad548a1feb30ed101c81633f0f66a94d09565533e86117066a541ff9d8df561",
    "tools/generate_focused_fixtures.py": "869546239aa11b4667ab0efec4fcb9d50255c2b52fbbabff39bd99ce79af640c",
    "tools/build.py": "a7f4ab068eda0cbdfa68cf7d43d9d95856563d729cf0453c7b3a258303781dee",
    "tools/gate.py": "c76a3de068b5990513b6e404ba9b3234e0e946018ea66fa03064667a0afdaa8e",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def exact(text, old, new, count=1):
    actual = text.count(old)
    assert actual == count, (old, actual, count)
    return text.replace(old, new)

def parent_text(relative):
    return (parent / relative).read_text()

def local_text(relative):
    return (stage / relative).read_text()

for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
for relative, expected in PRIOR_SHA256.items():
    assert sha(prior / relative) == expected, relative

parent_pins = json.loads(parent_text("pins.json"))
pins = json.loads(local_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "0fd9ef7f5",
    "parentEvidence": "parent-0fd9ef7f5/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [55, 355563],
    "diagnosticClassBound": 149,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount55-byte355563",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 54;", "MAX_RAW_CLASSES = 55;")
engine = exact(engine, "MAX_RAW_BYTES = 352504;", "MAX_RAW_BYTES = 355563;")
engine = exact(engine, "uint32(54), uint32(352504)", "uint32(55), uint32(355563)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[54]", "[55]", 4)
coord = exact(coord, "n > 54", "n > 55")
coord = exact(coord, "352504", "355563", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 54", "len(m.Decoders) > 55")
source = exact(source, "len(parts) > 54", "len(parts) > 55")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=148", "classes<=149")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount54-byte352504", "classcount55-byte355563")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56)")
retained = exact(retained, 'count_fixture("count-54-352504", 54, 352504)', 'count_fixture("count-55-355563", 55, 355563)')
retained = exact(retained, 'count_fixture("count-54-352505", 54, 352505)', 'count_fixture("count-55-355564", 55, 355564)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount54-byte352504", "classcount55-byte355563")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw54/byte352504", "raw55/byte355563")
built = exact(built, "classcount54-byte352504", "classcount55-byte355563")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "java-diff-mc-classcount54-byte352504-gate-", "java-diff-mc-classcount55-byte355563-gate-")
    value = exact(value, "java-diff-mc-classcount54-byte352504-build-", "java-diff-mc-classcount55-byte355563-build-")
    value = exact(value, "java-diff-mc-classcount54-byte352504-retained-fixtures-", "java-diff-mc-classcount55-byte355563-retained-fixtures-")
    value = exact(value, "java-diff-mc-classcount54-byte352504-focused-fixtures-", "java-diff-mc-classcount55-byte355563-focused-fixtures-")
    value = exact(value, "[54, 352504]", "[55, 355563]")
    value = exact(value, 'diagnosticClassBound"] == 148', 'diagnosticClassBound"] == 149')
    value = exact(value, 'head["totalClassBytes"] <= 352504', 'head["totalClassBytes"] <= 355563', 2)
    start = value.index("# Exact raw54 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    block = block.replace("raw54", "RAWFOCUS").replace("count-54", "COUNTFOCUS")
    block = block.replace("raw55", "raw56").replace("count-55", "count-56")
    block = block.replace("RAWFOCUS", "raw55").replace("COUNTFOCUS", "count-55")
    block = block.replace("352504", "355563").replace("352505", "355564")
    block = block.replace('"len(m.Decoders) > 54", "len(m.Decoders) > 55"', '"len(m.Decoders) > 55", "len(m.Decoders) > 56"')
    block = block.replace('"len(parts) > 54", "len(parts) > 55"', '"len(parts) > 55", "len(parts) > 56"')
    block = block.replace('text.count("[54]") == 4 and text.count("n > 54") == 1', 'text.count("[55]") == 4 and text.count("n > 55") == 1')
    block = block.replace('assert source.count("len(m.Decoders) > 54") == 1 and source.count("len(parts) > 54") == 1', 'assert source.count("len(m.Decoders) > 55") == 1 and source.count("len(parts) > 55") == 1')
    block = block.replace('text.replace("[54]", "[55]").replace("n > 54", "n > 55")', 'text.replace("[55]", "[56]").replace("n > 55", "n > 56")')
    block = block.replace("# chains agree. Raw55 is independently refused before mutation by the product", "# chains agree. Raw56 is independently refused before mutation by the product")
    block = block.replace('words(refusal) == ["1", "55"]', 'words(refusal) == ["1", "56"]')
    block = block.replace('assert spec["bindingCount"] == 54 and spec["totalClassBytes"] == total', 'assert spec["bindingCount"] == 55 and spec["totalClassBytes"] == total')
    assert "raw54" not in block and "count-54" not in block and "352504" not in block and "352505" not in block
    value = value[:start] + block + value[end:]
    value = exact(value, '"profile": "MC-RAW54-BYTE352504-P1"', '"profile": "MC-RAW55-BYTE355563-P1"')
    old = "Only raw capacity constants advance from raw53/350161/diagnostic147 to raw54/352504/diagnostic148. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw54 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fh replay remains deferred."
    new = "Only raw capacity constants advance from raw54/352504/diagnostic148 to raw55/355563/diagnostic149. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw55 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fo replay remains deferred."
    return exact(value, old, new)

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
