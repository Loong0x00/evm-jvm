#!/usr/bin/env python3
"""Verify raw68/394767 is a literal capacity-only delta from raw67/392193."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount67-byte392193-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 376562,
    "initSHA256": "18aa0fe507b70f20d3aa9ae30a4e78fbfc3fcdf8c1c797c78b9719f20fd0e40c",
    "runtimeSHA256": "1173f94dae8f4ae3cef34e292b3313636209c6fa025671e2d5aa0687ec5147a1",
    "runtimeKeccak256": "6642fb544be67a9d1be0001c8388c6285b8cb2b710d2e4b732e87b95e537e170"
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "421d039f105496ef0789813133eb7f978cd7de318a575d4924ba2059c23e6fb4",
    "runtimeSHA256": "e9664cd94446c9fe152f3326de27d86e44757c4e7dbe6457b5a0dce58dddcf1a",
    "runtimeKeccak256": "07b51d1a374bdcf35f8d5ea30323667cf1041b37f820dd24cccc81aeb95bb0a2"
}
PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "a785ac530f5f00d0b8186cfd8d300f596b9a06183d81661ab02b0e19569773e7",
    "coordinator/MCEntryCoordinator.sol": "88739c3788d94792ce7f092134158475b958d458aa3e0fce8539f26e34d82b41",
    "tools/Go.txt": "b310c21fb6f4c77df00cd3e3a0ec42a098c478ebf0277e1173db5711d5719c78",
    "tools/checkpoint_diagnostic.py": "b94f31e29ca63271a94396995361c5c05ccd48ea308bd3462162bf905128d853",
    "tools/checkpoint_frames.py": "b94f31e29ca63271a94396995361c5c05ccd48ea308bd3462162bf905128d853",
    "tools/build.py": "da8ffb1d51fdc9efd87b6c00864c6b70cdf513840976f9f94fd881e20bb10738",
    "tools/gate.py": "f9a331e616c099cb8c5672f546e5f9ccb78286ad611c87f600b69e71ed913f44",
    "tools/generate_fixtures.py": "61a806a8d3a182498e91b96c127247e04e11fd2f58b82d1328ec207e515489d3",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "bootstrap/java/util/Map.java": "8df987e8775bb1c31656bc49e336d5ad3ea6534a398feaa8a396fc81268c620d",
    "bootstrap/java/util/Map$Entry.class.hex": "7b642c3d23dca9a49a44a6fbbee8c3f6d3ae78f5427863e5bd098c2a949521b9",
    "bootstrap/java/util/Map$Entry.sha256": "155b108d5a541239f369b371408830b5cb0dc9e28529c8ba6d924d3faaa90f07",
    "root-commitment.json": "97991182d609e62a4989bf11c1bbedbd4c1f1bbdb490be3666a39d7777b20535"
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
assert parent_pins["rawLimits"] == [67, 392193]
assert parent_pins["bootstrapCount"] == 95 and parent_pins["diagnosticClassBound"] == 162
assert parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["integer"]["sha256"] == INTEGER_SHA256
assert parent_pins["mapEntry"]["sha256"] == MAP_ENTRY_SHA256
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "classcount67-byte392193-preflight",
    "parentEvidence": "classcount67-byte392193-preflight/{engine,coordinator,tools,bootstrap}",
    "rawLimits": [68, 394767],
    "diagnosticClassBound": 163,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount68-byte394767",
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

engine = exact(parent_engine, "MAX_RAW_CLASSES = 67;", "MAX_RAW_CLASSES = 68;")
engine = exact(engine, "MAX_RAW_BYTES = 392193;", "MAX_RAW_BYTES = 394767;")
engine = exact(engine, "uint32(67), uint32(392193)", "uint32(68), uint32(394767)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert image_from_function(engine, "_bootstrapMap") == map_image
assert image_from_function(engine, "_bootstrapInteger") == integer_image
assert image_from_function(engine, "_bootstrapMapEntry") == entry_image

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = exact(coordinator, "[67]", "[68]", 4)
coordinator = exact(coordinator, "n > 67", "n > 68")
coordinator = exact(coordinator, "392193", "394767", 2)
coordinator = exact(coordinator, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coordinator

go = parent_text("tools/Go.txt")
go = exact(go, "len(m.Decoders) > 67", "len(m.Decoders) > 68")
go = exact(go, "len(parts) > 67", "len(parts) > 68")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == go

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=162", "classes<=163")
assert local_text("tools/build.py") == parent_text("tools/build.py").replace("classcount67-byte392193", "classcount68-byte394767")

fixtures = parent_text("tools/generate_fixtures.py").replace("classcount67-byte392193", "classcount68-byte394767")
fixtures = exact(fixtures, '''count_fixture("count-67", 67)
count_fixture("count-68", 68)
count_fixture("count-67-392193", 67, 392193)
count_fixture("count-67-392194", 67, 392194)''', '''count_fixture("count-68", 68)
count_fixture("count-69", 69)
count_fixture("count-68-394767", 68, 394767)
count_fixture("count-68-394768", 68, 394768)''')
fixtures = exact(fixtures, '"rawLimits": [67, 392193]', '"rawLimits": [68, 394767]')
assert local_text("tools/generate_fixtures.py") == fixtures

# The full generated gate retains all focused and retained executable roots. It
# changes only exact capacity/one-past witness labels and values, including
# disposable transport/coordinator widening probes.
gate = parent_text("tools/gate.py").replace("classcount67-byte392193", "classcount68-byte394767")
gate = exact(gate, "[67, 392193]", "[68, 394767]", 2)
gate = exact(gate, 'diagnosticClassBound"] == 162', 'diagnosticClassBound"] == 163')
gate = exact(gate, 'diagnosticClassBound": 162', 'diagnosticClassBound": 163')
gate = exact(gate, "<= 392193", "<= 394767")
gate = gate.replace("count-68", "__COUNT69__").replace("count-67", "count-68").replace("__COUNT69__", "count-69")
gate = gate.replace("raw68", "raw69").replace("Raw68", "Raw69")
gate = gate.replace("392194", "394768").replace("392193", "394767")
gate = exact(gate, 'source.count("len(m.Decoders) > 67") == 1 and source.count("len(parts) > 67") == 1', 'source.count("len(m.Decoders) > 68") == 1 and source.count("len(parts) > 68") == 1')
gate = exact(gate, 'source.replace("len(m.Decoders) > 67", "len(m.Decoders) > 68")\n                    .replace("len(parts) > 67", "len(parts) > 68")', 'source.replace("len(m.Decoders) > 68", "len(m.Decoders) > 69")\n                    .replace("len(parts) > 68", "len(parts) > 69")')
gate = exact(gate, 'text.count("[67]") == 4 and text.count("n > 67") == 1', 'text.count("[68]") == 4 and text.count("n > 68") == 1')
gate = exact(gate, 'text.replace("[67]", "[68]").replace("n > 67", "n > 68")', 'text.replace("[68]", "[69]").replace("n > 68", "n > 69")')
gate = exact(gate, 'words(refusal) == ["1", "68"]', 'words(refusal) == ["1", "69"]')
gate = exact(gate, 'row["bindingCount"] == 67', 'row["bindingCount"] == 68')
gate = exact(gate, "MC-RAW67-BYTE394767-P1", "MC-RAW68-BYTE394767-P1")
gate = exact(gate, "Generated-only raw67/394767 q1/q7/direct/reopen capacity gate.", "Generated-only raw68/394767 q1/q7/direct/reopen capacity gate.")
gate = exact(gate, "# Exact raw67 is the capacity focus: q1/q7/direct and terminal reopens agree.", "# Exact raw68 is the capacity focus: q1/q7/direct and terminal reopens agree.")
gate = exact(gate, '''    "limitations": "Only raw capacity advances from raw66/385532/diagnostic161 to raw67/394767/diagnostic162. Bootstrap image95 Map.Entry/root and Integer image/highestOneBit remain byte-identical. The exact raw67 and retained generated Map/Integer focus run q1/q7/direct/reopen; raw69 and 394768 are atomic refusal witnesses. Generated inputs only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine HashBiMap.Inverse replay remains deferred.",''', '''    "limitations": "Only raw capacity advances from raw67/392193/diagnostic162 to raw68/394767/diagnostic163. Bootstrap image95 Map.Entry/root and Integer image/highestOneBit remain byte-identical. The exact raw68 and retained generated Map/Integer focus run q1/q7/direct/reopen; raw69 and 394768 are atomic refusal witnesses. Generated inputs only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine nf.class replay remains deferred.",''')
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
