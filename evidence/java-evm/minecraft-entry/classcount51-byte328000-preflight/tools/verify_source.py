#!/usr/bin/env python3
"""Verify raw51/328000 is an exact capacity-only delta from parent e883."""
from pathlib import Path
import copy
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-e883ec304"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

def read(path): return (stage / path).read_text()
def parent_read(path): return (parent / path).read_text()
def exact_replace(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)

pins = json.loads(read("build-pins.json"))
parent_pins = json.loads(parent_read("pins.json"))
assert pins["rawLimits"] == [51, 328000] and pins["diagnosticClassBound"] == 145
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 14
assert pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["checkpointCap"] == 1_048_576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] == 373596 <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"] and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]
assert pins["basis"] == "e883ec304" and pins["parentEvidence"] == "parent-e883ec304/artifacts/{engine,coordinator}/MCEntry*.sol"

engine = parent_read("artifacts/engine/MCEntryInterpreter.sol")
engine = exact_replace(engine, "MAX_RAW_CLASSES = 50;", "MAX_RAW_CLASSES = 51;")
engine = exact_replace(engine, "MAX_RAW_BYTES = 324338;", "MAX_RAW_BYTES = 328000;")
engine = exact_replace(engine, "uint32(50), uint32(324338)", "uint32(51), uint32(328000)")
assert read("engine/MCEntryInterpreter.sol") == engine

coord = parent_read("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact_replace(coord, "[50]", "[51]", 4)
coord = exact_replace(coord, "n > 50", "n > 51")
coord = exact_replace(coord, "324338", "328000", 2)
coord = exact_replace(coord, 'hex"1012415e5522d320596e7926fe0726946305441541f8d7d6e4d1a780f41a5864"', 'hex"' + pins["engine"]["runtimeKeccak256"] + '"')
assert read("coordinator/MCEntryCoordinator.sol") == coord

source = parent_read("canonical-driver.go.txt")
source = exact_replace(source, "len(m.Decoders) > 50", "len(m.Decoders) > 51")
source = exact_replace(source, "len(parts) > 50", "len(parts) > 51")
source = exact_replace(source, "c111e0f6abe60b2721e54ade23a5ff180d6caea370c73bcc693841f62b0f00f3", pins["engine"]["runtimeSHA256"])
source = exact_replace(source, "0x1012415e5522d320596e7926fe0726946305441541f8d7d6e4d1a780f41a5864", "0x" + pins["engine"]["runtimeKeccak256"])
source = exact_replace(source, "0xb454642b1787f9b546af4e1d913a9791a3dbc0c9bb1c876511173e4b4b2db6ae", "0x" + pins["coordinator"]["runtimeKeccak256"])
assert read("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert read("tools/" + relative) == exact_replace(parent_read(relative), "classes<=144", "classes<=145")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()

fixtures = (stage.parent / "index-out-of-bounds-string-constructor-preflight/tools/generate_fixtures.py").read_text()
fixtures = exact_replace(fixtures, "java-diff-mc-index-out-of-bounds-string-constructor-fixtures-", "java-diff-mc-classcount51-byte328000-retained-fixtures-")
fixtures = exact_replace(fixtures, "# Exact raw50 and aggregate-byte boundaries exercise this measured cap lift.", "# Exact raw51 and aggregate-byte boundaries exercise this measured cap lift.")
fixtures = exact_replace(fixtures, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51)", "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52)")
fixtures = exact_replace(fixtures, 'count_fixture("count-50-324338", 50, 324338)', 'count_fixture("count-51-328000", 51, 328000)')
fixtures = exact_replace(fixtures, 'count_fixture("count-50-324339", 50, 324339)', 'count_fixture("count-51-328001", 51, 328001)')
assert read("tools/generate_fixtures.py") == fixtures

# The current full gate is inherited exact except its local path assertions,
# capacity witnesses, and the explicit raw51 q1/q7/direct/reopen strengthening.
gate = parent_read("generated_gate.py")
gate = exact_replace(gate, "root = here.parents[3]", "root = here.parents[4]")
gate = exact_replace(gate, "java-diff-mc-substring-parent-gate-", "java-diff-mc-classcount51-byte328000-gate-")
gate = exact_replace(gate, "java-diff-mc-substring-parent-", "java-diff-mc-classcount51-byte328000-build-")
gate = exact_replace(gate, "java-diff-mc-index-out-of-bounds-string-constructor-fixtures-", "java-diff-mc-classcount51-byte328000-retained-fixtures-")
gate = exact_replace(gate, "[50, 324338]", "[51, 328000]")
gate = exact_replace(gate, 'diagnosticClassBound"] == 144', 'diagnosticClassBound"] == 145')
gate = exact_replace(gate, 'head["totalClassBytes"] <= 324338', 'head["totalClassBytes"] <= 328000', 2)
start = gate.index("# Exact raw50 is the focused capacity witness:")
end = gate.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
block = gate[start:end]
block = exact_replace(block, "raw50", "__RAW50__", 2)
block = exact_replace(block, "raw51", "raw52", 13)
block = exact_replace(block, "__RAW50__", "raw51", 2)
block = exact_replace(block, "count-50", "__COUNT50__", 7)
block = exact_replace(block, "count-51", "count-52", 6)
block = exact_replace(block, "__COUNT50__", "count-51", 7)
block = exact_replace(block, 'retained("raw51", "count-51")', 'q_equivalent("raw51", "count-51")')
block = exact_replace(block, 'assert source.count("len(m.Decoders) > 50") == 1 and source.count("len(parts) > 50") == 1', 'assert source.count("len(m.Decoders) > 51") == 1 and source.count("len(parts) > 51") == 1')
block = exact_replace(block, 'len(m.Decoders) > 50", "len(m.Decoders) > 51', 'len(m.Decoders) > 51", "len(m.Decoders) > 52')
block = exact_replace(block, 'len(parts) > 50", "len(parts) > 51', 'len(parts) > 51", "len(parts) > 52')
block = exact_replace(block, 'text.count("[50]") == 4 and text.count("n > 50") == 1', 'text.count("[51]") == 4 and text.count("n > 51") == 1')
block = exact_replace(block, 'text.replace("[50]", "[51]").replace("n > 50", "n > 51")', 'text.replace("[51]", "[52]").replace("n > 51", "n > 52")')
block = exact_replace(block, '["1", "51"]', '["1", "52"]')
block = exact_replace(block, 'spec["bindingCount"] == 50', 'spec["bindingCount"] == 51')
block = exact_replace(block, "324338", "__FIT__", 8)
block = exact_replace(block, "324339", "328001", 8)
block = exact_replace(block, "__FIT__", "328000", 8)
block = exact_replace(block, "Raw51", "Raw52")
gate = gate[:start] + block + gate[end:]
gate = exact_replace(gate, '"profile": "MC-STRING-SUBSTRING-INT-FULL-GATE"', '"profile": "MC-RAW51-BYTE328000-P1"')
gate = exact_replace(gate, "Only bootstrap image26 String changes. String.substring(int) returns its exact receiver only at begin zero; every nonzero valid UTF-16 suffix owns a copied char[] and String, including an empty suffix. Invalid begins retain StringProfileError and the two-argument overload remains absent. The current parent-generated retained corpus reruns direct/reopen where its historical q1 corpus would exceed the fixed 1200-second whole gate; current valid-suffix cases retain q1/q7/direct/reopen. This generated-only gate uses only trusted generated Java-8 fixtures and no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent alone owns genuine replay.", "Only the raw capacity constants advance from raw50/324338/diagnostic144 to raw51/328000/diagnostic145. All 94 bootstrap images and their runtime-derived ordered root, global native14, String-local11, exception14, frame/checkpoint/selected-resource limits and toolchain remain pinned. The exact raw51 generated focus runs q1/q7/direct/reopen; inherited generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This generated-only gate uses only trusted generated Java-8 fixtures and no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent alone owns genuine ni append and replay.")
assert read("tools/gate.py") == gate

expected = copy.deepcopy(parent_pins)
expected.update({"basis": "e883ec304", "parentEvidence": "parent-e883ec304/artifacts/{engine,coordinator}/MCEntry*.sol", "phase": "built", "rawLimits": [51, 328000], "diagnosticClassBound": 145, "engine": pins["engine"], "coordinator": pins["coordinator"], "worker": "classcount51-byte328000"})
assert pins == expected
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"basis": pins["basis"], "rawLimits": pins["rawLimits"], "diagnosticClassBound": pins["diagnosticClassBound"], "engine": pins["engine"], "coordinator": pins["coordinator"], "bootstrapRoot": pins["bootstrapRoot"], "verification": "literal-capacity-only-source-delta"}, indent=2))
