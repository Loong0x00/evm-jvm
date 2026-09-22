#!/usr/bin/env python3
"""Verify raw63/377990 is an exact capacity-only delta from parent-ddca01a33."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-ddca01a33"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

ENGINE = {
    "bytes": 377409,
    "initSHA256": "063bcfbe67e67ed60d5bc30a7c92c7212aff4c9d89c94e736d80ff31a2cb4ec0",
    "runtimeSHA256": "5dc001b2c94af42f449ad57ead8737e0465a441b014fa1495783aed9e248fe13",
    "runtimeKeccak256": "d78378536fccabe87a283d86cf0a3a84fe841fb6d297eca18c7f1434b9287069",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "6a4dade16407d539ac905b60d1ee6ee88e0a69f302e2fc7fd89cb5977e591f51",
    "runtimeSHA256": "1ac2e0b5b6079ceccc3eafcfe0bc77ed1bdcef3602f9e5db85ec39432174a48f",
    "runtimeKeccak256": "a176aacd525305d812f3221c59eacf26748f713f73572941db9925b966780c08",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "7fd3ccca368e2ac81f9a343db69a48b336ae2911af6c027bc9db73edbf496e9f",
    "artifacts/coordinator/MCEntryCoordinator.sol": "d54a62265c2abafd1c58ca344e3707c35f2c600b4fa2a3d906d49078a691c7be",
    "canonical-driver.go.txt": "2e983177769ac489dfa5066107c38689c7c63931a4a66e9cc97aa0a3bafc4778",
    "checkpoint_diagnostic.py": "076cefca981bb4b45f807aca02bdde93d3fda4b2f9d9c1efd5ada8ccaf7abc30",
    "checkpoint_frames.py": "076cefca981bb4b45f807aca02bdde93d3fda4b2f9d9c1efd5ada8ccaf7abc30",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "987877d296c0c514ec0e36319c2678a6409058cece9da50dd7b4de420ae6cac5",
    "bootstrap/java/lang/Integer.class.hex": "af99a59dbf1738d41ffce50c5618e3dff5280f96f9caa1a69ee735f31ee60c04",
}
STAGE_SHA256 = {
    "tools/build.py": "7171d6b86507ad3d62df587f675843334f59bcedc1d8490042870955a5aa3117",
    "tools/gate.py": "17761643c83379f455eea58eb75fb6e620c10e1e3efe83f322ee0102e7b795d1",
    "tools/generate_retained_fixtures.py": "8bb0252cbb3ecc3d0983bf688eafaef70734661fe6ede400fbd077794b76465a",
    "tools/generate_focused_fixtures.py": "1282aedb3aeeb98fba44e4ecf73ce5ae81dd78640c1d1fa96352075f56356d40",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
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
for relative, expected in STAGE_SHA256.items():
    assert sha(stage / relative) == expected, relative

parent_pins = json.loads(parent_text("pins.json"))
pins = json.loads(local_text("build-pins.json"))
assert parent_pins["rawLimits"] == [62, 376794]
assert parent_pins["diagnosticClassBound"] == 156
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
    "basis": "ddca01a33",
    "parentEvidence": "parent-ddca01a33/artifacts/{engine,coordinator}/MCEntry*.sol",
    "rawLimits": [63, 377990],
    "diagnosticClassBound": 157,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount63-byte377990",
})
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["bootstrapRoot"] == parent_pins["bootstrapRoot"]
assert pins["integer"] == parent_pins["integer"]

# The newly accepted Integer bytes and bootstrap root are not recompiled or
# regenerated here.  The capacity source is reconstructed from the parent, so
# its complete ordered 94-leaf bootstrap program is byte-for-byte unchanged.
integer_hex = (parent / "bootstrap/java/lang/Integer.class.hex").read_text().strip()
integer_image = bytes.fromhex(integer_hex)
assert len(integer_image) == pins["integer"]["bytes"]
assert hashlib.sha256(integer_image).hexdigest() == pins["integer"]["sha256"]
parent_engine = parent_text("artifacts/engine/MCEntryInterpreter.sol")
match = re.search(r"function _bootstrapInteger\(\).*?return hex\"([0-9a-f]+)\";", parent_engine, re.S)
assert match and bytes.fromhex(match.group(1)) == integer_image
assert len(re.findall(r"h\[\d+\] = ", parent_engine)) == 94

engine = exact(parent_engine, "MAX_RAW_CLASSES = 62;", "MAX_RAW_CLASSES = 63;")
engine = exact(engine, "MAX_RAW_BYTES = 376794;", "MAX_RAW_BYTES = 377990;")
engine = exact(engine, "uint32(62), uint32(376794)", "uint32(63), uint32(377990)")
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert match.group(1) in engine

coord = parent_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = exact(coord, "[62]", "[63]", 4)
coord = exact(coord, "n > 62", "n > 63")
coord = exact(coord, "376794", "377990", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coord

source = parent_text("canonical-driver.go.txt")
source = exact(source, "len(m.Decoders) > 62", "len(m.Decoders) > 63")
source = exact(source, "len(parts) > 62", "len(parts) > 63")
source = exact(source, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
source = exact(source, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
source = exact(source, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert local_text("tools/Go.txt") == source

for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text(relative), "classes<=156", "classes<=157")
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR,
    "bootstrapRoot": pins["bootstrapRoot"], "integer": pins["integer"],
    "verification": "literal-capacity-only-source-delta",
}, indent=2))
