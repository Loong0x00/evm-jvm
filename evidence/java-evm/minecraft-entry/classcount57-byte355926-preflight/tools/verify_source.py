#!/usr/bin/env python3
"""Verify raw57/355926 is an exact capacity-only delta from parent-faaa5b935."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-faaa5b935"
prior = stage.parent / "classcount56-byte355643-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377312,
    "initSHA256": "4403ae29bb27a0f6fd5da9c741a9b807568909d92088ec919bd2e809affbad7a",
    "runtimeSHA256": "110a004ce71981e25062187e570e709d5e55476586fe04fd10aa486b1678d543",
    "runtimeKeccak256": "711efd85e9baa56079382933c0412f4c6cbb3e1b39ac61e94b33c0473c161e96",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "1833b5c3257d1cc2d8f025b0562e7a84fc1f047157e64d10c407c11da766672f",
    "runtimeSHA256": "4111fd064a56315a538b3beecf0a4676280f538dc27194adc13a981d3c75eebb",
    "runtimeKeccak256": "8c3bcc03cb72d1c5a60277fffbee1fe1f98b48588b9ddb3bb0bf5db023814c21",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "694aec408a91f9c07e8873035c3b0df1153615a4bbce2b16dd861e4ef59e0938",
    "artifacts/coordinator/MCEntryCoordinator.sol": "4a29dd1732b067054cf23221eaa8401d1e583e58b3e20783ed6eb2e8fe6d4d20",
    "canonical-driver.go.txt": "6411081c1654edc735ff68d00ae37eecf058aa72e358df67e70308db12ad9932",
    "checkpoint_diagnostic.py": "87495ace94ec44464b0e1dac0e3535b92b697769996c452f73c0afca810b0e09",
    "checkpoint_frames.py": "87495ace94ec44464b0e1dac0e3535b92b697769996c452f73c0afca810b0e09",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "29d63a7970ac1a833063c3b4bb522e517d18ae44ad34ab73fc82f96e1b96631d",
}
PRIOR_SHA256 = {
    "tools/generate_retained_fixtures.py": "f1bae1d7aeba4c139551d6f9157367332233e8496a1b5723ebf212d20737884f",
    "tools/generate_focused_fixtures.py": "9b43650fd16f01ac73d027db36c29e06817c1ee530127e6265ee0918b8ecef26",
    "tools/build.py": "c1098f8a4dc74e50f9fc201e6ab75c4de2ba0bc7b3381ccead144d8e181a6697",
    "tools/gate.py": "f46374fd1f16f6dfecae7ccbd2f09f7e27d8751920879e4a9ed71ba6dbf02e3b",
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
    "basis": "faaa5b935",
    "parentEvidence": "parent-faaa5b935/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [57, 355926],
    "diagnosticClassBound": 151,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount57-byte355926",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 56;", "MAX_RAW_CLASSES = 57;")
engine = exact(engine, "MAX_RAW_BYTES = 355643;", "MAX_RAW_BYTES = 355926;")
engine = exact(engine, "uint32(56), uint32(355643)", "uint32(57), uint32(355926)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[56]", "[57]", 4)
coord = exact(coord, "n > 56", "n > 57")
coord = exact(coord, "355643", "355926", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 56", "len(m.Decoders) > 57")
source = exact(source, "len(parts) > 56", "len(parts) > 57")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=150", "classes<=151")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = (prior / "tools/generate_retained_fixtures.py").read_text()
retained = exact(retained, "classcount56-byte355643", "classcount57-byte355926")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58)")
retained = exact(retained, 'count_fixture("count-56-355643", 56, 355643)', 'count_fixture("count-57-355926", 57, 355926)')
retained = exact(retained, 'count_fixture("count-56-355644", 56, 355644)', 'count_fixture("count-57-355927", 57, 355927)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = (prior / "tools/generate_focused_fixtures.py").read_text()
focused = exact(focused, "classcount56-byte355643", "classcount57-byte355926")
assert local_text("tools/generate_focused_fixtures.py") == focused
built = (prior / "tools/build.py").read_text()
built = exact(built, "raw56/byte355643", "raw57/byte355926")
built = exact(built, "classcount56-byte355643", "classcount57-byte355926")
assert local_text("tools/build.py") == built

def expected_gate():
    value = (prior / "tools/gate.py").read_text()
    value = exact(value, "java-diff-mc-classcount56-byte355643-gate-", "java-diff-mc-classcount57-byte355926-gate-")
    value = exact(value, "java-diff-mc-classcount56-byte355643-build-", "java-diff-mc-classcount57-byte355926-build-")
    value = exact(value, "java-diff-mc-classcount56-byte355643-retained-fixtures-", "java-diff-mc-classcount57-byte355926-retained-fixtures-")
    value = exact(value, "java-diff-mc-classcount56-byte355643-focused-fixtures-", "java-diff-mc-classcount57-byte355926-focused-fixtures-")
    value = exact(value, "[56, 355643]", "[57, 355926]")
    value = exact(value, 'diagnosticClassBound"] == 150', 'diagnosticClassBound"] == 151')
    value = exact(value, 'head["totalClassBytes"] <= 355643', 'head["totalClassBytes"] <= 355926', 2)
    start = value.index("# Exact raw56 is the focused capacity witness:")
    end = value.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = value[start:end]
    for old, new in (("raw56", "RAWFOCUS"), ("count-56", "COUNTFOCUS"), ("raw57", "RAWREJECT"), ("count-57", "COUNTREJECT")):
        block = block.replace(old, new)
    for old, new in (("RAWFOCUS", "raw57"), ("COUNTFOCUS", "count-57"), ("RAWREJECT", "raw58"), ("COUNTREJECT", "count-58"), ("355643", "355926"), ("355644", "355927")):
        block = block.replace(old, new)
    block = exact(block, 'assert source.count("len(m.Decoders) > 56") == 1 and source.count("len(parts) > 56") == 1', 'assert source.count("len(m.Decoders) > 57") == 1 and source.count("len(parts) > 57") == 1')
    block = exact(block, 'source.replace("len(m.Decoders) > 56", "len(m.Decoders) > 57")', 'source.replace("len(m.Decoders) > 57", "len(m.Decoders) > 58")')
    block = exact(block, '.replace("len(parts) > 56", "len(parts) > 57")', '.replace("len(parts) > 57", "len(parts) > 58")')
    block = exact(block, 'assert text.count("[56]") == 4 and text.count("n > 56") == 1', 'assert text.count("[57]") == 4 and text.count("n > 57") == 1')
    block = exact(block, 'text.replace("[56]", "[57]").replace("n > 56", "n > 57")', 'text.replace("[57]", "[58]").replace("n > 57", "n > 58")')
    block = exact(block, '["1", "57"]', '["1", "58"]')
    block = exact(block, 'spec["bindingCount"] == 56', 'spec["bindingCount"] == 57')
    block = exact(block, "Raw57 is independently refused", "Raw58 is independently refused")
    assert "raw56" not in block and "count-56" not in block and "355643" not in block and "355644" not in block
    value = value[:start] + block + value[end:]
    value = exact(value, '"profile": "MC-RAW56-BYTE355643-P1"', '"profile": "MC-RAW57-BYTE355926-P1"')
    old = "Only raw capacity constants advance from raw55/355563/diagnostic149 to raw56/355643/diagnostic150. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw56 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fc replay remains deferred."
    new = "Only raw capacity constants advance from raw56/355643/diagnostic150 to raw57/355926/diagnostic151. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw57 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine fm replay remains deferred."
    return exact(value, old, new)

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
