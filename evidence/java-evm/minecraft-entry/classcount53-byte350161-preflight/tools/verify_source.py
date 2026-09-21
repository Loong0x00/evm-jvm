#!/usr/bin/env python3
"""Verify the raw53/350161 stage is an exact capacity-only parent delta."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-7e9332014"
retained_parent = stage.parent / "system-set-out-preflight" / "tools" / "generate_retained_fixtures.py"
focused_parent = stage.parent / "system-set-out-preflight" / "tools" / "generate_focused_fixtures.py"
previous_build = stage.parent / "classcount52-byte329162-preflight" / "tools" / "build.py"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "5a97b239a9fd6da8b3000fbeb86cd3e685f84b6969046105f8b093f9fd6a2402",
    "artifacts/coordinator/MCEntryCoordinator.sol": "0579b9ae43e1966a10349c1ef1f2523c541f8061dbf669be6d639161d8e0e839",
    "canonical-driver.go.txt": "df44400026b4be51e984da95016dc87bd5a0aa6d24439621f0c3df305873e376",
    "checkpoint_diagnostic.py": "205548d955b322296710b9449e9dc5813a2941fc7f6e67060e54b871f69437c7",
    "checkpoint_frames.py": "205548d955b322296710b9449e9dc5813a2941fc7f6e67060e54b871f69437c7",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "aff42051161e4eddeb4afe6beff8bfdf0df3ac2d25c281f5b47963cbe646e0fe",
    "generated_gate.py": "c7bd2510de552a4a2489837f51165b674dbf07d18817e175bf12785ba638dfa0",
}
RETAINED_GENERATOR_SHA256 = "927a56489fc93638b39952d3854e295ec90af7504e85c00ba66be8afec48396f"
FOCUSED_GENERATOR_SHA256 = "5db31cbe42f06da447f0c6754c73a20c466d561dd8050362e070ec8f0f11fafd"
PREVIOUS_BUILD_SHA256 = "139f1647ce56fa906b37fdba08257a6e6fc73ea7cbb602cddd8329705502f05d"
ENGINE = {
    "bytes": 377312,
    "initSHA256": "e145e61eb6ba2deb975d59336598d1b699b25db8acdaa3149b80af9919e0da28",
    "runtimeSHA256": "c39746fe252410dbd54520f9807567746c3595ca4504bd6a2212a68537e5115a",
    "runtimeKeccak256": "d7cfd5ae90a2f17b8c07fae1c5e174df31db5996c1e3061f5f40e0f7e171159d",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "afff80cabde591da8b01b0f70d62b3759969830251d6c3c5d6ec393247d4d584",
    "runtimeSHA256": "e2eaa83d0fe274215811982a8d80309e6e2a0c70e55c667f2aa78ef485e9c77f",
    "runtimeKeccak256": "c9b51e00a2ab1811e0b88b55dd9de1888ea42cb8b72733e7a6d1113b659c0324",
}
PARENT_ENGINE = {
    "runtimeSHA256": "b1e96bd7f3ceef7545d66894adac3a7f237b404a95447dedf0fc44299afe915f",
    "runtimeKeccak256": "fc102a43f14c48e6bb880ae53b46faef1cacdfc345d11c67590925c4b53dae56",
}
PARENT_COORDINATOR_KECCAK = "370b28185afa658202c1235ee7d0ece13a4f0c59c37e078f3e91e370cc66faf2"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def exact(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)

def parent_text(relative):
    return (parent / relative).read_text()

def local_text(relative):
    return (stage / relative).read_text()

for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
assert sha(retained_parent) == RETAINED_GENERATOR_SHA256
assert sha(focused_parent) == FOCUSED_GENERATOR_SHA256
assert sha(previous_build) == PREVIOUS_BUILD_SHA256

parent_pins = json.loads(parent_text("pins.json"))
pins = json.loads(local_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "7e9332014",
    "parentEvidence": "parent-7e9332014/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [53, 350161],
    "diagnosticClassBound": 147,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount53-byte350161",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 16
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 52;", "MAX_RAW_CLASSES = 53;")
engine = exact(engine, "MAX_RAW_BYTES = 329162;", "MAX_RAW_BYTES = 350161;")
engine = exact(engine, "uint32(52), uint32(329162)", "uint32(53), uint32(350161)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[52]", "[53]", 4)
coord = exact(coord, "n > 52", "n > 53")
coord = exact(coord, "329162", "350161", 2)
coord = exact(coord, PARENT_ENGINE["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 52", "len(m.Decoders) > 53")
source = exact(source, "len(parts) > 52", "len(parts) > 53")
source = exact(source, PARENT_ENGINE["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + PARENT_ENGINE["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + PARENT_COORDINATOR_KECCAK, "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=146", "classes<=147")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

retained = retained_parent.read_text()
retained = exact(retained, "java-diff-mc-system-set-out-retained-fixtures-", "java-diff-mc-classcount53-byte350161-retained-fixtures-")
retained = exact(retained, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54)")
retained = exact(retained, 'count_fixture("count-52-329162", 52, 329162)', 'count_fixture("count-53-350161", 53, 350161)')
retained = exact(retained, 'count_fixture("count-52-329163", 52, 329163)', 'count_fixture("count-53-350162", 53, 350162)')
assert local_text("tools/generate_retained_fixtures.py") == retained
focused = exact(focused_parent.read_text(), "java-diff-mc-system-set-out-fixtures-", "java-diff-mc-classcount53-byte350161-focused-fixtures-")
assert local_text("tools/generate_focused_fixtures.py") == focused

expected_build = previous_build.read_text()
expected_build = exact(expected_build, "raw52/byte329162", "raw53/byte350161")
expected_build = exact(expected_build, "classcount52-byte329162", "classcount53-byte350161")
assert local_text("tools/build.py") == expected_build

def expected_gate():
    s=parent_text("generated_gate.py")
    def exact(text, old, new, count=1):
        assert text.count(old)==count,(old,text.count(old),count)
        return text.replace(old,new)
    s=exact(s,'root = here.parents[3]','root = here.parents[4]')
    s=exact(s,'java-diff-mc-setout-parent-gate-','java-diff-mc-classcount53-byte350161-gate-')
    s=exact(s,'java-diff-mc-setout-parent-','java-diff-mc-classcount53-byte350161-build-')
    s=exact(s,'java-diff-mc-system-set-out-retained-fixtures-','java-diff-mc-classcount53-byte350161-retained-fixtures-')
    s=exact(s,'java-diff-mc-system-set-out-fixtures-','java-diff-mc-classcount53-byte350161-focused-fixtures-')
    s=exact(s,'[52, 329162]','[53, 350161]')
    s=exact(s,'diagnosticClassBound"] == 146','diagnosticClassBound"] == 147')
    s=exact(s,'head["totalClassBytes"] <= 329162','head["totalClassBytes"] <= 350161',2)
    start=s.index('# Exact raw52 is the focused capacity witness:')
    end=s.index('# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.',start)
    block=s[start:end]
    block=exact(block,'Exact raw52','Exact raw53')
    block=exact(block,'Raw53','Raw54')
    block=exact(block,'q_equivalent("raw52", "count-52")','q_equivalent("raw53", "count-53")')
    block=exact(block,'world-raw53-driver','world-raw54-driver')
    block=exact(block,'"raw53-driver"','"raw54-driver"',2)
    block=exact(block,'"count-53.zip"','"count-54.zip"',3)
    block=exact(block,'"count-53", expect=2','"count-54", expect=2')
    block=exact(block,'], "count-53")','], "count-54")',2)
    block=exact(block,'"raw53-coordinator-driver"','"raw54-coordinator-driver"')
    block=exact(block,'len(m.Decoders) > 52','len(m.Decoders) > 53',2)
    block=exact(block,'len(parts) > 52','len(parts) > 53',2)
    block=exact(block,'len(m.Decoders) > 53", "len(m.Decoders) > 53','len(m.Decoders) > 53", "len(m.Decoders) > 54')
    block=exact(block,'len(parts) > 53", "len(parts) > 53','len(parts) > 53", "len(parts) > 54')
    block=exact(block,'world-raw53-coordinator','world-raw54-coordinator')
    block=exact(block,'"raw53-coordinator"','"raw54-coordinator"',2)
    block=exact(block,'raw53-engine-coordinator','raw54-engine-coordinator',2)
    block=exact(block,'text.count("[52]") == 4 and text.count("n > 52") == 1','text.count("[53]") == 4 and text.count("n > 53") == 1')
    block=exact(block,'text.replace("[52]", "[53]").replace("n > 52", "n > 53")','text.replace("[53]", "[54]").replace("n > 53", "n > 54")')
    block=exact(block,'"raw53-engine-driver"','"raw54-engine-driver"')
    block=exact(block,'world-raw53-engine','world-raw54-engine')
    block=exact(block,'"raw53-engine"','"raw54-engine"',2)
    block=exact(block,'["1", "53"]','["1", "54"]')
    block=exact(block,'("count-52-329162", 329162), ("count-52-329163", 329163)','("count-53-350161", 350161), ("count-53-350162", 350162)')
    block=exact(block,'spec["bindingCount"] == 52','spec["bindingCount"] == 53')
    block=exact(block,'Exactly 329162','Exactly 350161')
    block=exact(block,'329163 is rejected','350162 is rejected')
    block=exact(block,'world-byte-329162','world-byte-350161')
    block=exact(block,'"byte-329162"','"byte-350161"',2)
    block=exact(block,'"count-52-329162.zip"','"count-53-350161.zip"')
    block=exact(block,'"count-52-329162"','"count-53-350161"')
    block=exact(block,'world-byte-329163','world-byte-350162')
    block=exact(block,'"byte-329163"','"byte-350162"',2)
    block=exact(block,'"count-52-329163.zip"','"count-53-350162.zip"')
    block=exact(block,'"count-52-329163"','"count-53-350162"')
    s=s[:start]+block+s[end:]
    s=exact(s,'"profile": "MC-SYSTEM-SET-OUT-P1"','"profile": "MC-RAW53-BYTE350161-P1"')
    old='Only canonical bootstrap image44 changes. Binding16 resolves exactly public static native System.setOut(PrintStream), then mutates canonical initialized System.out only; System.err and every other static remain unchanged. No SecurityManager permission, host stdout/stderr, forwarding, console, file, or provider behavior exists. Raw52/329162, diagnostic146, 94 images, native16, String-local11, exception14, frame/checkpoint/selected-resource limits, toolchain, and runtime-derived ordered-root rules remain pinned. The setOut identity/err/null/reset/subclass witness runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. No original artifact/JAR/resource, world, EULA, or Done input or claim exists. Parent replay remains deferred.'
    new='Only raw capacity constants advance from raw52/329162/diagnostic146 to raw53/350161/diagnostic147. All 94 ordered bootstrap images and their runtime-derived root, native16, String-local11, System setters, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw53 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent genuine qe replay remains deferred.'
    s=exact(s,old,new)
    old='''# Exactly 350161 raw bytes is admitted by the coordinator and reaches the
# engine\'s ordinary parser. The retained engine-side gas/reserve refusal proves
# only that this giant generated package cannot finish this bounded call; it is
# not a coordinator byte-limit refusal. 350162 is rejected atomically there.
world = out / "world-byte-350161"
run("byte-350161", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-53-350161.zip", "4096"], "count-53-350161")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["byte-350161"] = {"coordinatorAccepted": True, "engineRefusal": refusal}
'''
    new='''# Exactly 350161 raw bytes is admitted by the coordinator and fully supplied
# through DI0 to the engine. The fixed LOCAL1B call reaches the inherited empty
# EVM revert after that positive work; it is not a coordinator byte-limit
# refusal or a fabricated typed Java outcome. 350162 is rejected atomically
# by the coordinator before that engine work.
world = out / "world-byte-350161"
run("byte-350161", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-53-350161.zip", "4096"], "count-53-350161")
refusal = failure(world, "start-refusal.json")
assert sum(refusal["actualDI0ReadSizes"]) == 350161 and refusal["selector"] == "0x" and words(refusal) == []
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
rows["byte-350161"] = {"coordinatorAccepted": True, "engineRefusal": refusal}
'''
    s=exact(s,old,new)
    assert 'raw52-driver' not in s and 'count-52-329162' not in s and 'count-52-329163' not in s
    assert 'raw54-driver' in s and 'count-53-350161' in s and 'count-53-350162' in s
    return s

assert local_text("tools/gate.py") == expected_gate()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
