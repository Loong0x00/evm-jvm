#!/usr/bin/env python3
"""Verify the raw52/329162 stage is an exact capacity-only parent delta."""
from pathlib import Path
import copy
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-ff10121f9"
generator_parent = stage.parent / "system-out-preflight" / "tools" / "generate_fixtures.py"
previous_build = stage.parent / "classcount51-byte328000-preflight" / "tools" / "build.py"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "c67b1b0e89bf45a06052b821226533c07d592faf4201b9a3a6bf7410472ee975",
    "artifacts/coordinator/MCEntryCoordinator.sol": "851a333500605ecd75223abcd2f8367f09bab7bb57b1e4ac6c33122c4b459485",
    "canonical-driver.go.txt": "4d051470631d0ae23acb72d26bb3613e0f258777c057448c830b5a1c85b71829",
    "checkpoint_diagnostic.py": "840b65f1721169bac22dd19fc6e3a330c2b96d70c18cbe06dd985b48ea917230",
    "checkpoint_frames.py": "840b65f1721169bac22dd19fc6e3a330c2b96d70c18cbe06dd985b48ea917230",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "345cd9f0886136bae51be2d1d0709db961f1c9bcba0fa861140369d048d6bc5f",
    "generated_gate.py": "bdadc19e0e26b4750b97503e1916a1cd93d4a83a9ce448cb4e8a6b4022912227",
}
GENERATOR_SHA256 = "c616840c6b6aa6626beee94e50802618aacbd715b982c7c045073bde2ad45aca"
ENGINE = {
    "bytes": 373634,
    "initSHA256": "ce1791c5e69457ec61b768bf4276ac2326825f24598054b1e7292bea0a633e5b",
    "runtimeSHA256": "76f3ebd73d9dc97dbb90fa12af3909691b6562628e1fd2759553d9b0f1df32bf",
    "runtimeKeccak256": "3945b3cf36830821333053345232da292816d7a8f89066f507c1161740b11fd3",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "c61e347049d94b21a5bc699781b1849eb87ee9d30ea83dbe3e4fa7f56e5501c7",
    "runtimeSHA256": "9848ec61605a519f858000e91a5955ca8cd5deabb09005ae944a1c1096fe5fa7",
    "runtimeKeccak256": "348c04fd8df68a05f296b938c063c363f93c89fe80570e04a40588d86d9479c2",
}
PARENT_ENGINE_KECCAK = "2e39559c5ffafda3fbca8c6de772aab81dfa4800e3eafbc416ab2ea1cda80c82"
PARENT_ENGINE_SHA256 = "112430e03816e1d80a78ce32fa76000a1837904674874e516ce3408efc8fc03c"
PARENT_COORDINATOR_KECCAK = "ead84d85691a7abb5fbc8f9c907861f6393c32c8c249acc61abaa92cea9c3766"

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
assert sha(generator_parent) == GENERATOR_SHA256

parent_pins = json.loads(parent_text("pins.json"))
pins = json.loads(local_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "ff10121f9",
    "parentEvidence": "parent-ff10121f9/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [52, 329162],
    "diagnosticClassBound": 146,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount52-byte329162",
})
assert pins == expected_pins
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 14
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
engine = exact(engine, "MAX_RAW_CLASSES = 51;", "MAX_RAW_CLASSES = 52;")
engine = exact(engine, "MAX_RAW_BYTES = 328000;", "MAX_RAW_BYTES = 329162;")
engine = exact(engine, "uint32(51), uint32(328000)", "uint32(52), uint32(329162)")
assert local_text("engine/MCEntryInterpreter.sol") == engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[51]", "[52]", 4)
coord = exact(coord, "n > 51", "n > 52")
coord = exact(coord, "328000", "329162", 2)
coord = exact(coord, PARENT_ENGINE_KECCAK, ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 51", "len(m.Decoders) > 52")
source = exact(source, "len(parts) > 51", "len(parts) > 52")
source = exact(source, PARENT_ENGINE_SHA256, ENGINE["runtimeSHA256"])
source = exact(source, "0x" + PARENT_ENGINE_KECCAK, "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + PARENT_COORDINATOR_KECCAK, "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    expected = exact(parent_text(relative), "classes<=145", "classes<=146")
    assert local_text("tools/" + relative) == expected
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

fixtures = generator_parent.read_text()
fixtures = exact(fixtures, "java-diff-mc-system-out-fixtures-", "java-diff-mc-classcount52-byte329162-retained-fixtures-")
fixtures = exact(fixtures, "# Exact raw51 and aggregate-byte boundaries exercise this measured cap lift.", "# Exact raw52 and aggregate-byte boundaries exercise this measured cap lift.")
fixtures = exact(fixtures, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53)")
fixtures = exact(fixtures, 'count_fixture("count-51-328000", 51, 328000)', 'count_fixture("count-52-329162", 52, 329162)')
fixtures = exact(fixtures, 'count_fixture("count-51-328001", 51, 328001)', 'count_fixture("count-52-329163", 52, 329163)')
assert local_text("tools/generate_fixtures.py") == fixtures

expected_build = previous_build.read_text()
expected_build = exact(expected_build, "raw51/byte328000", "raw52/byte329162")
expected_build = exact(expected_build, "classcount51-byte328000", "classcount52-byte329162")
assert local_text("tools/build.py") == expected_build

gate = parent_text("generated_gate.py")
gate = exact(gate, "root = here.parents[3]", "root = here.parents[4]")
gate = exact(gate, "java-diff-mc-systemout-parent-gate-", "java-diff-mc-classcount52-byte329162-gate-")
gate = exact(gate, "java-diff-mc-systemout-parent-", "java-diff-mc-classcount52-byte329162-build-")
gate = exact(gate, "java-diff-mc-system-out-fixtures-", "java-diff-mc-classcount52-byte329162-retained-fixtures-")
gate = exact(gate, "[51, 328000]", "[52, 329162]")
gate = exact(gate, 'diagnosticClassBound"] == 145', 'diagnosticClassBound"] == 146')
gate = exact(gate, 'head["totalClassBytes"] <= 328000', 'head["totalClassBytes"] <= 329162', 2)
start = gate.index("# Exact raw51 is the focused capacity witness:")
end = gate.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
block = gate[start:end]
block = exact(block, "raw52", "raw53", 13)
block = exact(block, "raw51", "raw52", 2)
block = exact(block, "count-52", "count-53", 6)
block = exact(block, "count-51", "count-52", 7)
block = exact(block, 'retained("raw52", "count-52")', 'q_equivalent("raw52", "count-52")')
block = exact(block, "len(m.Decoders) > 51", "len(m.Decoders) > 52", 2)
block = exact(block, 'len(m.Decoders) > 52", "len(m.Decoders) > 52', 'len(m.Decoders) > 52", "len(m.Decoders) > 53')
block = exact(block, "len(parts) > 51", "len(parts) > 52", 2)
block = exact(block, 'len(parts) > 52", "len(parts) > 52', 'len(parts) > 52", "len(parts) > 53')
block = exact(block, 'text.count("[51]") == 4 and text.count("n > 51") == 1', 'text.count("[52]") == 4 and text.count("n > 52") == 1')
block = exact(block, 'text.replace("[51]", "[52]").replace("n > 51", "n > 52")', 'text.replace("[52]", "[53]").replace("n > 52", "n > 53")')
block = exact(block, '["1", "52"]', '["1", "53"]')
block = exact(block, "328001", "329163", 8)
block = exact(block, "328000", "329162", 8)
block = exact(block, "# chains agree. Raw52 is independently refused before mutation by the product\n", "# chains agree. Raw53 is independently refused before mutation by the product\n")
block = exact(block, 'assert spec["bindingCount"] == 51 and spec["totalClassBytes"] == total', 'assert spec["bindingCount"] == 52 and spec["totalClassBytes"] == total')
gate = gate[:start] + block + gate[end:]
gate = exact(gate, '"profile": "MC-SYSTEM-OUT-P1"', '"profile": "MC-RAW52-BYTE329162-P1"')
old = "Only bootstrap image44 java/lang/System changes: public static final PrintStream out is constructed after the retained err as a distinct non-null guest sink. No host stdout/stderr, console, file, provider, stream setter, input stream, or broader System API is exposed. Raw51/328000, diagnostic145, all 94 ordered bootstrap positions, native14, String-local11, exception14, frame/checkpoint/selected-resource limits, toolchain, and runtime-derived root rules remain pinned. The exact System.out generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent alone owns unchanged-original replay."
new = "Only raw capacity constants advance from raw51/328000/diagnostic145 to raw52/329162/diagnostic146. All 94 ordered bootstrap images and their runtime-derived root, native14, String-local11, System out/err, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw52 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent alone owns genuine no binding and replay."
gate = exact(gate, old, new)
assert local_text("tools/gate.py") == gate

assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": pins["bootstrapRoot"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
