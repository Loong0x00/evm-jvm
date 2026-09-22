#!/usr/bin/env python3
"""Verify raw65/381732 is a literal capacity-only delta from raw64/379594."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount64-byte379594-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377409,
    "initSHA256": "ba29504da6b286591c0ac03eda77673ca5f436a880ebc613194e89828161c57a",
    "runtimeSHA256": "76ced9b94e49066523f55c00c11fbce5402caf3c166a3df030b83d8f8869ae0a",
    "runtimeKeccak256": "1624e883bdaf4458be83917fd36006c0d7e9695361a856eaf5943488a3c54dec",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "245c8962a7867eb8ca442f513a9f5a9a583e7d9402efbe02fc07345bf41ed661",
    "runtimeSHA256": "a1c05a1ec297719fc3ef92bf79da6d100f044cd2c6edd14f62f2c9f9c668f68b",
    "runtimeKeccak256": "ac7828c9d71568a7b6744436310f6c36be488b09ec2d246951589dee3a225d17",
}
PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "27e02ebb253a36e9535a1a25e64119ad71a81adfbecdf1a32e75356aac546881",
    "coordinator/MCEntryCoordinator.sol": "a61803391e474f848f5f3b886bc27c47ad6472b23c72da70fbdbfc3b5a16b770",
    "tools/Go.txt": "6bfa9da6b41c3c3913961d5b1436ede8370450208d1ce6c7f39b9549a31ffd74",
    "tools/checkpoint_diagnostic.py": "7ccb5327e9f629539248b0a9bbf48ef58c17b52dd977c236389441e3b06ff77d",
    "tools/checkpoint_frames.py": "7ccb5327e9f629539248b0a9bbf48ef58c17b52dd977c236389441e3b06ff77d",
    "tools/build.py": "b4827087cb84808d93157bb876bafe3b3fdcd5fab249162280d7300ac92ab29e",
    "tools/gate.py": "c1dfe92e22a5b24d49c02955aeb3efbe728e13cb3e1f013ae42b467f9b1d8bcf",
    "tools/generate_focused_fixtures.py": "0f143d77b6e216198edb2bc784bf7bf7764a91d3cc8bb40f6f90d7c8ffd191b8",
    "tools/generate_retained_fixtures.py": "3284e29bc987bdea3eccb8abfaeec906ae25541ab755a4eeb34d15cabe336122",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
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

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(local_text("build-pins.json"))
assert parent_pins["rawLimits"] == [64, 379594]
assert parent_pins["diagnosticClassBound"] == 158
assert parent_pins["bootstrapCount"] == 94 and parent_pins["globalNativeBindings"] == 16
assert parent_pins["bootstrapRoot"] == "57722a32ab679ecdca73bd05c5cb633aa5984568e531a0dcbf2651bc0dac997c"
assert parent_pins["integer"] == {
    "slot": 70, "bytes": 2039,
    "sha256": "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd",
    "keccak256": "1a698ef9f803879a7f45c3613a679295cd1db22528c2c0e986fc4f9a6b845ba9",
}
assert parent_pins["bootstrapSHA256"]["Integer"] == parent_pins["integer"]["sha256"]
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "classcount64-byte379594-preflight",
    "parentEvidence": "classcount64-byte379594-preflight/{engine,coordinator,tools}",
    "rawLimits": [65, 381732],
    "diagnosticClassBound": 159,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount65-byte381732",
})
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"]
assert pins["integer"] == parent_pins["integer"]

# Integer is inherited as a fixed raw image; its ordered bootstrap leaf/root is
# not regenerated or moved by this capacity-only adjustment.
parent_engine = parent_text("engine/MCEntryInterpreter.sol")
match = re.search(r"function _bootstrapInteger\(\).*?return hex\"([0-9a-f]+)\";", parent_engine, re.S)
assert match
integer_image = bytes.fromhex(match.group(1))
assert len(integer_image) == pins["integer"]["bytes"]
assert hashlib.sha256(integer_image).hexdigest() == pins["integer"]["sha256"]
assert len(re.findall(r"h\[\d+\] = ", parent_engine)) == 94

engine = exact(parent_engine, "MAX_RAW_CLASSES = 64;", "MAX_RAW_CLASSES = 65;")
engine = exact(engine, "MAX_RAW_BYTES = 379594;", "MAX_RAW_BYTES = 381732;")
engine = exact(engine, "uint32(64), uint32(379594)", "uint32(65), uint32(381732)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert match.group(1) in engine

coord = parent_text("coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[64]", "[65]", 4)
coord = exact(coord, "n > 64", "n > 65")
coord = exact(coord, "379594", "381732", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("tools/Go.txt")
source = exact(source, "len(m.Decoders) > 64", "len(m.Decoders) > 65")
source = exact(source, "len(parts) > 64", "len(parts) > 65")
source = exact(source, "377432", "377409", 2)
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=158", "classes<=159")

assert local_text("tools/build.py") == parent_text("tools/build.py").replace("classcount64-byte379594", "classcount65-byte381732").replace("raw64/byte379594", "raw65/byte381732")
assert local_text("tools/generate_focused_fixtures.py") == parent_text("tools/generate_focused_fixtures.py").replace("classcount64-byte379594", "classcount65-byte381732")
retained = parent_text("tools/generate_retained_fixtures.py").replace("classcount64-byte379594", "classcount65-byte381732")
retained = exact(retained, "29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65", "29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66")
retained = exact(retained, "count-64-379594\", 64, 379594", "count-65-381732\", 65, 381732")
retained = exact(retained, "count-64-379595\", 64, 379595", "count-65-381733\", 65, 381733")
assert local_text("tools/generate_retained_fixtures.py") == retained

# The complete gate is inherited verbatim except stage labels and its two exact
# capacity witnesses: raw65/66 and byte381732/381733.
gate = parent_text("tools/gate.py").replace("classcount64-byte379594", "classcount65-byte381732")
gate = exact(gate, "[64, 379594]", "[65, 381732]")
gate = exact(gate, "== 158", "== 159")
gate = gate.replace("<= 379594", "<= 381732")
s = gate.index("# Exact raw64 is the focused capacity witness:")
e = gate.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", s)
b = gate[s:e]
b = b.replace("raw65", "__RAW_REFUSAL__").replace("raw64", "raw65").replace("__RAW_REFUSAL__", "raw66")
b = b.replace("Raw65", "__RAW_REFUSAL_CAPITAL__").replace("Raw64", "Raw65").replace("__RAW_REFUSAL_CAPITAL__", "Raw66")
b = b.replace("count-65", "__COUNT_REFUSAL__").replace("count-64", "count-65").replace("__COUNT_REFUSAL__", "count-66")
b = exact(b, 'assert source.count("len(m.Decoders) > 64") == 1 and source.count("len(parts) > 64") == 1', 'assert source.count("len(m.Decoders) > 65") == 1 and source.count("len(parts) > 65") == 1')
b = exact(b, 'source = (source.replace("len(m.Decoders) > 64", "len(m.Decoders) > 65")\n                    .replace("len(parts) > 64", "len(parts) > 65"))', 'source = (source.replace("len(m.Decoders) > 65", "len(m.Decoders) > 66")\n                    .replace("len(parts) > 65", "len(parts) > 66"))')
b = exact(b, 'assert text.count("[64]") == 4 and text.count("n > 64") == 1', 'assert text.count("[65]") == 4 and text.count("n > 65") == 1')
b = exact(b, 'text.replace("[64]", "[65]").replace("n > 64", "n > 65")', 'text.replace("[65]", "[66]").replace("n > 65", "n > 66")')
b = exact(b, 'spec["bindingCount"] == 64', 'spec["bindingCount"] == 65')
b = exact(b, '["1", "65"]', '["1", "66"]')
b = b.replace("379594", "381732").replace("379595", "381733")
gate = gate[:s] + b + gate[e:]
gate = exact(gate, "MC-RAW64-BYTE379594-P1", "MC-RAW65-BYTE381732-P1")
gate = exact(gate, "Only raw capacity constants advance from raw63/377990/diagnostic157 to raw64/379594/diagnostic158; bootstrap Integer slot70 and its root remain exact.", "Only raw capacity constants advance from raw64/379594/diagnostic158 to raw65/381732/diagnostic159; bootstrap Integer slot70 and its root remain exact.")
gate = exact(gate, "The exact raw64 generated focus", "The exact raw65 generated focus")
gate = exact(gate, "Parent genuine ImmutableEntry replay remains deferred.", "Parent genuine AbstractMapEntry replay remains deferred.")
assert local_text("tools/gate.py") == gate

for relative in ("engine/build.js", "coordinator/build.js", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR,
    "bootstrapRoot": pins["bootstrapRoot"], "integer": pins["integer"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
