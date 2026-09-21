#!/usr/bin/env python3
"""Verify raw54/352504 is an exact capacity-only delta from parent-462bcc352."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-462bcc352"
prior = stage.parent / "classcount53-byte350161-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "75cae42bb2427218302a5aab98da84bb646a741da5ca28864347514c1eb94711",
    "runtimeSHA256": "608af07f25938cb3a75b0feb8e7dd9032a44a92d309aa61d3a06f11a6bee6fc7",
    "runtimeKeccak256": "cadf199e0b4e67a48d4b0ff7a2058396af711f703a1711c143e0d06bf418891a",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "27f13906ec6b320e571ca376b2f30fc6269f756020ca291a8e5e431cf813a1bc",
    "runtimeSHA256": "f9d5181ff65c2de443e0a39199093c234bae31893ce2cc715bebd1dbc2923147",
    "runtimeKeccak256": "0199fad071f02499a1704789ff6c81b8e1d755bf45b7fe122f7071145dca47b0",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "c04be0e420275b28674f05f2c3eba9e829bb633e86a1232ef581e78a26e665d7",
    "artifacts/coordinator/MCEntryCoordinator.sol": "9ae1bb8bf06e2781b7855fd687d2a4403e79f1f0bf3a809c8084cf31eb1d5de3",
    "canonical-driver.go.txt": "03c477383dd0370574305a1b2ec8f4da564b0615174f59c02d97306ad195ad32",
    "checkpoint_diagnostic.py": "b32a34ea08fba261f2e640fb915cfc78b4be6f19f37675c70b1b810b3f8a260b",
    "checkpoint_frames.py": "b32a34ea08fba261f2e640fb915cfc78b4be6f19f37675c70b1b810b3f8a260b",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "9e5ac2102b0af06f7b34af7ebcb877a071a35fe890d5b9b664021bf6d510d612",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "557b5ad003cad8c0935c8fa63c6da79d363c97c8ac2c1123b3ddf194bcb281f3",
    "tools/generate_focused_fixtures.py": "19b5c956d3eb28a01d98bf0e700cf4a292911aed0c2036c1366f992c5a578c95",
    "tools/build.py": "42fdf9534987a9ecc3c4702da79b9f795eac7ffd81c9d62aa0ae0fad2176e18d",
    "tools/gate.py": "b38268652d65032876c275184327333b8b22b6b413a50a654dcf6d1b3d738edb",
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
    "basis": "462bcc352",
    "parentEvidence": "parent-462bcc352/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [54, 352504],
    "diagnosticClassBound": 148,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount54-byte352504",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 53;", "MAX_RAW_CLASSES = 54;")
engine = exact(engine, "MAX_RAW_BYTES = 350161;", "MAX_RAW_BYTES = 352504;")
engine = exact(engine, "uint32(53), uint32(350161)", "uint32(54), uint32(352504)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[53]", "[54]", 4)
coord = exact(coord, "n > 53", "n > 54")
coord = exact(coord, "350161", "352504", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 53", "len(m.Decoders) > 54")
source = exact(source, "len(parts) > 53", "len(parts) > 54")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=147", "classes<=148")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "java-diff-mc-classcount53-byte350161-retained-fixtures-", "java-diff-mc-classcount54-byte352504-retained-fixtures-")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55)")
retained = exact(retained, 'count_fixture("count-53-350161", 53, 350161)', 'count_fixture("count-54-352504", 54, 352504)')
retained = exact(retained, 'count_fixture("count-53-350162", 53, 350162)', 'count_fixture("count-54-352505", 54, 352505)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "java-diff-mc-classcount53-byte350161-focused-fixtures-", "java-diff-mc-classcount54-byte352504-focused-fixtures-")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw53/byte350161", "raw54/byte352504")
built = exact(built, "classcount53-byte350161", "classcount54-byte352504")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "java-diff-mc-classcount53-byte350161-gate-", "java-diff-mc-classcount54-byte352504-gate-")
    value = exact(value, "java-diff-mc-classcount53-byte350161-build-", "java-diff-mc-classcount54-byte352504-build-")
    value = exact(value, "java-diff-mc-classcount53-byte350161-retained-fixtures-", "java-diff-mc-classcount54-byte352504-retained-fixtures-")
    value = exact(value, "java-diff-mc-classcount53-byte350161-focused-fixtures-", "java-diff-mc-classcount54-byte352504-focused-fixtures-")
    value = exact(value, "[53, 350161]", "[54, 352504]")
    value = exact(value, 'diagnosticClassBound"] == 147', 'diagnosticClassBound"] == 148')
    value = exact(value, 'head["totalClassBytes"] <= 350161', 'head["totalClassBytes"] <= 352504', 2)
    start = value.index("# Exact raw53 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    changes = (
        ("Exact raw53", "Exact raw54", 1), ("Raw54", "Raw55", 1),
        ('q_equivalent("raw53", "count-53")', 'q_equivalent("raw54", "count-54")', 1),
        ("world-raw54-driver", "world-raw55-driver", 1), ('"raw54-driver"', '"raw55-driver"', 2),
        ('"count-54.zip"', '"count-55.zip"', 3), ('"count-54", expect=2', '"count-55", expect=2', 1),
        ('], "count-54")', '], "count-55")', 2), ('"raw54-coordinator-driver"', '"raw55-coordinator-driver"', 1),
        ("len(m.Decoders) > 53", "len(m.Decoders) > 54", 2), ("len(parts) > 53", "len(parts) > 54", 2),
        ('len(m.Decoders) > 54", "len(m.Decoders) > 54', 'len(m.Decoders) > 54", "len(m.Decoders) > 55', 1),
        ('len(parts) > 54", "len(parts) > 54', 'len(parts) > 54", "len(parts) > 55', 1),
        ("world-raw54-coordinator", "world-raw55-coordinator", 1), ('"raw54-coordinator"', '"raw55-coordinator"', 2),
        ("raw54-engine-coordinator", "raw55-engine-coordinator", 2),
        ('text.count("[53]") == 4 and text.count("n > 53") == 1', 'text.count("[54]") == 4 and text.count("n > 54") == 1', 1),
        ('text.replace("[53]", "[54]").replace("n > 53", "n > 54")', 'text.replace("[54]", "[55]").replace("n > 54", "n > 55")', 1),
        ('"raw54-engine-driver"', '"raw55-engine-driver"', 1), ("world-raw54-engine", "world-raw55-engine", 1),
        ('"raw54-engine"', '"raw55-engine"', 2), ('["1", "54"]', '["1", "55"]', 1),
        ('("count-53-350161", 350161), ("count-53-350162", 350162)', '("count-54-352504", 352504), ("count-54-352505", 352505)', 1),
        ('spec["bindingCount"] == 53', 'spec["bindingCount"] == 54', 1), ("Exactly 350161", "Exactly 352504", 1),
        ("350162 is rejected", "352505 is rejected", 1), ("world-byte-350161", "world-byte-352504", 1),
        ('"byte-350161"', '"byte-352504"', 2), ('"count-53-350161.zip"', '"count-54-352504.zip"', 1),
        ('"count-53-350161"', '"count-54-352504"', 1), ("world-byte-350162", "world-byte-352505", 1),
        ('"byte-350162"', '"byte-352505"', 2), ('"count-53-350162.zip"', '"count-54-352505.zip"', 1),
        ('"count-53-350162"', '"count-54-352505"', 1), ("== 350161", "== 352504", 1),
    )
    for old, new, count in changes:
        block = exact(block, old, new, count)
    value = value[:start] + block + value[end:]
    value = exact(value, '"profile": "MC-RAW53-BYTE350161-P1"', '"profile": "MC-RAW54-BYTE352504-P1"')
    old = "Only raw capacity constants advance from raw52/329162/diagnostic146 to raw53/350161/diagnostic147. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw53 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine qe replay remains deferred."
    new = "Only raw capacity constants advance from raw53/350161/diagnostic147 to raw54/352504/diagnostic148. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw54 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fh replay remains deferred."
    value = exact(value, old, new)
    return value

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
