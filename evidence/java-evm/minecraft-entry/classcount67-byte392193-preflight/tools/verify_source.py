#!/usr/bin/env python3
"""Verify raw67/392193 is a literal capacity-only delta from raw66/385532."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount66-byte385532-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 376562,
    "initSHA256": "23579b945f160d91fb9ef836228ac3ab8c8f1ada1e4a6686f16ace9a6bee21b2",
    "runtimeSHA256": "45c4580328a555a1af54389dcfe4dbb02ab31449116b91f3528168e8b49763f3",
    "runtimeKeccak256": "fc17ece6ec0f3ab0f3c6bbba18168fa5acc19c1f0846b714798f06cacd008c6a",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "96602d31eceb220e10f34c666296c175c02adc108911c665c0c2a3d3b25a1230",
    "runtimeSHA256": "e2b98959965590e6241a2abf87e0191c93f7401c81b880860003b6e8eaa113e9",
    "runtimeKeccak256": "96452a3291b2ff726a4dd447b819b54c9b7a3f73bc41336d69f416c258de15ae",
}
PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "a667afa6cd4687fa475aabe064a18a5c8df07468206a8a60daf14afe6d38ec35",
    "coordinator/MCEntryCoordinator.sol": "b2b56ca07cbcec24f4ecf4226751ee759e295676b2d52d2a9de70858d9d201ba",
    "tools/Go.txt": "a20fa3ceaeb432caeba39be734d6495ed1f7a27486f9cd53c5f6e8de602258c1",
    "tools/checkpoint_diagnostic.py": "be0628b32f1a49b448f983d4e8b7fc65113cdc7a0c2c4f10036391a344c7ce41",
    "tools/checkpoint_frames.py": "be0628b32f1a49b448f983d4e8b7fc65113cdc7a0c2c4f10036391a344c7ce41",
    "tools/build.py": "309ec87ce0becff7df0d051c7a76923f9514abea8a9e511796a2c13607727883",
    "tools/gate.py": "9c0dbd214824f28ac03b5ed58ff42fec66e04829879d07dd99c645f73c00e414",
    "tools/generate_fixtures.py": "55339cd071eb54dc7214da4c7a62b2a223686ed84e59048d5d817b7a07d73163",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "bootstrap/java/util/Map.java": "8df987e8775bb1c31656bc49e336d5ad3ea6534a398feaa8a396fc81268c620d",
    "bootstrap/java/util/Map$Entry.class.hex": "7b642c3d23dca9a49a44a6fbbee8c3f6d3ae78f5427863e5bd098c2a949521b9",
    "bootstrap/java/util/Map$Entry.sha256": "155b108d5a541239f369b371408830b5cb0dc9e28529c8ba6d924d3faaa90f07",
    "root-commitment.json": "97991182d609e62a4989bf11c1bbedbd4c1f1bbdb490be3666a39d7777b20535",
}
ROOT = "9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622"
MAP_ENTRY_SHA256 = "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5"
INTEGER_SHA256 = "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd"


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


def image_from_function(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    body = text[start:end if end >= 0 else len(text)]
    values = re.findall(r'hex"([0-9a-f]+)"', body)
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(local_text("build-pins.json"))
assert parent_pins["rawLimits"] == [66, 385532]
assert parent_pins["bootstrapCount"] == 95 and parent_pins["diagnosticClassBound"] == 161
assert parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["integer"]["sha256"] == INTEGER_SHA256
assert parent_pins["mapEntry"]["sha256"] == MAP_ENTRY_SHA256
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "classcount66-byte385532-preflight",
    "parentEvidence": "classcount66-byte385532-preflight/{engine,coordinator,tools,bootstrap}",
    "rawLimits": [67, 392193],
    "diagnosticClassBound": 162,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount67-byte392193",
})
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == ROOT and pins["integer"] == parent_pins["integer"]
assert pins["mapEntry"] == parent_pins["mapEntry"]
assert pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

# Full 95-image root and the immutable image95 Map.Entry source/hex remain
# byte-for-byte inherited. Integer/highestOneBit and Map.Entry are extracted
# from the source, never inferred from labels.
assert (stage / "root-commitment.json").read_bytes() == (parent / "root-commitment.json").read_bytes()
for relative in ("bootstrap/java/util/Map.java", "bootstrap/java/util/Map$Entry.class.hex", "bootstrap/java/util/Map$Entry.sha256"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative
parent_engine = parent_text("engine/MCEntryInterpreter.sol")
map_image = image_from_function(parent_engine, "_bootstrapMap")
integer_image = image_from_function(parent_engine, "_bootstrapInteger")
entry_image = image_from_function(parent_engine, "_bootstrapMapEntry")
assert hashlib.sha256(integer_image).hexdigest() == INTEGER_SHA256
assert hashlib.sha256(entry_image).hexdigest() == MAP_ENTRY_SHA256
assert len(re.findall(r"h\[\d+\] = ", parent_engine)) == 95

engine = exact(parent_engine, "MAX_RAW_CLASSES = 66;", "MAX_RAW_CLASSES = 67;")
engine = exact(engine, "MAX_RAW_BYTES = 385532;", "MAX_RAW_BYTES = 392193;")
engine = exact(engine, "uint32(66), uint32(385532)", "uint32(67), uint32(392193)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert image_from_function(engine, "_bootstrapMap") == map_image
assert image_from_function(engine, "_bootstrapInteger") == integer_image
assert image_from_function(engine, "_bootstrapMapEntry") == entry_image

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = exact(coordinator, "[66]", "[67]", 4)
coordinator = exact(coordinator, "n > 66", "n > 67")
coordinator = exact(coordinator, "385532", "392193", 2)
coordinator = exact(coordinator, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coordinator

go = parent_text("tools/Go.txt")
go = exact(go, "len(m.Decoders) > 66", "len(m.Decoders) > 67")
go = exact(go, "len(parts) > 66", "len(parts) > 67")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == go

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=161", "classes<=162")
assert local_text("tools/build.py") == parent_text("tools/build.py").replace("classcount66-byte385532", "classcount67-byte392193")

fixtures = parent_text("tools/generate_fixtures.py").replace("classcount66-byte385532", "classcount67-byte392193")
fixtures = exact(fixtures, '''count_fixture("count-66", 66)
count_fixture("count-67", 67)
count_fixture("count-66-385532", 66, 385532)
count_fixture("count-66-385533", 66, 385533)''', '''count_fixture("count-67", 67)
count_fixture("count-68", 68)
count_fixture("count-67-392193", 67, 392193)
count_fixture("count-67-392194", 67, 392194)''')
fixtures = exact(fixtures, '"rawLimits": [66, 385532]', '"rawLimits": [67, 392193]')
assert local_text("tools/generate_fixtures.py") == fixtures

# The full generated gate retains all focused and retained executable roots. It
# changes only the exact capacity/one-past witness labels and values, including
# the disposable transport/coordinator widening probes.
gate = parent_text("tools/gate.py").replace("classcount66-byte385532", "classcount67-byte392193")
gate = exact(gate, "[66, 385532]", "[67, 392193]", 2)
gate = exact(gate, 'diagnosticClassBound"] == 161', 'diagnosticClassBound"] == 162')
gate = exact(gate, 'diagnosticClassBound": 161', 'diagnosticClassBound": 162')
gate = exact(gate, "<= 385532", "<= 392193")
gate = gate.replace("count-67", "__COUNT68__").replace("count-66", "count-67").replace("__COUNT68__", "count-68")
gate = gate.replace("raw67", "raw68").replace("Raw67", "Raw68")
gate = gate.replace("385533", "392194").replace("385532", "392193")
gate = exact(gate, 'source.count("len(m.Decoders) > 66") == 1 and source.count("len(parts) > 66") == 1', 'source.count("len(m.Decoders) > 67") == 1 and source.count("len(parts) > 67") == 1')
gate = exact(gate, 'source.replace("len(m.Decoders) > 66", "len(m.Decoders) > 67")\n                    .replace("len(parts) > 66", "len(parts) > 67")', 'source.replace("len(m.Decoders) > 67", "len(m.Decoders) > 68")\n                    .replace("len(parts) > 67", "len(parts) > 68")')
gate = exact(gate, 'text.count("[66]") == 4 and text.count("n > 66") == 1', 'text.count("[67]") == 4 and text.count("n > 67") == 1')
gate = exact(gate, 'text.replace("[66]", "[67]").replace("n > 66", "n > 67")', 'text.replace("[67]", "[68]").replace("n > 67", "n > 68")')
gate = exact(gate, 'words(refusal) == ["1", "67"]', 'words(refusal) == ["1", "68"]')
gate = exact(gate, 'row["bindingCount"] == 66', 'row["bindingCount"] == 67')
gate = exact(gate, "MC-RAW66-BYTE392193-P1", "MC-RAW67-BYTE392193-P1")
gate = exact(gate, "Generated-only raw66/392193 q1/q7/direct/reopen capacity gate.", "Generated-only raw67/392193 q1/q7/direct/reopen capacity gate.")
gate = exact(gate, "# Exact raw66 is the capacity focus: q1/q7/direct and terminal reopens agree.", "# Exact raw67 is the capacity focus: q1/q7/direct and terminal reopens agree.")
gate = exact(gate, '''    "limitations": "Only raw capacity advances from raw65/381732/diagnostic160 to raw66/392193/diagnostic161. Bootstrap image95 Map.Entry/root and Integer image/highestOneBit remain byte-identical. The exact raw66 and retained generated Map/Integer focus run q1/q7/direct/reopen; raw68 and 392194 are atomic refusal witnesses. Generated inputs only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine qz replay remains deferred.",''', '''    "limitations": "Only raw capacity advances from raw66/385532/diagnostic161 to raw67/392193/diagnostic162. Bootstrap image95 Map.Entry/root and Integer image/highestOneBit remain byte-identical. The exact raw67 and retained generated Map/Integer focus run q1/q7/direct/reopen; raw68 and 392194 are atomic refusal witnesses. Generated inputs only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine HashBiMap.Inverse replay remains deferred.",''')
assert local_text("tools/gate.py") == gate

for relative in ("engine/build.js", "coordinator/build.js", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR,
    "bootstrapRoot": ROOT, "mapEntry": pins["mapEntry"], "integer": pins["integer"],
    "verification": "literal-capacity-only-source-delta+fixed95-bootstrap-root",
}, indent=2))
