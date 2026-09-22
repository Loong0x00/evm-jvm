#!/usr/bin/env python3
"""Verify raw58/370032 is an exact capacity-only delta from parent-01d17b7cf."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-01d17b7cf"
prior = stage.parent / "classcount57-byte355926-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "aad66382f42b8e97789b685841778667c47625271dea2631f61ebf96bedacc93",
    "runtimeSHA256": "db76779ac4a6becf3dfef5c11e0c781e0ba86e2a91c8a0292f886bdec3c24d75",
    "runtimeKeccak256": "94b8a54ec6c67df7a6965d02adb0374cb8a8625b6367ddf6da72b0bdc1dc678c"
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "e00af1b063a02745c671caa4212abb3796276f52339ba3a6a784c9b255a91682",
    "runtimeSHA256": "4f93403cf46e05909debaec2f7effaf2b06b425bef9d2d3d8049a478c87c6c5d",
    "runtimeKeccak256": "229ad7ed5ba5f6dd656cae920f7ec2bb6ca04dfb6a94a41a664303f0f72aebbb"
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "faf3509a661ca557c0b2782cc9b771bafd10211c2e7e5136f80dcca0f05858b9",
    "artifacts/coordinator/MCEntryCoordinator.sol": "6a186fee22e83deccff3c7fecae76069c04a2c0c20ea35a032aa47f41e39f63d",
    "canonical-driver.go.txt": "0c1e40491373f4b8607c2cca1ae91bcb445eacee027f6a0c9c7b7ca10b8c858f",
    "checkpoint_diagnostic.py": "e5c67521fddbe6ff599b44485e8b27969fffbdb2a2ee7f0b24856c8285589f3c",
    "checkpoint_frames.py": "e5c67521fddbe6ff599b44485e8b27969fffbdb2a2ee7f0b24856c8285589f3c",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "126dc25af28c9df3cf922994779ac0bb5382ff15423fd040e821973215926d45"
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "4db77138352b7943378002432ba77e62bb421624473530912c8cc7f8648dc490",
    "tools/generate_focused_fixtures.py": "185be1de70ad593d2e5a63fe24737583da260f0ebe28f6b303ca300898b5dcd7",
    "tools/build.py": "4d3f2b5a0cd50e1fbb75da2cfdcd12e13ef4bbccba9a1cbad7cbc6a2719cebec",
    "tools/gate.py": "dfa39d8e701cdd226d61825b26449abbefeb54a0b0aeeb721bb0d266b73372ee"
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
    "basis": "01d17b7cf",
    "parentEvidence": "parent-01d17b7cf/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [58, 370032],
    "diagnosticClassBound": 152,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount58-byte370032",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 57;", "MAX_RAW_CLASSES = 58;")
engine = exact(engine, "MAX_RAW_BYTES = 355926;", "MAX_RAW_BYTES = 370032;")
engine = exact(engine, "uint32(57), uint32(355926)", "uint32(58), uint32(370032)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[57]", "[58]", 4)
coord = exact(coord, "n > 57", "n > 58")
coord = exact(coord, "355926", "370032", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 57", "len(m.Decoders) > 58")
source = exact(source, "len(parts) > 57", "len(parts) > 58")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=151", "classes<=152")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount57-byte355926", "classcount58-byte370032")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59)")
retained = exact(retained, 'count_fixture("count-57-355926", 57, 355926)', 'count_fixture("count-58-370032", 58, 370032)')
retained = exact(retained, 'count_fixture("count-57-355927", 57, 355927)', 'count_fixture("count-58-370033", 58, 370033)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount57-byte355926", "classcount58-byte370032")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw57/byte355926", "raw58/byte370032")
built = exact(built, "classcount57-byte355926", "classcount58-byte370032")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "java-diff-mc-classcount57-byte355926-gate-", "java-diff-mc-classcount58-byte370032-gate-")
    value = exact(value, "java-diff-mc-classcount57-byte355926-build-", "java-diff-mc-classcount58-byte370032-build-")
    value = exact(value, "java-diff-mc-classcount57-byte355926-retained-fixtures-", "java-diff-mc-classcount58-byte370032-retained-fixtures-")
    value = exact(value, "java-diff-mc-classcount57-byte355926-focused-fixtures-", "java-diff-mc-classcount58-byte370032-focused-fixtures-")
    value = exact(value, "[57, 355926]", "[58, 370032]")
    value = exact(value, 'diagnosticClassBound"] == 151', 'diagnosticClassBound"] == 152')
    value = exact(value, 'head["totalClassBytes"] <= 355926', 'head["totalClassBytes"] <= 370032', 2)
    start = value.index("# Exact raw57 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw57", "RAWFOCUS"), ("count-57", "COUNTFOCUS"), ("raw58", "RAWREJECT"), ("count-58", "COUNTREJECT")): block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw58"), ("COUNTFOCUS", "count-58"), ("RAWREJECT", "raw59"), ("COUNTREJECT", "count-59"), ("355926", "370032"), ("355927", "370033")): block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 57") == 1 and source.count("len(parts) > 57") == 1', 'assert source.count("len(m.Decoders) > 58") == 1 and source.count("len(parts) > 58") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 57", "len(m.Decoders) > 58")', 'source.replace("len(m.Decoders) > 58", "len(m.Decoders) > 59")')
    block = exact(block, '.replace("len(parts) > 57", "len(parts) > 58")', '.replace("len(parts) > 58", "len(parts) > 59")')
    block = exact(block, 'assert text.count("[57]") == 4 and text.count("n > 57") == 1', 'assert text.count("[58]") == 4 and text.count("n > 58") == 1')
    block = exact(block, 'text.replace("[57]", "[58]").replace("n > 57", "n > 58")', 'text.replace("[58]", "[59]").replace("n > 58", "n > 59")')
    block = exact(block, '["1", "58"]', '["1", "59"]')
    block = exact(block, 'spec["bindingCount"] == 57', 'spec["bindingCount"] == 58')
    block = exact(block, "Raw58 is independently refused", "Raw59 is independently refused")
    assert "raw57" not in block and "count-57" not in block and "355926" not in block and "355927" not in block
    value = value[:start] + block + value[end:]
    old_capacity = '''# Exactly 370032 raw bytes is admitted by the coordinator and fully supplied
# through DI0 to the engine. The fixed LOCAL1B call reaches the inherited empty
# EVM revert after that positive work; it is not a coordinator byte-limit
# refusal or a fabricated typed Java outcome. 370033 is rejected atomically
# by the coordinator before that engine work.
world = out / "world-byte-370032"
run("byte-370032", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-58-370032.zip", "4096"], "count-58-370032")
refusal = failure(world, "start-refusal.json")
assert sum(refusal["actualDI0ReadSizes"]) == 370032 and refusal["selector"] == "0x" and words(refusal) == []
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
rows["byte-370032"] = {"coordinatorAccepted": True, "engineRefusal": refusal}
world = out / "world-byte-370033"'''
    new_capacity = '''# Exactly 370032 raw bytes is admitted by the coordinator and fully supplied
# through DI0 to the engine. The unchanged 1MiB checkpoint cap then refuses
# the oversized prepared machine at LC0StateError(1,0), before Head mutation;
# this is neither a coordinator byte-limit refusal nor a fabricated Java
# outcome. 370033 is rejected atomically by the coordinator before engine work.
world = out / "world-byte-370032"
run("byte-370032", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-58-370032.zip", "4096"], "count-58-370032")
refusal = failure(world, "start-refusal.json")
assert sum(refusal["actualDI0ReadSizes"]) == 370032
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"]
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
rows["byte-370032"] = {"coordinatorAccepted": True, "checkpointCapRefusal": refusal}
world = out / "world-byte-370033"'''
    value = exact(value, old_capacity, new_capacity)
    value = exact(value, '"profile": "MC-RAW57-BYTE355926-P1"', '"profile": "MC-RAW58-BYTE370032-P1"')
    old = "Only raw capacity constants advance from raw56/355643/diagnostic150 to raw57/355926/diagnostic151. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw57 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fm replay remains deferred."
    new = "Only raw capacity constants advance from raw57/355926/diagnostic151 to raw58/370032/diagnostic152. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw58 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine HashBiMap replay remains deferred."
    return exact(value, old, new)

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
