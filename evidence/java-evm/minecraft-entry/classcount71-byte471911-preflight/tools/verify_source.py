#!/usr/bin/env python3
"""Verify the literal raw71 / byte471911 capacity delta from identity-hash.

Only checked-in stage sources and pinned local Node modules are read. No
original/JAR/external class/resource/network input is opened or evaluated.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "system-identity-hash-code-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "build-pins.json": "1d23c76a677312fa8f457a665b6afb93a982f7bc344dab02faa15b9933a7651c",
    "root-commitment.json": "115af8050356c9f0cf69ab14bf65303892dc904b5af40655f1c7bc9b2f42878c",
    "engine/MCEntryInterpreter.sol": "bbe088c9ad87c9714017204ad5943ee1fa764d0034e329b27baf0e5539aef2a1",
    "coordinator/MCEntryCoordinator.sol": "a4809dd4c679784f72204c339cffc071b0689505a7235303a0d688a68d1aae4a",
    "tools/Go.txt": "82d6dc58f6b6b7256599f1b266aae3f64134708d966b2607a9c17c9d497d1758",
    "tools/checkpoint_diagnostic.py": "9d58e3f73d1fc4ce8d57dbeb2f6e2f90c6faaa4eb56f0315eb4362f48b5bdc0e",
    "tools/checkpoint_frames.py": "b27ca60b02227bb00f4c2c4cc78000c17f223fd0af4eeb48c5627725acdea071",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "bootstrap/java/io/PrintStream.java": "8294f200b3de4b27de6198eed2fabc3977df3c0da3556418ea42fcdd68ce2093",
    "bootstrap/java/lang/String.class.hex": "69cad4f5531e62ca260b7b0c068609a2af58d683ab6169e236368f06fbdd0b7b",
    "bootstrap/java/lang/String.java": "3f7d9e35a8a10949d34dcea78f5a4e3cb5a5b4255b2aadd764fb98e01cf64077",
    "bootstrap/java/lang/String.sha256": "cf524b12441bc6a31e3f827418d770b963196545f796ae8a10fa4ac957e2c1c8",
    "bootstrap/java/lang/System.class.hex": "d9da74f0882a63f124833f46abdc454ba0952062a6ffa88439dd6fa8523a7555",
    "bootstrap/java/lang/System.java": "fc160d58dbc1cfe85da30e32d1cfd196b8e327a19fe721f9c0748a16319b8215",
    "bootstrap/java/lang/System.sha256": "a6fa69bbb952dba6481f57a0bd6d1fb220756bb0f457ca37342db0a0c2877425",
    "bootstrap/java/util/Locale.class.hex": "16660fe0ab426c6caaa8e400550e9eb1ebe4aec0b387195749d6ce263f0d5ab8",
    "bootstrap/java/util/Locale.java": "6558483205b92fcc43fe7e0f748198b0019ad18cbf0c950f9ec602e7e97a6375",
    "bootstrap/java/util/Locale.sha256": "871b1720b5e2383c5a2a0b7c29246a46f61effc71c0678664ad3e13968631be9",
}
ENGINE = {
    "bytes": 380017,
    "initSHA256": "3e8d5ea019df898b2d122d7a6f2defaef27a1b5f6556915a87f2386f9c381051",
    "runtimeSHA256": "b7bca42e9f7c8ba63a3ca1ace3a52b6364008fb1207c3cc09181783ee68af5ce",
    "runtimeKeccak256": "01219b54112c6271aa91bd85ac8b26645f39cf866ca38e906e2becb76d857f4e",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "ac9a14c3ad1cfce5ea8be90b6833e538c425c76f41bf467d62c58e2129836e23",
    "runtimeSHA256": "a2410292b70affd987b23e2ba58b78d8ab27e98b8370564c89b421a81293e13f",
    "runtimeKeccak256": "defc9c766c8fbf84fef162a142fa3ffd1215e76b19ab086150bcf24a9d555a0f",
}
ROOT = "6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    actual = text.count(old)
    assert actual == count, (old, actual, count)
    return text.replace(old, new)


def function_image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def leaves(text):
    body = text[text.index("function _bootstrapRoot"):text.index("function _prepare")]
    assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', body)
    assert len(assignments) == 96 and [int(index) for index, _, _ in assignments] == list(range(96))
    values = []
    for _, function, constant in assignments:
        if function:
            values.append({"image": function_image(text, function).hex()})
        else:
            at = text.index("bytes32 private constant " + constant)
            declaration = text[at:text.index(";", at)]
            folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration)
            literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
            assert folded or literal, constant
            values.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
    return values


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
parent_pins = json.loads((parent / "build-pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
assert parent_pins["rawLimits"] == [70, 464925]
assert parent_pins["diagnosticClassBound"] == 166
assert parent_pins["bootstrapCount"] == 96 and parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["globalNativeBindings"] == 17 and parent_pins["stringLocalBinding"] == 12
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "system-identity-hash-code-preflight",
    "parentEvidence": "system-identity-hash-code-preflight/{engine,coordinator,tools,build-pins,root-commitment}",
    "rawLimits": [71, 471911], "diagnosticClassBound": 167,
    "engine": ENGINE, "coordinator": COORDINATOR, "worker": "classcount71-byte471911",
})
assert pins == expected_pins
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["system"]["sha256"] == "6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564"

# The engine literal delta is three capacity values and the constructor tuple,
# no bootstrap image, DBOOT domain, native dispatch, opcode, or other quota.
parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
engine = exact(parent_engine, "MAX_RAW_CLASSES = 70;", "MAX_RAW_CLASSES = 71;")
engine = exact(engine, "MAX_RAW_BYTES = 464925;", "MAX_RAW_BYTES = 471911;")
engine = exact(engine, "uint32(70), uint32(464925)", "uint32(71), uint32(471911)")
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == engine
for fixed in ("MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "new bytes32[](96)", "new uint256[](14)"):
    assert engine.count(fixed) == 1, fixed
assert hashlib.sha256(function_image(engine, "_bootstrapSystem")).hexdigest() == pins["system"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapString")).hexdigest() == pins["string"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapLocale")).hexdigest() == pins["locale"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapMapEntry")).hexdigest() == pins["mapEntry"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapInteger")).hexdigest() == pins["integer"]["sha256"]

# Re-fold the fixed 96 leaves independently. Since DBOOT and every image are
# exact parent bytes, this must keep the canonical bootstrap root unchanged.
assert (stage / "root-commitment.json").read_bytes() == (parent / "root-commitment.json").read_bytes()
record = json.loads((stage / "root-commitment.json").read_text())
assert record["bootstrapCount"] == 96 and record["bootstrapRoot"] == ROOT
assert leaves(parent_engine) == leaves(engine)
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = 'const{keccak256}=require("js-sha3");const p=JSON.parse(process.argv[1]),w=x=>x.padStart(64,"0"),h=p.l.map(x=>x.image?keccak256(Buffer.from(x.image,"hex")):x.hash),r=keccak256(Buffer.from(w(p.d)+w("40")+w(h.length.toString(16))+h.map(w).join(""),"hex"));console.log(JSON.stringify({keccak256:h,bootstrapRoot:r}));'
folded = json.loads(subprocess.check_output(["node", "-e", node, json.dumps({"d": record["dboot"], "l": leaves(engine)})], cwd=root, env={**os.environ, "NODE_PATH": str(node_modules)}, text=True))
assert folded["keccak256"] == record["keccak256"] and folded["bootstrapRoot"] == ROOT

# Coordinator and product driver receive exactly fixed capacity guards plus the
# code identities rebuilt from the changed engine/coordinator bytecode.
parent_coord = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, "[70]", "[71]", 4)
coord = exact(coord, "n > 70", "n > 71")
coord = exact(coord, "464925", "471911", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord
parent_go = (parent / "tools/Go.txt").read_text()
go = exact(parent_go, "len(m.Decoders) > 70", "len(m.Decoders) > 71")
go = exact(go, "len(parts) > 70", "len(parts) > 71")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert (stage / "tools/Go.txt").read_text() == go
for name in ("engine/build.js", "coordinator/build.js"):
    assert (stage / name).read_bytes() == (parent / name).read_bytes(), name
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == exact((parent / "tools" / name).read_text(), "classes<=166", "classes<=167")
for relative in PARENT_SHA256:
    if relative.startswith("bootstrap/"):
        assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative

fixtures = (stage / "tools/generate_fixtures.py").read_text()
for fragment in ('count_fixture("count-71", 71)', 'count_fixture("count-72", 72)',
                 'count_fixture("count-71-471911", 71, 471911)',
                 'count_fixture("count-71-471912", 71, 471912)', '"rawLimits": [71, 471911]'):
    assert fragment in fixtures, fragment
gate = (stage / "tools/gate.py").read_text()
for fragment in ('[71, 471911]', 'diagnosticClassBound"] == 167', 'q_equivalent("count-71")',
                 '"count-72.zip"', 'count-71-471911', 'count-71-471912', '["1", "72"]'):
    assert fragment in gate, fragment
assert "<= 1200" in gate and 'actualDI0ReadSizes"]) == 471911' in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"], "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR, "bootstrapRoot": ROOT,
    "systemSHA256": pins["system"]["sha256"], "stringSHA256": pins["string"]["sha256"],
    "globalNativeBindings": pins["globalNativeBindings"], "stringLocalBinding": pins["stringLocalBinding"],
    "verification": "literal-capacity-only-source-delta+independent-fixed-96-leaf-root+generated-input-only",
}, indent=2))
