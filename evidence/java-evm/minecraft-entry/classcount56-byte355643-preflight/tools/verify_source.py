#!/usr/bin/env python3
"""Verify raw56/355643 is an exact capacity-only delta from parent-0da61f0b5."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-0da61f0b5"
prior = stage.parent / "classcount55-byte355563-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "a02085ccbe05ac49fee3d5c3b143404abd0bd1d3f1e41cce78d74bba4e659dd9",
    "runtimeSHA256": "3c76cb5c39670150649da861d6c11454dd15f479f003c09209b5310a10729e3c",
    "runtimeKeccak256": "2fe23993c6d89095121173bbe38e0123fffcbc219a7e5b9cbd6d03018423ca6a",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "404fb1b2ddee1a242edb0717ebd278665fd51e35ba0775746b6530c5174bbdd6",
    "runtimeSHA256": "a4d43d6f19d253ba3de17c5bc83257b2f83a4ef0aaa3d9a814ffeacefbec9195",
    "runtimeKeccak256": "483c65759756160c73e0c8730487423e76c4d996a62148ece7afa2a832c4b75f",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "b61f7bd36c4def245138e376f1e7846c76628e2697ef8d991fb14ff24ca01d34",
    "artifacts/coordinator/MCEntryCoordinator.sol": "7c54cc732be371f7401727961e301e1c6a54b1165e34713afcbdf880aaf355d1",
    "canonical-driver.go.txt": "13a8e7a11c31a2f62f2b31d7b1c8758b41b91d2376ffcf29de0fe1d2c595c170",
    "checkpoint_diagnostic.py": "08fde630e5ec2e9ad747354126bff42a752954e482f556a7decfd1096d0fde5c",
    "checkpoint_frames.py": "08fde630e5ec2e9ad747354126bff42a752954e482f556a7decfd1096d0fde5c",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "35be1358e0e4e18763f81fe268e2bfa5f4b1cf97c67b39196b5ea082b78025b6",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "c2b3577323fc1c07d0735428a0073be9edb0635c81df34857df60fec9d344300",
    "tools/generate_focused_fixtures.py": "887716242edede7e41dd0ec3a388aeea9e227f90986c62861b61eb7d5e6fb6fb",
    "tools/build.py": "936c7ada0347d40a9e2b2b962274e1a3af8e927c6f651d776bc68cc02eb6b049",
    "tools/gate.py": "2ff08a77eed4e3a167f96b20b2fa169c4efcba318be245e2934116db6b78c57f",
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
    "basis": "0da61f0b5",
    "parentEvidence": "parent-0da61f0b5/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [56, 355643],
    "diagnosticClassBound": 150,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount56-byte355643",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 55;", "MAX_RAW_CLASSES = 56;")
engine = exact(engine, "MAX_RAW_BYTES = 355563;", "MAX_RAW_BYTES = 355643;")
engine = exact(engine, "uint32(55), uint32(355563)", "uint32(56), uint32(355643)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[55]", "[56]", 4)
coord = exact(coord, "n > 55", "n > 56")
coord = exact(coord, "355563", "355643", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 55", "len(m.Decoders) > 56")
source = exact(source, "len(parts) > 55", "len(parts) > 56")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=149", "classes<=150")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount55-byte355563", "classcount56-byte355643")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57)")
retained = exact(retained, 'count_fixture("count-55-355563", 55, 355563)', 'count_fixture("count-56-355643", 56, 355643)')
retained = exact(retained, 'count_fixture("count-55-355564", 55, 355564)', 'count_fixture("count-56-355644", 56, 355644)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount55-byte355563", "classcount56-byte355643")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw55/byte355563", "raw56/byte355643")
built = exact(built, "classcount55-byte355563", "classcount56-byte355643")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "java-diff-mc-classcount55-byte355563-gate-", "java-diff-mc-classcount56-byte355643-gate-")
    value = exact(value, "java-diff-mc-classcount55-byte355563-build-", "java-diff-mc-classcount56-byte355643-build-")
    value = exact(value, "java-diff-mc-classcount55-byte355563-retained-fixtures-", "java-diff-mc-classcount56-byte355643-retained-fixtures-")
    value = exact(value, "java-diff-mc-classcount55-byte355563-focused-fixtures-", "java-diff-mc-classcount56-byte355643-focused-fixtures-")
    value = exact(value, "[55, 355563]", "[56, 355643]")
    value = exact(value, 'diagnosticClassBound"] == 149', 'diagnosticClassBound"] == 150')
    value = exact(value, 'head["totalClassBytes"] <= 355563', 'head["totalClassBytes"] <= 355643', 2)
    start = value.index("# Exact raw55 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw55", "RAWFOCUS"), ("count-55", "COUNTFOCUS"), ("raw56", "RAWREJECT"), ("count-56", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw56"), ("COUNTFOCUS", "count-56"), ("RAWREJECT", "raw57"), ("COUNTREJECT", "count-57"), ("355563", "355643"), ("355564", "355644")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 55") == 1 and source.count("len(parts) > 55") == 1', 'assert source.count("len(m.Decoders) > 56") == 1 and source.count("len(parts) > 56") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 55", "len(m.Decoders) > 56")', 'source.replace("len(m.Decoders) > 56", "len(m.Decoders) > 57")')
    block = exact(block, '.replace("len(parts) > 55", "len(parts) > 56")', '.replace("len(parts) > 56", "len(parts) > 57")')
    block = exact(block, 'assert text.count("[55]") == 4 and text.count("n > 55") == 1', 'assert text.count("[56]") == 4 and text.count("n > 56") == 1')
    block = exact(block, 'text.replace("[55]", "[56]").replace("n > 55", "n > 56")', 'text.replace("[56]", "[57]").replace("n > 56", "n > 57")')
    block = exact(block, '["1", "56"]', '["1", "57"]')
    block = exact(block, 'spec["bindingCount"] == 55', 'spec["bindingCount"] == 56')
    block = exact(block, "Raw56 is independently refused", "Raw57 is independently refused")
    assert "raw55" not in block and "count-55" not in block and "355563" not in block and "355564" not in block
    value = value[:start] + block + value[end:]
    value = exact(value, '"profile": "MC-RAW55-BYTE355563-P1"', '"profile": "MC-RAW56-BYTE355643-P1"')
    old = "Only raw capacity constants advance from raw54/352504/diagnostic148 to raw55/355563/diagnostic149. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw55 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fo replay remains deferred."
    new = "Only raw capacity constants advance from raw55/355563/diagnostic149 to raw56/355643/diagnostic150. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw56 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fc replay remains deferred."
    return exact(value, old, new)

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
