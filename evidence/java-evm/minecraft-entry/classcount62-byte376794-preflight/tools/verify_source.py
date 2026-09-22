#!/usr/bin/env python3
"""Verify raw62/376794 is an exact capacity-only delta from parent-cc2b7556b."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-cc2b7556b"
prior = stage.parent / "classcount61-byte375416-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "4a9fe83ddbd99091f51c7b10954f194248c52b5b05e19452bdd579a47eac803b",
    "runtimeSHA256": "ac6e9b45b42a092b3a0966cc2f7dbf65e23f1b25146948795541985aaf3dc3bd",
    "runtimeKeccak256": "9a50554eeb732f3f8ad367af225648916cd0f4a4387d7d9f1c6e1256ded43410"
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "74f963295b098cd366ac3a543cabf392bc87a71f3b8b72ae54cd3c1f81c5e86e",
    "runtimeSHA256": "5d33873f066eb0193eb9ebf3c2d8f3301a467a9120854985825f043598d81412",
    "runtimeKeccak256": "21284882f342fef344a739baaf3ae3919785f42118abb161c4e43c8a1fddf281"
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "a401eca4dedca435882c88ff5a3f55a4144f7a041e7b34da23bbbbc626c93b4b",
    "artifacts/coordinator/MCEntryCoordinator.sol": "d3a20e39130197d7bf40dc0d0771b8d1026018023d3171d0d33ba2181c83bcd0",
    "canonical-driver.go.txt": "2eebdd4ba21e87291770aa84f83ce6a232c96754ad9f9270956fcd71b0214aa9",
    "checkpoint_diagnostic.py": "d56eb6df401ca91051c23414a345a4eb1f5fe6b16ecd71a70ec4f89f0c20c6ed",
    "checkpoint_frames.py": "d56eb6df401ca91051c23414a345a4eb1f5fe6b16ecd71a70ec4f89f0c20c6ed",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "e6386aeda43f718a61335a43278ba96e738e26c92cd30da6147b545285304bd8"
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "74462fc4d0fb24c966553b43a31a53e5a9d26e6fb4072d883608d09bf30c1cca",
    "tools/generate_focused_fixtures.py": "2d163027c5bcab1cbc49ec0d0c117d2b7faedae6cebe6c0951aed955c01c4d01",
    "tools/build.py": "1711ae21c889c2aee373e1faeb60ef568aaf82d04306514bb25bb78f04748ea8",
    "tools/gate.py": "69c025f698b8b743746bae85dc594da6bb85c85320afb95e646f7427ead230f7"
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
    "basis": "cc2b7556b",
    "parentEvidence": "parent-cc2b7556b/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [62, 376794],
    "diagnosticClassBound": 156,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount62-byte376794",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 61;", "MAX_RAW_CLASSES = 62;")
engine = exact(engine, "MAX_RAW_BYTES = 375416;", "MAX_RAW_BYTES = 376794;")
engine = exact(engine, "uint32(61), uint32(375416)", "uint32(62), uint32(376794)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[61]", "[62]", 4)
coord = exact(coord, "n > 61", "n > 62")
coord = exact(coord, "375416", "376794", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 61", "len(m.Decoders) > 62")
source = exact(source, "len(parts) > 61", "len(parts) > 62")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=155", "classes<=156")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount61-byte375416", "classcount62-byte376794")
retained = exact(retained, "55, 56, 57, 58, 59, 60, 61, 62)", "55, 56, 57, 58, 59, 60, 61, 62, 63)")
retained = exact(retained, 'count_fixture("count-61-375416", 61, 375416)', 'count_fixture("count-62-376794", 62, 376794)')
retained = exact(retained, 'count_fixture("count-61-375417", 61, 375417)', 'count_fixture("count-62-376795", 62, 376795)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount61-byte375416", "classcount62-byte376794")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw61/byte375416", "raw62/byte376794")
built = exact(built, "classcount61-byte375416", "classcount62-byte376794")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "classcount61-byte375416", "classcount62-byte376794", 4)
    value = exact(value, "[61, 375416]", "[62, 376794]")
    value = exact(value, 'diagnosticClassBound"] == 155', 'diagnosticClassBound"] == 156')
    value = exact(value, "<= 375416", "<= 376794", 2)
    value = exact(value, "MC-RAW61-BYTE375416-P1", "MC-RAW62-BYTE376794-P1")
    value = exact(value, "raw60/373340/diagnostic154 to raw61/375416/diagnostic155", "raw61/375416/diagnostic155 to raw62/376794/diagnostic156")
    value = exact(value, "exact raw61 generated focus", "exact raw62 generated focus")
    value = exact(value, "genuine CollectPreconditions replay", "genuine Hashing replay")
    start = value.index("# Exact raw61 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw61", "RAWFOCUS"), ("count-61", "COUNTFOCUS"), ("raw62", "RAWREJECT"), ("count-62", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw62"), ("COUNTFOCUS", "count-62"), ("RAWREJECT", "raw63"), ("COUNTREJECT", "count-63"), ("375416", "376794"), ("375417", "376795")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 61") == 1 and source.count("len(parts) > 61") == 1', 'assert source.count("len(m.Decoders) > 62") == 1 and source.count("len(parts) > 62") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 61", "len(m.Decoders) > 62")', 'source.replace("len(m.Decoders) > 62", "len(m.Decoders) > 63")')
    block = exact(block, '.replace("len(parts) > 61", "len(parts) > 62")', '.replace("len(parts) > 62", "len(parts) > 63")')
    block = exact(block, 'assert text.count("[61]") == 4 and text.count("n > 61") == 1', 'assert text.count("[62]") == 4 and text.count("n > 62") == 1')
    block = exact(block, 'text.replace("[61]", "[62]").replace("n > 61", "n > 62")', 'text.replace("[62]", "[63]").replace("n > 62", "n > 63")')
    block = exact(block, '["1", "62"]', '["1", "63"]')
    block = exact(block, 'spec["bindingCount"] == 61', 'spec["bindingCount"] == 62')
    assert all(word not in block for word in ("raw61", "count-61", "375416", "375417"))
    return value[:start] + block + value[end:]

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
