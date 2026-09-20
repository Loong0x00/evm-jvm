#!/usr/bin/env python3
"""Strict generated-only source pins for raw38 / byte285489.

Only the whitelisted generated/runtime source files in parent-0f8778735 and the
accepted generated fixture source are read. No original artifact, JAR, class,
resource, checkpoint, world, or StatusData bytes are opened.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-0f8778735"
fixture_parent = stage.parent / "thread-empty-stack-trace-preflight"
PARENT_DOMAIN = "MC-THREAD-EMPTY-TRACE1"
DOMAIN = "MC-RAW38-BYTE285489-P1"
PARENT_ENGINE = "4d432d5448524541442d54524143452d454e4731"
ENGINE = "4d432d52415733382d4259544532383534383945"
PARENT_OWNER = "4d432d5448524541442d54524143452d4f574e31"
OWNER = "4d432d52415733382d425954453238353438394f"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(text, pairs):
    for old, new, count in pairs:
        assert text.count(old) == count, (old, text.count(old), count)
        text = text.replace(old, new)
    return text


inputs = {
    "artifacts/engine/MCEntryInterpreter.sol": parent / "artifacts/engine/MCEntryInterpreter.sol",
    "artifacts/coordinator/MCEntryCoordinator.sol": parent / "artifacts/coordinator/MCEntryCoordinator.sol",
    "canonical-driver.go.txt": parent / "canonical-driver.go.txt",
    "checkpoint_diagnostic.py": parent / "checkpoint_diagnostic.py",
    "checkpoint_frames.py": parent / "checkpoint_frames.py",
    "verify_receipts.js": parent / "verify_receipts.js",
    "artifacts/engine/build.js": parent / "artifacts/engine/build.js",
    "artifacts/coordinator/build.js": parent / "artifacts/coordinator/build.js",
    "generated_gate.py": parent / "generated_gate.py",
    "pins.json": parent / "pins.json",
    "fixtures/generate_fixtures.py": fixture_parent / "tools/generate_fixtures.py",
}
input_hashes = {name: digest(path) for name, path in inputs.items()}
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "95cc5d977", "parentEvidence": "parent-0f8778735",
    "fixtureBasis": "thread-empty-stack-trace-preflight", "sha256": input_hashes,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == 20
assert len(bytes.fromhex(PARENT_OWNER)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["runtimeBaseline"] == 393185 and parent_pins["engine"]["bytes"] == 393157
assert parent_pins["runtimeCap"] == 393216 and parent_pins["bootstrapCount"] == 91
assert parent_pins["rawLimits"] == [37, 282358] and parent_pins["diagnosticClassBound"] == 128
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14 and parent_pins["maxFrames"] == 128

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
initial_engine = replace_exact(parent_engine, [
    (PARENT_DOMAIN, DOMAIN, 9),
    ("MAX_RAW_CLASSES = 37;", "MAX_RAW_CLASSES = 38;", 1),
    ("MAX_RAW_BYTES = 282358;", "MAX_RAW_BYTES = 285489;", 1),
    ("uint32(37), uint32(282358)", "uint32(38), uint32(285489)", 1),
])
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == initial_engine
for fixed in (
    "MAX_RAW_CLASSES = 38;", "MAX_RAW_BYTES = 285489;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "new bytes32[](91)", "new uint256[](14)",
    "return 13;", "uint32(38), uint32(285489)", "h[90] = DBOOT_STACK_TRACE_ELEMENT;",
):
    assert initial_engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
initial_coordinator = replace_exact(parent_coordinator, [
    (PARENT_DOMAIN, DOMAIN, 4), (PARENT_ENGINE, ENGINE, 1),
    ("[37]", "[38]", 4), ("n > 37", "n > 38", 1), ("282358", "285489", 2),
])
assert initial_coordinator.count("if (size == 0 || size > 285489)") == 1
assert initial_coordinator.count("if (uint256(total) + size > 285489)") == 1

parent_driver = (parent / "canonical-driver.go.txt").read_text()
initial_driver = replace_exact(parent_driver, [
    (PARENT_DOMAIN, DOMAIN, 6), ("0x" + PARENT_ENGINE, "0x" + ENGINE, 1),
    ("0x" + PARENT_OWNER, "0x" + OWNER, 1),
    ("len(m.Decoders) > 37", "len(m.Decoders) > 38", 1),
    ("len(parts) > 37", "len(parts) > 38", 1),
])
assert initial_driver.count("len(m.Decoders) > 38") == initial_driver.count("len(parts) > 38") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == (parent / name).read_text().replace("classes<=128", "classes<=129")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()

fixture_expected = replace_exact((fixture_parent / "tools/generate_fixtures.py").read_text(), [
    ("java-diff-mc-thread-empty-stack-trace-fixtures-", "java-diff-mc-classcount38-byte285489-fixtures-", 1),
    ("# Exact raw37 and aggregate-byte boundaries exercise this measured cap lift.",
     "# Exact raw38 and aggregate-byte boundaries exercise this measured cap lift.", 1),
    ("for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38): count_fixture(\"count-%d\" % count, count)",
     "for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39): count_fixture(\"count-%d\" % count, count)", 1),
    ("count_fixture(\"count-37-282358\", 37, 282358)", "count_fixture(\"count-38-285489\", 38, 285489)", 1),
    ("count_fixture(\"count-37-282359\", 37, 282359)", "count_fixture(\"count-38-285490\", 38, 285490)", 1),
])
assert (stage / "tools/generate_fixtures.py").read_text() == fixture_expected

# Reconstruct the parent gate exactly, replacing only its staging names and the
# one focused raw-capacity block. The retained rows remain byte-for-byte parent code.
def expected_gate():
    text = (parent / "generated_gate.py").read_text()
    text = replace_exact(text, [
        ("root = here.parents[3]", "root = here.parents[4]", 1),
        ("java-diff-mc-thread-empty-parent-gate-", "java-diff-mc-classcount38-byte285489-gate-", 1),
        ("java-diff-mc-thread-empty-parent-", "java-diff-mc-classcount38-byte285489-build-", 1),
        ("java-diff-mc-thread-empty-stack-trace-fixtures-", "java-diff-mc-classcount38-byte285489-fixtures-", 1),
        ('pins["rawLimits"] == [37, 282358]', 'pins["rawLimits"] == [38, 285489]', 1),
        ('pins["diagnosticClassBound"] == 128', 'pins["diagnosticClassBound"] == 129', 1),
        ('head["totalClassBytes"] <= 282358', 'head["totalClassBytes"] <= 285489', 1),
    ])
    begin = text.index("# Exact raw37 is the focused capacity witness:")
    end = text.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", begin)
    block = text[begin:end]
    block = replace_exact(block, [
        ("len(m.Decoders) > 38", "len(m.Decoders) > 39", 1),
        ("len(parts) > 38", "len(parts) > 39", 1),
        ("len(m.Decoders) > 37", "len(m.Decoders) > 38", 2),
        ("len(parts) > 37", "len(parts) > 38", 2),
        ('text.count("[37]") == 4 and text.count("n > 37") == 1',
         'text.count("[38]") == 4 and text.count("n > 38") == 1', 1),
        ('text.replace("[37]", "[38]").replace("n > 37", "n > 38")',
         'text.replace("[38]", "[39]").replace("n > 38", "n > 39")', 1),
        ("Raw38", "Raw39", 1), ("raw38", "raw39", 13), ("raw37", "raw38", 2),
        ("282359", "285490", 8), ("282358", "285489", 8),
        ("count-38", "count-39", 6), ("count-37", "count-38", 7),
        ('spec["bindingCount"] == 37', 'spec["bindingCount"] == 38', 1),
        ('["1", "38"]', '["1", "39"]', 1),
    ])
    old = '''summary = {"profile": "MC-THREAD-EMPTY-TRACE1-P", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only bootstrap image50 java/lang/Thread and appended image90 java/lang/StackTraceElement change semantically. getStackTrace allocates a fresh non-null empty StackTraceElement[]; it exposes no frame capture, element construction or StackTraceElement API. The root remains runtime-derived as keccak256(abi.encode(DBOOT, h)) over 91 exact ordered image hashes. The ThreadLocal root leaf is an exact verified static hash and two unused interpreter parameters are removed only as layout recovery; no root, cap, error precedence or execution path is weakened. Raw37/282358, diagnostic128, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new = '''summary = {"profile": "MC-RAW38-BYTE285489-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted 91-image stage: 37 to 38, aggregate raw bytes 282358 to 285489, and read-only checkpoint diagnostic class bound 128 to 129. The 91 ordered bootstrap images, runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, Provider construction, factory, world, or Done input or claim. Parent alone appends/runs genuine StatusData with accelerated replay."}'''
    assert text.count(old) == 1
    return (text[:begin] + block + text[end:]).replace(old, new)

assert (stage / "tools/gate.py").read_text() == expected_gate()

# The 91-image root remains computed from the actual source-image order, never
# embedded as a root literal. Recompute the ABI-word sequence with pinned local
# js-sha3, using only public generated image/root evidence.
root_record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((fixture_parent / "root-commitment.json").read_text())
assert root_record["domain"] == DOMAIN and root_record["bootstrapCount"] == 91
assert root_record["order"] == base_root["order"] and root_record["keccak256"] == base_root["keccak256"]
assert "return keccak256(abi.encode(DBOOT, h));" in initial_engine
assert root_record["bootstrapRoot"] not in initial_engine
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
program = r'''const fs=require("fs"),{keccak256}=require("js-sha3"); const x=JSON.parse(fs.readFileSync(0,"utf8")); const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b}; const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1")); const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.keccak256.length),...x.keccak256.map(v=>Buffer.from(v,"hex"))])); process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
computed = json.loads(subprocess.run(["node", "-e", program], input=json.dumps(root_record), text=True,
    capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert computed == {"dboot": root_record["dboot"], "bootstrapRoot": root_record["bootstrapRoot"]}

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coordinator
    assert (stage / "tools/Go.txt").read_text() == initial_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected = {
        "basis": "95cc5d977", "parentEvidence": "parent-0f8778735", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393157, "runtimeCap": 393216,
        "bootstrapCount": 91, "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [38, 285489], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 129, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected and pins["engine"]["bytes"] == 393157 <= 393216
    assert pins["coordinator"]["bytes"] == 5394
    final_coordinator = initial_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == final_coordinator
    final_driver = initial_driver
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert final_driver.count(old) == 1
        final_driver = final_driver.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        final_driver, changed = re.subn(pattern, replacement, final_driver)
        assert changed == 1
    assert (stage / "tools/Go.txt").read_text() == final_driver
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-0f8778735", "fixtureBasis": "thread-empty-stack-trace-preflight",
    "phase": phase, "domain": DOMAIN, "bootstrapImages": 91,
    "bootstrapRoot": root_record["bootstrapRoot"], "rawLimits": [38, 285489],
    "diagnosticClassBound": 129, "runtimeBaseline": 393157, "runtimeCap": 393216,
    "globalNativeBindings": 13, "maxFrames": 128, "checkpointCap": 1048576,
    "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
