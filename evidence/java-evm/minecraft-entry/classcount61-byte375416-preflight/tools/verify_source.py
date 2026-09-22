#!/usr/bin/env python3
"""Verify raw61/375416 is an exact capacity-only delta from parent-8875b58aa."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-8875b58aa"
prior = stage.parent / "classcount60-byte373340-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "4bf2cfc768bafca587b582873084391148aae2a0b2dd45b224a48002b38dc464",
    "runtimeSHA256": "bec5e09700e2fa8f86a7091bbcc95f7e7394fd2d7aa404b5b80b8ddb40685373",
    "runtimeKeccak256": "02116d0a7c46e60b1b8b8d0e730aff38a0b96692350334e12f2505e4b5d71c54"
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "c3ac5c1cdde4fa6958df03647ef19f137e7eba245f786a6e6d89a9c7a817aeb5",
    "runtimeSHA256": "4ac843a5ced80acc133fecbd182aa82414259ebc6c4b5417221bf2b4c6f243aa",
    "runtimeKeccak256": "97919d9488e863a01ee3226991ee41ded3d1f841d4eac26db7cbcee553dbb10b"
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "6910112ea201ac97c7b21d750405b4a62c8190a71577ce62ca19c94886a98497",
    "artifacts/coordinator/MCEntryCoordinator.sol": "6b60b84d12b1fffe274b73a4cce6bba6c5827fda53baf1a59af21bc910a8d7d5",
    "canonical-driver.go.txt": "f628d1f074b88e431d0bdb7202b707a0f843a38dee2b7f38ed1ac7935c679486",
    "checkpoint_diagnostic.py": "0528700e3e3fbc658914019e5b8bd6576a8609da40ab7143bb53ca9456d3d904",
    "checkpoint_frames.py": "0528700e3e3fbc658914019e5b8bd6576a8609da40ab7143bb53ca9456d3d904",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "14153f252922822a4b93f7dbc265a212d6eac7eedb4207fe9e96ecf0ed07ff37"
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "a5a9a6eab3161b90d0fd5efc1995d139e58bc40ff182de98591346c45324095c",
    "tools/generate_focused_fixtures.py": "1603af234c673305a00bca0189b9e2b9067656724cd9765bcf0fb7cdeacfc876",
    "tools/build.py": "909a799e5685feb07885dc534c1a1fc9aef19ecd5c9c77cfc1de17fe3f73d1ea",
    "tools/gate.py": "d1e561762df02b6d64bbd5a4958de3b032d7bb7a288290cffce5ac33858ed4dc"
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
    "basis": "8875b58aa",
    "parentEvidence": "parent-8875b58aa/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [61, 375416],
    "diagnosticClassBound": 155,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount61-byte375416",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 60;", "MAX_RAW_CLASSES = 61;")
engine = exact(engine, "MAX_RAW_BYTES = 373340;", "MAX_RAW_BYTES = 375416;")
engine = exact(engine, "uint32(60), uint32(373340)", "uint32(61), uint32(375416)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[60]", "[61]", 4)
coord = exact(coord, "n > 60", "n > 61")
coord = exact(coord, "373340", "375416", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 60", "len(m.Decoders) > 61")
source = exact(source, "len(parts) > 60", "len(parts) > 61")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=154", "classes<=155")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount60-byte373340", "classcount61-byte375416")
retained = exact(retained, "55, 56, 57, 58, 59, 60, 61)", "55, 56, 57, 58, 59, 60, 61, 62)")
retained = exact(retained, 'count_fixture("count-60-373340", 60, 373340)', 'count_fixture("count-61-375416", 61, 375416)')
retained = exact(retained, 'count_fixture("count-60-373341", 60, 373341)', 'count_fixture("count-61-375417", 61, 375417)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount60-byte373340", "classcount61-byte375416")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw60/byte373340", "raw61/byte375416")
built = exact(built, "classcount60-byte373340", "classcount61-byte375416")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "classcount60-byte373340", "classcount61-byte375416", 4)
    value = exact(value, "[60, 373340]", "[61, 375416]")
    value = exact(value, 'diagnosticClassBound"] == 154', 'diagnosticClassBound"] == 155')
    value = exact(value, "<= 373340", "<= 375416", 2)
    value = exact(value, "MC-RAW60-BYTE373340-P1", "MC-RAW61-BYTE375416-P1")
    value = exact(value, "raw59/372111/diagnostic153 to raw60/373340/diagnostic154", "raw60/373340/diagnostic154 to raw61/375416/diagnostic155")
    value = exact(value, "exact raw60 generated focus", "exact raw61 generated focus")
    value = exact(value, "genuine BiMap replay", "genuine CollectPreconditions replay")
    start = value.index("# Exact raw60 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw60", "RAWFOCUS"), ("count-60", "COUNTFOCUS"), ("raw61", "RAWREJECT"), ("count-61", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw61"), ("COUNTFOCUS", "count-61"), ("RAWREJECT", "raw62"), ("COUNTREJECT", "count-62"), ("373340", "375416"), ("373341", "375417")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 60") == 1 and source.count("len(parts) > 60") == 1', 'assert source.count("len(m.Decoders) > 61") == 1 and source.count("len(parts) > 61") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 60", "len(m.Decoders) > 61")', 'source.replace("len(m.Decoders) > 61", "len(m.Decoders) > 62")')
    block = exact(block, '.replace("len(parts) > 60", "len(parts) > 61")', '.replace("len(parts) > 61", "len(parts) > 62")')
    block = exact(block, 'assert text.count("[60]") == 4 and text.count("n > 60") == 1', 'assert text.count("[61]") == 4 and text.count("n > 61") == 1')
    block = exact(block, 'text.replace("[60]", "[61]").replace("n > 60", "n > 61")', 'text.replace("[61]", "[62]").replace("n > 61", "n > 62")')
    block = exact(block, '["1", "61"]', '["1", "62"]')
    block = exact(block, 'spec["bindingCount"] == 60', 'spec["bindingCount"] == 61')
    block = exact(block, "Raw61 is independently refused", "Raw62 is independently refused")
    assert all(word not in block for word in ("raw60", "count-60", "373340", "373341"))
    return value[:start] + block + value[end:]

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
