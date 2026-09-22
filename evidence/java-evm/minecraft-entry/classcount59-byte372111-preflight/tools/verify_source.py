#!/usr/bin/env python3
"""Verify raw59/372111 is an exact capacity-only delta from parent-949992f6c."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-949992f6c"
prior = stage.parent / "classcount58-byte370032-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "ab53cd46370541989ffe00f03c48b5696cb5ff8cf85480e5302969b8bfd914d7",
    "runtimeSHA256": "0d7f5c4277eaab6724fa341e8b45dc28328d4deffec23cf4cf5890961483a2c5",
    "runtimeKeccak256": "17ebbc185c38e4e6734796841a9fb0fb86adec451f0aeee750a2098d1e5ced0b",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "e7ed7045b3b9c8e8b9449bd36ce0d31d2d2393d4d86aa73e477de4a5ac92e130",
    "runtimeSHA256": "fa3111f18acf3b7af48c979dece4bf4975969a4f61dc9c237e118a3db494aeef",
    "runtimeKeccak256": "db5fe7b7be81e4e9bf6bd1a5b2d914aa30339932e80db1fdea436b1c23470b11",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "3f142caf94408be163e17ebe8755d22aabe97e01fa6f7b056665828ed8f22af5",
    "artifacts/coordinator/MCEntryCoordinator.sol": "cae48b4ba396deeae9aef0a45010befd8482111a73aaa898c1e3d22f0f4bc952",
    "canonical-driver.go.txt": "6ad7b851fbb445b59fd2d1bdc1da490557dd32e0762835ba2961ef6bac0dfe95",
    "checkpoint_diagnostic.py": "9aa47cd526d8594a838e5878d7f44a7c2270132312f791797ee3bfe6d62c38de",
    "checkpoint_frames.py": "9aa47cd526d8594a838e5878d7f44a7c2270132312f791797ee3bfe6d62c38de",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "2fb6c8bd24228636dee6ca7724154aa66b3224c4d46f4c853887ba7242fb0468",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "ebccbe129c3fd18c6b9e5c952998054f7f2fceff6e5d55073d3fc77703609e41",
    "tools/generate_focused_fixtures.py": "f9ce0705fb490a9e92051637070171ee2bae72b159833e33f86a90dd4e8a70ef",
    "tools/build.py": "5690f3f06843198ee8eabbb3ba8389df60113b03e2608c23145ddb1d8a7b6b97",
    "tools/gate.py": "c87f03a98bcb1a1a5e378bb7d98bf45413a8a46034c5fe9de709f79e0e29adfc",
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
    "basis": "949992f6c",
    "parentEvidence": "parent-949992f6c/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [59, 372111],
    "diagnosticClassBound": 153,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount59-byte372111",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 58;", "MAX_RAW_CLASSES = 59;")
engine = exact(engine, "MAX_RAW_BYTES = 370032;", "MAX_RAW_BYTES = 372111;")
engine = exact(engine, "uint32(58), uint32(370032)", "uint32(59), uint32(372111)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[58]", "[59]", 4)
coord = exact(coord, "n > 58", "n > 59")
coord = exact(coord, "370032", "372111", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 58", "len(m.Decoders) > 59")
source = exact(source, "len(parts) > 58", "len(parts) > 59")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=152", "classes<=153")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount58-byte370032", "classcount59-byte372111")
retained = exact(retained, "55, 56, 57, 58, 59)", "55, 56, 57, 58, 59, 60)")
retained = exact(retained, 'count_fixture("count-58-370032", 58, 370032)', 'count_fixture("count-59-372111", 59, 372111)')
retained = exact(retained, 'count_fixture("count-58-370033", 58, 370033)', 'count_fixture("count-59-372112", 59, 372112)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount58-byte370032", "classcount59-byte372111")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw58/byte370032", "raw59/byte372111")
built = exact(built, "classcount58-byte370032", "classcount59-byte372111")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "classcount58-byte370032", "classcount59-byte372111", 4)
    value = exact(value, "[58, 370032]", "[59, 372111]")
    value = exact(value, 'diagnosticClassBound"] == 152', 'diagnosticClassBound"] == 153')
    value = exact(value, '<= 370032', '<= 372111', 2)
    value = exact(value, 'MC-RAW58-BYTE370032-P1', 'MC-RAW59-BYTE372111-P1')
    value = exact(value, 'raw57/355926/diagnostic151 to raw58/370032/diagnostic152', 'raw58/370032/diagnostic152 to raw59/372111/diagnostic153')
    value = exact(value, 'exact raw58 generated focus', 'exact raw59 generated focus')
    value = exact(value, 'genuine HashBiMap replay', 'genuine Maps$IteratorBasedAbstractMap replay')
    start = value.index("# Exact raw58 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw58", "RAWFOCUS"), ("count-58", "COUNTFOCUS"), ("raw59", "RAWREJECT"), ("count-59", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw59"), ("COUNTFOCUS", "count-59"), ("RAWREJECT", "raw60"), ("COUNTREJECT", "count-60"), ("370032", "372111"), ("370033", "372112")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 58") == 1 and source.count("len(parts) > 58") == 1', 'assert source.count("len(m.Decoders) > 59") == 1 and source.count("len(parts) > 59") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 58", "len(m.Decoders) > 59")', 'source.replace("len(m.Decoders) > 59", "len(m.Decoders) > 60")')
    block = exact(block, '.replace("len(parts) > 58", "len(parts) > 59")', '.replace("len(parts) > 59", "len(parts) > 60")')
    block = exact(block, 'assert text.count("[58]") == 4 and text.count("n > 58") == 1', 'assert text.count("[59]") == 4 and text.count("n > 59") == 1')
    block = exact(block, 'text.replace("[58]", "[59]").replace("n > 58", "n > 59")', 'text.replace("[59]", "[60]").replace("n > 59", "n > 60")')
    block = exact(block, '["1", "59"]', '["1", "60"]')
    block = exact(block, 'spec["bindingCount"] == 58', 'spec["bindingCount"] == 59')
    block = exact(block, 'Raw59 is independently refused', 'Raw60 is independently refused')
    assert all(word not in block for word in ("raw58", "count-58", "370032", "370033"))
    return value[:start] + block + value[end:]

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
