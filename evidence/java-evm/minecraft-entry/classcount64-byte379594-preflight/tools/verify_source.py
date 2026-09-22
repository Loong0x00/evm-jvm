#!/usr/bin/env python3
"""Verify raw64/379594 is a literal capacity-only delta from raw63/377990."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount63-byte377990-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377432,
    "initSHA256": "5120ba754fd9253640f954856116951c6e755b5ee47de42543fe4a18b7ef1416",
    "runtimeSHA256": "0a52a8b0f61dd84a017c28f6b238e6d3e247bc6a6acb1d808eabaa09cbff9867",
    "runtimeKeccak256": "dd5928fefe9a7a9a0ac2d78b2705cd1dbdb5c5a647874b14a41fda0162768e4d",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "962adaf93436d269f90bb061e2ccf0215e4e56628160d416b2b642ec53905140",
    "runtimeSHA256": "6edcc6d11660a46028072e5fdda5bcc83e92e47df8ade2dc24eab2373934dc63",
    "runtimeKeccak256": "db41f8e16fec9b88d2fc4b32c6237b4fd5fe9188627519112d281821db058740",
}
PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "b7f468aac813a97aa1ace0f8becbd801fdd4dcf657ccea49aeca3aca04c115b0",
    "coordinator/MCEntryCoordinator.sol": "b5a89788beabf09fe4c271b24327fd8dc90f1ccc4bf1670264cae9d3b04628a4",
    "tools/Go.txt": "80b2eb66f0ef47aff9afbf672f3f78aadf844bd286661a53929a5e864b01bd92",
    "tools/checkpoint_diagnostic.py": "72fef13a5cf3260bbf3bfee27e8320dc14f1cc29c18ff4bcb5c66122fd789b11",
    "tools/checkpoint_frames.py": "72fef13a5cf3260bbf3bfee27e8320dc14f1cc29c18ff4bcb5c66122fd789b11",
    "tools/build.py": "7171d6b86507ad3d62df587f675843334f59bcedc1d8490042870955a5aa3117",
    "tools/gate.py": "17761643c83379f455eea58eb75fb6e620c10e1e3efe83f322ee0102e7b795d1",
    "tools/generate_focused_fixtures.py": "1282aedb3aeeb98fba44e4ecf73ce5ae81dd78640c1d1fa96352075f56356d40",
    "tools/generate_retained_fixtures.py": "8bb0252cbb3ecc3d0983bf688eafaef70734661fe6ede400fbd077794b76465a",
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
assert parent_pins["rawLimits"] == [63, 377990]
assert parent_pins["diagnosticClassBound"] == 157
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
    "basis": "classcount63-byte377990-preflight",
    "parentEvidence": "classcount63-byte377990-preflight/{engine,coordinator,tools}",
    "rawLimits": [64, 379594],
    "diagnosticClassBound": 158,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount64-byte379594",
})
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"]
assert pins["integer"] == parent_pins["integer"]

# The accepted Integer image is neither rebuilt nor regenerated.  Its raw image
# and the ordered bootstrap leaves are byte-for-byte inherited from raw63.
parent_engine = parent_text("engine/MCEntryInterpreter.sol")
match = re.search(r"function _bootstrapInteger\(\).*?return hex\"([0-9a-f]+)\";", parent_engine, re.S)
assert match
integer_image = bytes.fromhex(match.group(1))
assert len(integer_image) == pins["integer"]["bytes"]
assert hashlib.sha256(integer_image).hexdigest() == pins["integer"]["sha256"]
assert len(re.findall(r"h\[\d+\] = ", parent_engine)) == 94

engine = exact(parent_engine, "MAX_RAW_CLASSES = 63;", "MAX_RAW_CLASSES = 64;")
engine = exact(engine, "MAX_RAW_BYTES = 377990;", "MAX_RAW_BYTES = 379594;")
engine = exact(engine, "uint32(63), uint32(377990)", "uint32(64), uint32(379594)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert match.group(1) in engine

coord = parent_text("coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[63]", "[64]", 4)
coord = exact(coord, "n > 63", "n > 64")
coord = exact(coord, "377990", "379594", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("tools/Go.txt")
source = exact(source, "len(m.Decoders) > 63", "len(m.Decoders) > 64")
source = exact(source, "len(parts) > 63", "len(parts) > 64")
source = exact(source, "377409", "377432", 2)
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=157", "classes<=158")

assert local_text("tools/build.py") == parent_text("tools/build.py").replace("classcount63-byte377990", "classcount64-byte379594").replace("raw63/byte377990", "raw64/byte379594")
assert local_text("tools/generate_focused_fixtures.py") == parent_text("tools/generate_focused_fixtures.py").replace("classcount63-byte377990", "classcount64-byte379594")
retained = parent_text("tools/generate_retained_fixtures.py").replace("classcount63-byte377990", "classcount64-byte379594")
retained = exact(retained, "29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64", "29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65")
retained = exact(retained, "count-63-377990\", 63, 377990", "count-64-379594\", 64, 379594")
retained = exact(retained, "count-63-377991\", 63, 377991", "count-64-379595\", 64, 379595")
assert local_text("tools/generate_retained_fixtures.py") == retained

# The gate retains every prior generated direct/reopen control.  Its only edits
# are reproducible directory labels plus the 64/65 and 379594/379595 witnesses.
gate = parent_text("tools/gate.py")
gate = gate.replace("classcount63-byte377990", "classcount64-byte379594")
gate = exact(gate, "[63, 377990]", "[64, 379594]")
gate = exact(gate, "== 157", "== 158")
gate = gate.replace("<= 377990", "<= 379594")
s = gate.index("# Exact raw63 is the focused capacity witness:")
e = gate.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", s)
b = gate[s:e]
b = exact(b, "# Exact raw63 is the focused capacity witness:", "# Exact raw64 is the focused capacity witness:")
b = exact(b, "# chains agree. Raw64 is independently refused", "# chains agree. Raw65 is independently refused")
b = exact(b, 'q_equivalent("raw63", "count-63")', 'q_equivalent("raw64", "count-64")')
a = b.index('world = out / "world-raw64-driver"')
b = b[:a] + b[a:].replace("raw64", "raw65").replace("count-64", "count-65")
b = b.replace("len(m.Decoders) > 63", "len(m.Decoders) > 64")
b = b.replace("len(parts) > 63", "len(parts) > 64")
b = exact(b, 'source.replace("len(m.Decoders) > 64", "len(m.Decoders) > 64")', 'source.replace("len(m.Decoders) > 64", "len(m.Decoders) > 65")')
b = exact(b, '.replace("len(parts) > 64", "len(parts) > 64")', '.replace("len(parts) > 64", "len(parts) > 65")')
b = b.replace("[63]", "[64]").replace("n > 63", "n > 64")
b = exact(b, 'text.replace("[64]", "[64]").replace("n > 64", "n > 64")', 'text.replace("[64]", "[65]").replace("n > 64", "n > 65")')
b = b.replace("count-63", "count-64").replace("377990", "379594").replace("377991", "379595")
b = exact(b, 'spec["bindingCount"] == 63', 'spec["bindingCount"] == 64')
b = exact(b, '["1", "64"]', '["1", "65"]')
gate = gate[:s] + b + gate[e:]
gate = exact(gate, "MC-RAW63-BYTE377990-P1", "MC-RAW64-BYTE379594-P1")
gate = exact(gate, "Only raw capacity constants advance from raw62/376794/diagnostic156 to raw63/377990/diagnostic157; bootstrap Integer slot70 and its root remain exact.", "Only raw capacity constants advance from raw63/377990/diagnostic157 to raw64/379594/diagnostic158; bootstrap Integer slot70 and its root remain exact.")
gate = exact(gate, "The exact raw63 generated focus", "The exact raw64 generated focus")
gate = exact(gate, "Parent genuine HashBiMap$BiEntry replay remains deferred.", "Parent genuine ImmutableEntry replay remains deferred.")
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
