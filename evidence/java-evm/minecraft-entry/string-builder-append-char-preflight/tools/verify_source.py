#!/usr/bin/env python3
"""Strict generated-only source/commitment verifier for append(char).

It reads only the accepted generated monitor stage and this stage's generated
bootstrap source. It never opens an original artifact, JAR, class input,
resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "monitor-enter-exit-preflight"
PARENT_DOMAIN = "MC-MONITOR-ENTER-EXIT1"
DOMAIN = "MC-SB-APPEND-CHAR-0001"
PARENT_ENGINE = "4d432d4d4f4e49544f522d454e5445522d455831"
ENGINE = "4d432d53422d415050454e442d434841522d3031"
PARENT_OWNER = "4d432d4d4f4e49544f522d454e5445522d455830"
OWNER = "4d432d53422d415050454e442d434841522d3032"
STRING_BUILDER_SHA256 = "7f2e95a40c6ec353b603368e0a2609a2e0baa7cf84f7d65b7d4865daf6792270"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


inputs_paths = {
    "engine/MCEntryInterpreter.sol": parent / "engine/MCEntryInterpreter.sol",
    "coordinator/MCEntryCoordinator.sol": parent / "coordinator/MCEntryCoordinator.sol",
    "tools/Go.txt": parent / "tools/Go.txt",
    "tools/checkpoint_diagnostic.py": parent / "tools/checkpoint_diagnostic.py",
    "tools/checkpoint_frames.py": parent / "tools/checkpoint_frames.py",
    "tools/verify_receipts.js": parent / "tools/verify_receipts.js",
    "engine/build.js": parent / "engine/build.js",
    "coordinator/build.js": parent / "coordinator/build.js",
    "build-pins.json": parent / "build-pins.json",
    "tools/gate.py": parent / "tools/gate.py",
    "tools/generate_fixtures.py": parent / "tools/generate_fixtures.py",
    "root-commitment.json": parent / "root-commitment.json",
}
input_hashes = {name: digest(path) for name, path in inputs_paths.items()}
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "868c7d1b8", "parentEvidence": "monitor-enter-exit-preflight",
    "fixtureBasis": "monitor-enter-exit-preflight", "sha256": input_hashes,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == 20
assert len(bytes.fromhex(PARENT_OWNER)) == len(bytes.fromhex(OWNER)) == 20

# Image84 is derived reproducibly from trusted stage source. The cleanup strips
# only four Code-local StackMapTable attributes which this EVM parser never
# reads; method Code, exception tables, field data, and CP contents stay exact.
source = stage / "bootstrap/java/lang/StringBuilder.java"
assert digest(source) == "befb130a6a9f08c1473d44e19a8655cbe6bdd7f0c8c117d0efbc42867fe8d1de"
source_text = source.read_text()
assert source_text.count("public StringBuilder append(char input)") == 1
assert source_text.count("return append(new String(new char[] { input }));") == 1
assert source_text.count("public StringBuilder append(String input)") == 1
assert source_text.count("public StringBuilder append(CharSequence input, int start, int end)") == 1
assert source_text.count("public StringBuilder append(") == 3
assert source_text.count("public String toString()") == 1 and source_text.count("public void setLength(int length)") == 1
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
strip_spec = importlib.util.spec_from_file_location("strip_stackmap", here / "strip_stackmap.py")
strip_module = importlib.util.module_from_spec(strip_spec)
strip_spec.loader.exec_module(strip_module)
with tempfile.TemporaryDirectory(prefix="sb-append-char-", dir=root / "build") as temporary:
    classes = Path(temporary) / "classes"
    classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source], check=True)
    generated = (classes / "java/lang/StringBuilder.class").read_bytes()
cleaned, removed = strip_module.strip_stackmap(generated)
assert len(generated) == 990 and hashlib.sha256(generated).hexdigest() == "9e4dc94a2d6cebc233b9f10cbc0c7055d16ab9a62cf8a4be368a0e76b8d81204"
assert removed == 64 and len(cleaned) == 926 and hashlib.sha256(cleaned).hexdigest() == STRING_BUILDER_SHA256
image = bytes.fromhex("".join((stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().split()))
assert image == cleaned

parent_pins = json.loads((parent / "build-pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["runtimeBaseline"] == 393123 and parent_pins["engine"]["bytes"] == 393191
assert parent_pins["runtimeCap"] == 393216 and parent_pins["bootstrapCount"] == 91
assert parent_pins["rawLimits"] == [38, 285489] and parent_pins["diagnosticClassBound"] == 129
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14 and parent_pins["maxFrames"] == 128
assert parent_pins["address"] == "0x" + PARENT_ENGINE and parent_pins["owner"] == "0x" + PARENT_OWNER

parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
pattern = r'(function _bootstrapStringBuilder\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})'
assert len(re.findall(pattern, expected_engine)) == 1
expected_engine, count = re.subn(pattern, r'\g<1>' + image.hex() + r'\g<2>', expected_engine)
assert count == 1
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
# Only runtime image84 changes; the immutable 91-image order and all fixed
# parser/quota/native bounds retain their accepted literal values.
for fixed in (
    "MAX_RAW_CLASSES = 38;", "MAX_RAW_BYTES = 285489;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "new bytes32[](91)", "new uint256[](14)",
    "return 13;", "uint32(38), uint32(285489)", "h[44] = keccak256(_bootstrapSystem());",
    "h[84] = keccak256(_bootstrapStringBuilder());", "h[90] = DBOOT_STACK_TRACE_ELEMENT;",
    "return keccak256(abi.encode(DBOOT, h));",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
assert parent_coordinator.count(PARENT_DOMAIN) == 4 and parent_coordinator.count(PARENT_ENGINE) == 1
initial_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
parent_driver = (parent / "tools/Go.txt").read_text()
assert parent_driver.count(PARENT_DOMAIN) == 6
initial_driver = parent_driver.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)
assert (stage / "tools/checkpoint_diagnostic.py").read_bytes() == (parent / "tools/checkpoint_diagnostic.py").read_bytes()
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "tools/checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "tools/verify_receipts.js").read_bytes()
assert (stage / "engine/build.js").read_bytes() == (parent / "engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "coordinator/build.js").read_bytes()

fixture_addition = '''# append(char) keeps each UTF-16 code unit without a host conversion. The
# prefix comes through the retained append(String) path; NUL, ASCII, and both
# surrogate halves must survive independently in the returned String copy.
build("stringbuilder-append-char", {
    "StringBuilderAppendCharMain.java": """public final class StringBuilderAppendCharMain {
  static int result;
  public static void main(String[] ignored) {
    StringBuilder builder = new StringBuilder();
    if (builder.append("pre") != builder) throw new Error();
    if (builder.append('\\\\u0000') != builder) throw new Error();
    if (builder.append('A') != builder) throw new Error();
    if (builder.append('\\\\ud83d') != builder) throw new Error();
    if (builder.append('\\\\ude00') != builder) throw new Error();
    String first = builder.toString();
    if (first.length() != 7 || first.charAt(0) != 'p' || first.charAt(1) != 'r'
        || first.charAt(2) != 'e' || first.charAt(3) != '\\\\u0000'
        || first.charAt(4) != 'A' || first.charAt(5) != '\\\\ud83d'
        || first.charAt(6) != '\\\\ude00') throw new Error();
    builder.append('!');
    if (first.length() != 7 || first.charAt(6) != '\\\\ude00'
        || builder.toString().charAt(7) != '!') throw new Error();
    result = 7;
  }
}
""",
}, ["StringBuilderAppendCharMain.class"], "StringBuilderAppendCharMain")
append_char_disassembly = subprocess.run(
    [javap, "-classpath", classes_root / "stringbuilder-append-char", "-c", "StringBuilderAppendCharMain"],
    text=True, capture_output=True, check=True,
).stdout
assert append_char_disassembly.count("StringBuilder.append:(C)Ljava/lang/StringBuilder;") >= 5

'''
base_fixture = (parent / "tools/generate_fixtures.py").read_text()
expected_fixture = base_fixture.replace("java-diff-mc-monitor-enter-exit-fixtures-", "java-diff-mc-string-builder-append-char-fixtures-")
fixture_needle = 'for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39): count_fixture("count-%d" % count, count)\n'
assert expected_fixture.count(fixture_needle) == 1
expected_fixture = expected_fixture.replace(fixture_needle, fixture_addition + fixture_needle)
assert (stage / "tools/generate_fixtures.py").read_text() == expected_fixture

parent_gate = (parent / "tools/gate.py").read_text()
expected_gate = parent_gate.replace(PARENT_DOMAIN, DOMAIN)
expected_gate = expected_gate.replace("java-diff-mc-monitor-enter-exit-build-", "java-diff-mc-string-builder-append-char-build-")
expected_gate = expected_gate.replace("java-diff-mc-monitor-enter-exit-fixtures-", "java-diff-mc-string-builder-append-char-fixtures-")
expected_gate = expected_gate.replace("java-diff-mc-monitor-enter-exit-gate-", "java-diff-mc-string-builder-append-char-gate-")
expected_gate = expected_gate.replace("One generated-only bounded monitorenter/monitorexit and retained acceptance gate.", "One generated-only bounded StringBuilder.append(char) and retained acceptance gate.")
expected_gate = expected_gate.replace('assert pins["bootstrapSHA256"]["StringBuilder"] == "22ca3088c0cebccc5714beefd40cf187dbaebe5930477559e20ab8709249ffa4"', 'assert pins["bootstrapSHA256"]["StringBuilder"] == "' + STRING_BUILDER_SHA256 + '"')
focused_needle = 'q_equivalent("monitor-enter-exit", "monitor-enter-exit")\n\n'
focused_addition = '''# append(char) is ordinary Java bytecode in only image84. The focused root
# exercises retained String-prefix copying plus NUL, ASCII, and surrogate UTF-16
# units, same-builder return identity, independent toString copies, q1/q7/direct,
# and each durable reopen.
q_equivalent("stringbuilder-append-char", "stringbuilder-append-char")

'''
assert expected_gate.count(focused_needle) == 1
expected_gate = expected_gate.replace(focused_needle, focused_needle + focused_addition)
old_limit = '"limitations": "Only monitorenter(0xc2)/monitorexit(0xc3) are added to predecode and execution. They pop one reference; null raises guest NPE; non-null balanced and reentrant operations are bounded single-guest-thread no-ops. No ownership, contention, wait/notify, provider factory, world, or Done claim is made. The 91-image order/runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."'
new_limit = '"limitations": "Only bootstrap image84 java/lang/StringBuilder changes. Its ordinary append(char) returns the same builder, preserves existing logical chars, and appends exactly the supplied UTF-16 code unit through the retained append(String) path. The source-derived image removes only ignored Code-local StackMapTable attributes; all Code bytes and all non-StackMap classfile structure are retained. No other append overload, provider factory, world, or Done claim is made. The 91-image order/runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."'
assert expected_gate.count(old_limit) == 1
expected_gate = expected_gate.replace(old_limit, new_limit)
assert (stage / "tools/gate.py").read_text() == expected_gate
assert "whole_gate_seconds <= 1200" in expected_gate and "canonical-receipts" in expected_gate

# Recalculate the immutable root from the actual source image.  Image84 is the
# only leaf delta from the accepted monitor stage.
root_record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((parent / "root-commitment.json").read_text())
assert root_record["domain"] == DOMAIN and root_record["bootstrapCount"] == 91
assert root_record["order"] == base_root["order"]
changed = [i for i, (old, new) in enumerate(zip(base_root["keccak256"], root_record["keccak256"])) if old != new]
assert changed == [84] and len(root_record["keccak256"]) == 91
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const image=Buffer.from(x.image,"hex");const leaf=keccak256(image);const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.keccak256.length),...x.keccak256.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({leaf:leaf,dboot:d,bootstrapRoot:r}));'''
calculation = dict(root_record, image=image.hex())
computed = json.loads(subprocess.run(["node", "-e", program], input=json.dumps(calculation), text=True,
    capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert root_record["keccak256"][84] == computed["leaf"]
assert root_record["dboot"] == computed["dboot"] and root_record["bootstrapRoot"] == computed["bootstrapRoot"]

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coordinator
    assert (stage / "tools/Go.txt").read_text() == initial_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    bootstrap_sha256 = dict(parent_pins["bootstrapSHA256"])
    bootstrap_sha256["StringBuilder"] = STRING_BUILDER_SHA256
    expected = {
        "basis": "868c7d1b8", "parentEvidence": "monitor-enter-exit-preflight", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393191, "runtimeCap": 393216,
        "bootstrapCount": 91, "bootstrapSHA256": bootstrap_sha256,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [38, 285489], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 129, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected and pins["engine"]["bytes"] <= 393216
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
        final_driver, changed_count = re.subn(pattern, replacement, final_driver)
        assert changed_count == 1
    assert (stage / "tools/Go.txt").read_text() == final_driver
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "868c7d1b8", "fixtureBasis": "monitor-enter-exit-preflight",
    "phase": phase, "domain": DOMAIN, "bootstrapImages": 91,
    "bootstrapRoot": root_record["bootstrapRoot"], "stringBuilderSHA256": STRING_BUILDER_SHA256,
    "rawLimits": [38, 285489], "diagnosticClassBound": 129,
    "runtimeBaseline": 393191, "runtimeCap": 393216, "globalNativeBindings": 13,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "address": "0x" + ENGINE,
}, indent=2))
