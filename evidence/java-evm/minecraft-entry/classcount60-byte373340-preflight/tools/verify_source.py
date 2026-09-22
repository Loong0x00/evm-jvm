#!/usr/bin/env python3
"""Verify raw60/373340 is an exact capacity-only delta from parent-2c73cca83."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-2c73cca83"
prior = stage.parent / "classcount59-byte372111-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "5adf0ac4ff4eb3f49989eba2937c2a79ebdb58d4f922462ba0a680ca2a7300a1",
    "runtimeSHA256": "9825682a16e19ee322d629b2c117b30e10551a39db032b370b6797e4bd9a6695",
    "runtimeKeccak256": "2d05b7242f5abc06a2d98d6018defb5c5c950c5b595583275d42e7d19e11f6cc",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "54f7723e3dd1a740fbbd0bc2b4cabf819eddd6ccb748482a901b3fde070a599a",
    "runtimeSHA256": "b3302660de4d96c9f195e73e73105ad60bdcac8b47deb0b832da198d912a70f8",
    "runtimeKeccak256": "adaba408a62bf86844ee9f47877c2ead683f006adc06938c41f48b2ac20c47af",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "60fa77c37b1418b7aa47874f418c31bd9386bc81bf20054d7cecfcfbd4f418cb",
    "artifacts/coordinator/MCEntryCoordinator.sol": "04029a6fd256a1908fb4471d8487b75590a7f33d197c38640a580e250786ea95",
    "canonical-driver.go.txt": "b686c952ee7a9afcca91d96cbd9c0e34a3a4b3855ade4172e0a1cb9fa2c031a8",
    "checkpoint_diagnostic.py": "3c04213e79913b42847ea8f0f7fb6261514fc9a509b1d227f08abd7397d7c588",
    "checkpoint_frames.py": "3c04213e79913b42847ea8f0f7fb6261514fc9a509b1d227f08abd7397d7c588",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "3ee8153170aae45e496267f6f8b6a1f02a17e94dbea343bae915a756c6e83d99",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "2732a277268524fcf3264d85a71bfa460fa82318ccc9ac62781b5244b0c07f6b",
    "tools/generate_focused_fixtures.py": "afac357d86588697d1eb18ef86e73cbcb7bbdd34cd25840473b68326afcab0e1",
    "tools/build.py": "29ea532001ef49d16e4cd8ff7bcf5697cb4635a39c04f45f2f1b7b22f1274516",
    "tools/gate.py": "7844081c4aff074364e45312f4dd12c0fe5ad844ce2db7f13d2fa2b917e7fb08",
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
    "basis": "2c73cca83",
    "parentEvidence": "parent-2c73cca83/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [60, 373340],
    "diagnosticClassBound": 154,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount60-byte373340",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 59;", "MAX_RAW_CLASSES = 60;")
engine = exact(engine, "MAX_RAW_BYTES = 372111;", "MAX_RAW_BYTES = 373340;")
engine = exact(engine, "uint32(59), uint32(372111)", "uint32(60), uint32(373340)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[59]", "[60]", 4)
coord = exact(coord, "n > 59", "n > 60")
coord = exact(coord, "372111", "373340", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 59", "len(m.Decoders) > 60")
source = exact(source, "len(parts) > 59", "len(parts) > 60")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=153", "classes<=154")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount59-byte372111", "classcount60-byte373340")
retained = exact(retained, "55, 56, 57, 58, 59, 60)", "55, 56, 57, 58, 59, 60, 61)")
retained = exact(retained, 'count_fixture("count-59-372111", 59, 372111)', 'count_fixture("count-60-373340", 60, 373340)')
retained = exact(retained, 'count_fixture("count-59-372112", 59, 372112)', 'count_fixture("count-60-373341", 60, 373341)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount59-byte372111", "classcount60-byte373340")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw59/byte372111", "raw60/byte373340")
built = exact(built, "classcount59-byte372111", "classcount60-byte373340")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "classcount59-byte372111", "classcount60-byte373340", 4)
    value = exact(value, "[59, 372111]", "[60, 373340]")
    value = exact(value, 'diagnosticClassBound"] == 153', 'diagnosticClassBound"] == 154')
    value = exact(value, "<= 372111", "<= 373340", 2)
    value = exact(value, "MC-RAW59-BYTE372111-P1", "MC-RAW60-BYTE373340-P1")
    value = exact(value, "raw58/370032/diagnostic152 to raw59/372111/diagnostic153", "raw59/372111/diagnostic153 to raw60/373340/diagnostic154")
    value = exact(value, "exact raw59 generated focus", "exact raw60 generated focus")
    value = exact(value, "genuine Maps$IteratorBasedAbstractMap replay", "genuine BiMap replay")
    start = value.index("# Exact raw59 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw59", "RAWFOCUS"), ("count-59", "COUNTFOCUS"), ("raw60", "RAWREJECT"), ("count-60", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw60"), ("COUNTFOCUS", "count-60"), ("RAWREJECT", "raw61"), ("COUNTREJECT", "count-61"), ("372111", "373340"), ("372112", "373341")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 59") == 1 and source.count("len(parts) > 59") == 1', 'assert source.count("len(m.Decoders) > 60") == 1 and source.count("len(parts) > 60") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 59", "len(m.Decoders) > 60")', 'source.replace("len(m.Decoders) > 60", "len(m.Decoders) > 61")')
    block = exact(block, '.replace("len(parts) > 59", "len(parts) > 60")', '.replace("len(parts) > 60", "len(parts) > 61")')
    block = exact(block, 'assert text.count("[59]") == 4 and text.count("n > 59") == 1', 'assert text.count("[60]") == 4 and text.count("n > 60") == 1')
    block = exact(block, 'text.replace("[59]", "[60]").replace("n > 59", "n > 60")', 'text.replace("[60]", "[61]").replace("n > 60", "n > 61")')
    block = exact(block, '["1", "60"]', '["1", "61"]')
    block = exact(block, 'spec["bindingCount"] == 59', 'spec["bindingCount"] == 60')
    block = exact(block, "Raw60 is independently refused", "Raw61 is independently refused")
    assert all(word not in block for word in ("raw59", "count-59", "372111", "372112"))
    return value[:start] + block + value[end:]

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
