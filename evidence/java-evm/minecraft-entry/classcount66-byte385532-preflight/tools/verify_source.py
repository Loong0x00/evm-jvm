#!/usr/bin/env python3
"""Verify raw66/385532 is a literal capacity-only delta from Map.Entry P1."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "map-entry-link-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 376562,
    "initSHA256": "97460d64b9c253ce4ca947e3a1af0d99d50df8d8b655c9f3ddbe782f99809e02",
    "runtimeSHA256": "8de39f100a5707c46288ff79ad9fb860daa4e9a96e4c188ab8361ff0e8661431",
    "runtimeKeccak256": "1871e2779eb5ffd554c3157cfabfc24ea3864c777a086d102b7a1e4db0486030",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "4939b64ea487541a55725ccf00d3e6e403e566ee138e70490844b889f866b8d9",
    "runtimeSHA256": "05617b4b36ec2c637bb27b87309ecce7defffa35c2fd6cb7233991dc59ff76ae",
    "runtimeKeccak256": "7caf404024a72f477941a70d2147373f38559dff7e750b21434883528b771819",
}
PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "e0495c8682a2d462cadba147bdc62fc51b277c21e468eb3d8dc82fddb68ad501",
    "coordinator/MCEntryCoordinator.sol": "7203afa672cf9946a6a84306bf4f735e6e5da7f1844a73dbc866bc491accd2d0",
    "tools/Go.txt": "18e4feea13a00379ebde8cc9e8a873e48d1648954830459231752388c31beb30",
    "tools/checkpoint_diagnostic.py": "c0eb96dbf43dc4412de48773f660f8019ebd5abee4c78055127791abfc654e2c",
    "tools/checkpoint_frames.py": "c0eb96dbf43dc4412de48773f660f8019ebd5abee4c78055127791abfc654e2c",
    "tools/build.py": "0e85d206f471172a29b433fb20e4e0f00eab6e488b0edd767a0701e2e399b65e",
    "tools/gate.py": "3c4f09c5998846f56218784e794ce666b6c6348a82dfe5749cfc5965761ddada",
    "tools/generate_fixtures.py": "b9d837f6c4c8ee7f6c770c0d68173aaa1c1a00a73fadd1bbbf227710f1b3dde6",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "bootstrap/java/util/Map.java": "8df987e8775bb1c31656bc49e336d5ad3ea6534a398feaa8a396fc81268c620d",
    "bootstrap/java/util/Map$Entry.class.hex": "7b642c3d23dca9a49a44a6fbbee8c3f6d3ae78f5427863e5bd098c2a949521b9",
    "bootstrap/java/util/Map$Entry.sha256": "155b108d5a541239f369b371408830b5cb0dc9e28529c8ba6d924d3faaa90f07",
    "root-commitment.json": "97991182d609e62a4989bf11c1bbedbd4c1f1bbdb490be3666a39d7777b20535",
}
GATE_SHA256 = "9c0dbd214824f28ac03b5ed58ff42fec66e04829879d07dd99c645f73c00e414"
FIXTURE_SHA256 = "55339cd071eb54dc7214da4c7a62b2a223686ed84e59048d5d817b7a07d73163"
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
assert parent_pins["rawLimits"] == [65, 381732]
assert parent_pins["bootstrapCount"] == 95 and parent_pins["diagnosticClassBound"] == 160
assert parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["integer"]["sha256"] == INTEGER_SHA256
assert parent_pins["mapEntry"]["sha256"] == MAP_ENTRY_SHA256
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "map-entry-link-preflight",
    "parentEvidence": "map-entry-link-preflight/{engine,coordinator,tools,bootstrap}",
    "rawLimits": [66, 385532],
    "diagnosticClassBound": 161,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount66-byte385532",
})
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == ROOT and pins["integer"] == parent_pins["integer"]
assert pins["mapEntry"] == parent_pins["mapEntry"]
assert pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]

# The full 95-image root commitment and its Java-8 Map.Entry source/hex are
# inherited byte-for-byte. Integer/highestOneBit and the existing Map image are
# extracted from the actual source rather than inferred from a label.
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

engine = exact(parent_engine, "MAX_RAW_CLASSES = 65;", "MAX_RAW_CLASSES = 66;")
engine = exact(engine, "MAX_RAW_BYTES = 381732;", "MAX_RAW_BYTES = 385532;")
engine = exact(engine, "uint32(65), uint32(381732)", "uint32(66), uint32(385532)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert image_from_function(engine, "_bootstrapMap") == map_image
assert image_from_function(engine, "_bootstrapInteger") == integer_image
assert image_from_function(engine, "_bootstrapMapEntry") == entry_image

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = exact(coordinator, "[65]", "[66]", 4)
coordinator = exact(coordinator, "n > 65", "n > 66")
coordinator = exact(coordinator, "381732", "385532", 2)
coordinator = exact(coordinator, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coordinator

go = parent_text("tools/Go.txt")
go = exact(go, "len(m.Decoders) > 65", "len(m.Decoders) > 66")
go = exact(go, "len(parts) > 65", "len(parts) > 66")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == go

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=160", "classes<=161")
assert local_text("tools/build.py") == parent_text("tools/build.py").replace("map-entry-link", "classcount66-byte385532")
for relative in ("engine/build.js", "coordinator/build.js", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative

# The test-only changes are themselves pinned source files. They add only
# generated CountMain/Tail capacity inputs and three-layer 66/67 plus exact-byte
# witnesses; the retained Map.Entry and Integer roots stay in the full matrix.
gate = local_text("tools/gate.py")
fixtures = local_text("tools/generate_fixtures.py")
assert sha(stage / "tools/gate.py") == GATE_SHA256
assert sha(stage / "tools/generate_fixtures.py") == FIXTURE_SHA256
for token in (
    "[66, 385532]", "diagnosticClassBound\": 161", "q_equivalent(\"count-66\")",
    "raw67-driver", "raw67-coordinator", "raw67-engine", "count-66-385532",
    "count-66-385533", "MC-RAW66-BYTE385532-P1", "Parent genuine qz replay remains deferred",
):
    assert token in gate, token
for token in (
    "count_fixture(\"count-66\", 66)", "count_fixture(\"count-67\", 67)",
    "count_fixture(\"count-66-385532\", 66, 385532)",
    "count_fixture(\"count-66-385533\", 66, 385533)", "bootstrapCount\": 95",
):
    assert token in fixtures, token
assert "original" in fixtures and "count-66-385532" in fixtures
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR,
    "bootstrapRoot": ROOT, "mapEntry": pins["mapEntry"], "integer": pins["integer"],
    "verification": "literal-capacity-only-source-delta+fixed95-bootstrap-root",
}, indent=2))
