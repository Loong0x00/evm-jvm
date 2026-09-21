#!/usr/bin/env python3
"""Verify that this stage changes only canonical PrintStream image83 and its root leaf."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-98e55f145"
base_root_path = stage.parent / "system-out-preflight/root-commitment.json"
PD = "MC-SUBSTRING-INT-00005"
D = "MC-PRINT-STREAM-OUTPUT-STREAM-001"
OLD_LEAF = "3731cc740c09a9df0c76d9775252bff86b931e928d443a2e340f9d7076deca45"
IMAGE_SHA = "f6b60f173a697b6b9ec39919cc307180feefa5ef35c7aad44e3bfa1366d5d726"
IMAGE_KECCAK = "c1ff3f8133bf58b9aa931dd43f2c3a952bd796af365edfc723ff1006c20f12a6"
ADDR = "0x4d432d5052494e542d53545245414d2d4f555401"
OWNER = "0x4d432d5052494e542d53545245414d2d4f555402"
PARENT_ADDR = "0x4d432d535542535452494e472d494e542d303039"
PARENT_OWNER = "0x4d432d535542535452494e472d494e542d303061"
FRAGMENT_SHA = "87174b95773fc3b1f1008a88c6615e031114f12b3375c390c03e0efb67879a5e"
FOCUSED_GENERATOR_SHA = "341a89bb9101bfa1e7ea75c1ba4bfa20b6117889f167957aeab032f8d9fa0810"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def u2(data, at):
    assert at + 2 <= len(data)
    return int.from_bytes(data[at:at + 2], "big"), at + 2

def u4(data, at):
    assert at + 4 <= len(data)
    return int.from_bytes(data[at:at + 4], "big"), at + 4

def class_info(data):
    """Parse complete member tables and exact Code payloads, not textual snippets."""
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8
    count, at = u2(data, at)
    cp = [None] * count
    index = 1
    while index < count:
        tag = data[at]; at += 1
        if tag == 1:
            size, at = u2(data, at); cp[index] = (tag, data[at:at + size]); at += size
        elif tag in (3, 4):
            at += 4
        elif tag in (5, 6):
            at += 8; index += 1
        elif tag in (7, 8, 16, 19, 20):
            value, at = u2(data, at); cp[index] = (tag, value)
        elif tag in (9, 10, 11, 12, 18):
            left, at = u2(data, at); right, at = u2(data, at); cp[index] = (tag, left, right)
        elif tag == 15:
            at += 3
        else:
            raise AssertionError(("constant-pool-tag", tag))
        index += 1
    access, at = u2(data, at); this, at = u2(data, at); super_, at = u2(data, at)
    interfaces, at = u2(data, at); assert at + 2 * interfaces <= len(data); at += 2 * interfaces
    def utf(index):
        assert cp[index][0] == 1
        return cp[index][1]
    def cls(index):
        assert cp[index][0] == 7
        return utf(cp[index][1])
    def members():
        nonlocal at
        amount, at = u2(data, at)
        items = []
        for _ in range(amount):
            member_access, at = u2(data, at); name, at = u2(data, at); desc, at = u2(data, at); attributes, at = u2(data, at)
            values = []
            for _ in range(attributes):
                attr_name, at = u2(data, at); size, at = u4(data, at)
                values.append((utf(attr_name), data[at:at + size])); at += size
            items.append((member_access, utf(name), utf(desc), values))
        return items
    fields = members(); methods = members()
    attributes, at = u2(data, at)
    for _ in range(attributes):
        _, at = u2(data, at); size, at = u4(data, at); at += size
    assert at == len(data)
    return {"count": count, "cp": cp, "classAccess": access, "this": cls(this), "super": cls(super_), "fields": fields, "methods": methods}

def code(method):
    attributes = method[3]
    assert len(attributes) == 1 and attributes[0][0] == b"Code"
    data = attributes[0][1]
    at = 0; maximum_stack, at = u2(data, at); maximum_locals, at = u2(data, at); size, at = u4(data, at)
    value = data[at:at + size]; at += size
    handlers, at = u2(data, at); assert at + 8 * handlers <= len(data); at += 8 * handlers
    nested, at = u2(data, at)
    for _ in range(nested):
        _, at = u2(data, at); length, at = u4(data, at); at += length
    assert at == len(data)
    return maximum_stack, maximum_locals, value

def exact(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)

assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
built = sys.argv[1] == "--built"
if built:
    assert len(sys.argv) == 3
    pins_path = Path(sys.argv[2]).resolve()
else:
    assert len(sys.argv) == 2 and not (stage / "build-pins.json").exists()

parent_inputs = json.loads((stage / "parent-input.json").read_text())
expected_inputs = {
    "parent-98e55f145/artifacts/engine/MCEntryInterpreter.sol": parent / "artifacts/engine/MCEntryInterpreter.sol",
    "parent-98e55f145/artifacts/coordinator/MCEntryCoordinator.sol": parent / "artifacts/coordinator/MCEntryCoordinator.sol",
    "parent-98e55f145/canonical-driver.go.txt": parent / "canonical-driver.go.txt",
    "parent-98e55f145/checkpoint_diagnostic.py": parent / "checkpoint_diagnostic.py",
    "parent-98e55f145/checkpoint_frames.py": parent / "checkpoint_frames.py",
    "parent-98e55f145/verify_receipts.js": parent / "verify_receipts.js",
    "parent-98e55f145/generated_gate.py": parent / "generated_gate.py",
    "parent-98e55f145/pins.json": parent / "pins.json",
    "parent-98e55f145/artifacts/engine/build.js": parent / "artifacts/engine/build.js",
    "parent-98e55f145/artifacts/coordinator/build.js": parent / "artifacts/coordinator/build.js",
    "classcount52-byte329162-preflight/tools/generate_fixtures.py": stage.parent / "classcount52-byte329162-preflight/tools/generate_fixtures.py",
    "string-substring-int-preflight/tools/generate_fixtures.py": stage.parent / "string-substring-int-preflight/tools/generate_fixtures.py",
    "system-out-preflight/root-commitment.json": base_root_path,
}
assert parent_inputs == {"basis": "175bf8ace", "sha256": {name: sha(path) for name, path in expected_inputs.items()}}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["bootstrapRoot"] == "86dfeffdbb279e8b80834d4905ce6bd639074af4c82d12e6b8a4acf2cdb86542"
assert parent_pins["rawLimits"] == [52, 329162] and parent_pins["bootstrapCount"] == 94
assert parent_pins["globalNativeBindings"] == 14 and parent_pins["stringLocalBinding"] == 11

# The producer/image are independent of host PrintStream. The full classfile
# proves direct super, OutputStream constructor, retained sink Code, and only
# the Java-required write(int) low-code-unit bridge.
spec = importlib.util.spec_from_file_location("printstream_image", stage / "bootstrap/build_print_stream.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
image = module.build()
assert len(image) == 378 and hashlib.sha256(image).hexdigest() == IMAGE_SHA
assert image.hex() == "".join((stage / "bootstrap/java/io/PrintStream.class.hex").read_text().split())
info = class_info(image)
assert info["count"] == 24 and info["classAccess"] == 0x21
assert info["this"] == b"java/io/PrintStream" and info["super"] == b"java/io/OutputStream"
assert [(item[0], item[1], item[2]) for item in info["fields"]] == [(2, b"println", b"Ljava/lang/String;"), (2, b"print", b"C")]
assert [(item[0], item[1], item[2]) for item in info["methods"]] == [
    (1, b"<init>", b"()V"), (1, b"println", b"(Ljava/lang/String;)V"), (1, b"print", b"(C)V"), (1, b"write", b"(I)V")]
assert code(info["methods"][0]) == (1, 1, bytes.fromhex("2ab70001b1"))
assert code(info["methods"][1]) == (2, 2, bytes.fromhex("2bc22bc32a2bb50002b1"))
assert code(info["methods"][2]) == (2, 2, bytes.fromhex("2a1bb5000fb1"))
assert code(info["methods"][3]) == (3, 2, bytes.fromhex("2a1b1100ff7e92b5000fb1"))
# CP#1 must be Methodref(OutputStream,<init>()V), so the direct constructor
# cannot regress to Object or self recursion; CP#15 remains the private char field.
cp = info["cp"]
assert cp[1][0] == 10 and cp[cp[1][1]][0] == 7 and cp[cp[cp[1][1]][1]][1] == b"java/io/OutputStream"
assert cp[15][0] == 9 and cp[cp[15][1]][0] == 7 and cp[cp[cp[15][1]][1]][1] == b"java/io/PrintStream"
source = (stage / "bootstrap/java/io/PrintStream.java").read_text()
for required in ("class PrintStream extends OutputStream", "public PrintStream() { super(); }", "public void println(String line)", "public void print(char codeUnit)", "public void write(int value)", "print = (char) (value & 0xff);"):
    assert source.count(required) == 1, required

# Exact engine derivation: only stage domain identity, image83 leaf/literal and
# its local comment change. The OutputStream literal remains parent-byte-identical.
engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert engine.count(PD) == 9
expected_engine = engine.replace(PD, D)
expected_engine = exact(expected_engine, OLD_LEAF, IMAGE_KECCAK)
old_comment = """    /// @dev Bounded Java 8 PrintStream: retained println(String) plus bounded print(char).
    /// @dev println preserves monitor/null/reference semantics; print stores one UTF-16 code unit privately.
"""
new_comment = """    /// @dev Canonical direct OutputStream PrintStream: retained println(String)/print(char), plus required write(int).
    /// @dev println preserves monitor/null/reference semantics; write(int) stores only its low UTF-16 code unit privately.
"""
expected_engine = exact(expected_engine, old_comment, new_comment)
pattern = r"(function _bootstrapPrintStream\(\) private pure returns \(bytes memory\) \{ return hex\")[0-9a-f]+(\"; \})"
assert len(re.findall(pattern, expected_engine)) == 1
expected_engine, changes = re.subn(pattern, r"\g<1>" + image.hex() + r"\g<2>", expected_engine)
assert changes == 1
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == expected_engine
for invariant in ("MAX_RAW_CLASSES = 52;", "MAX_RAW_BYTES = 329162;", "new bytes32[](94)", "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "h[35] = keccak256(_bootstrapOutputStream());", "h[83] = DBOOT_PRINT_STREAM;"):
    assert expected_engine.count(invariant) == 1, invariant
assert re.search(r"function _bootstrapOutputStream\(\).*?return hex\"([0-9a-f]+)\";", expected_engine, re.S).group(1) == re.search(r"function _bootstrapOutputStream\(\).*?return hex\"([0-9a-f]+)\";", engine, re.S).group(1)

# Root stays ordered/runtime-derived. Only leaf83 changes, including no folded
# Object/OutputStream leaf and no replacement of another historical image.
base_root = json.loads(base_root_path.read_text())
record = json.loads((stage / "root-commitment.json").read_text())
leaves = list(base_root["keccak256"]); leaves[83] = IMAGE_KECCAK
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.leaves.length),...x.leaves.map(v=>Buffer.from(v,"hex"))]));console.log(JSON.stringify({d,r}));'''
calculated = json.loads(subprocess.run(["node", "-e", node], input=json.dumps({"domain": D, "leaves": leaves}), text=True, capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert record == {"domain": D, "bootstrapCount": 94, "dboot": calculated["d"], "bootstrapRoot": calculated["r"], "order": base_root["order"], "keccak256": leaves}
assert [index for index, (before, after) in enumerate(zip(base_root["keccak256"], record["keccak256"])) if before != after] == [83]
assert record["keccak256"][0] == base_root["keccak256"][0] and record["keccak256"][35] == base_root["keccak256"][35]

# Coordinator/driver start as exact parent-domain/endpoint rebinding. Build then
# pins the newly built engine and coordinator hashes, not arbitrary source edits.
initial_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text().replace(PD, D).replace(PARENT_ADDR[2:], ADDR[2:])
initial_driver = (parent / "canonical-driver.go.txt").read_text().replace(PD, D).replace(PARENT_ADDR, ADDR).replace(PARENT_OWNER, OWNER)
if not built:
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord
    assert (stage / "tools/Go.txt").read_text() == initial_driver
else:
    pins = json.loads(pins_path.read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"]); bootstrap_sha["PrintStream"] = IMAGE_SHA
    expected_pins = {"phase": "built", "basis": "175bf8ace", "parentEvidence": "parent-98e55f145/artifacts/{engine,coordinator}/MCEntry*.sol", "domain": D, "bootstrapCount": 94, "bootstrapRoot": record["bootstrapRoot"], "bootstrapSHA256": bootstrap_sha, "globalNativeBindings": 14, "stringLocalBinding": 11, "exceptionKinds": 14, "maxFrames": 128, "rawLimits": [52, 329162], "diagnosticClassBound": 146, "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000, "runtimeCap": 393216, "address": ADDR, "owner": OWNER, "engine": pins["engine"], "coordinator": pins["coordinator"], "worker": "print-stream-output-stream"}
    assert pins == expected_pins == json.loads((stage / "build-pins.json").read_text())
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
    expected_coord = exact(initial_coord, parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_coord
    expected_driver = initial_driver
    for old, new in ((parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"])):
        expected_driver = exact(expected_driver, old, new)
    for pattern, replacement in ((r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]), (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]), (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"])):
        expected_driver, amount = re.subn(pattern, replacement, expected_driver); assert amount == 1
    assert (stage / "tools/Go.txt").read_text() == expected_driver

assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes(), name
retained = (stage.parent / "classcount52-byte329162-preflight/tools/generate_fixtures.py").read_text().replace("java-diff-mc-classcount52-byte329162-retained-fixtures-", "java-diff-mc-print-stream-output-stream-retained-fixtures-")
assert (stage / "tools/generate_retained_fixtures.py").read_text() == retained
assert sha(stage / "tools/generate_focused_fixtures.py") == FOCUSED_GENERATOR_SHA

# Gate is a deterministic parent gate rewrite with the hash-pinned narrow focus.
fragment = stage / "tools/outputstream_gate_fragment.py"
assert sha(fragment) == FRAGMENT_SHA
expected_gate = (parent / "generated_gate.py").read_text()
expected_gate = expected_gate.replace("root = here.parents[3]", "root = here.parents[4]")
expected_gate = exact(expected_gate, "assert build.name.startswith(\"java-diff-mc-raw52-parent-\")", "assert build.name.startswith(\"java-diff-mc-print-stream-output-stream-build-\")")
expected_gate = exact(expected_gate, "assert retained_fixtures.name.startswith(\"java-diff-mc-classcount52-byte329162-retained-fixtures-\")", "assert retained_fixtures.name.startswith(\"java-diff-mc-print-stream-output-stream-retained-fixtures-\")")
expected_gate = exact(expected_gate, "assert focused_fixtures.name.startswith(\"java-diff-mc-string-substring-int-fixtures-\")", "assert focused_fixtures.name.startswith(\"java-diff-mc-print-stream-output-stream-fixtures-\")")
expected_gate = exact(expected_gate, "assert out.name.startswith(\"java-diff-mc-raw52-parent-gate-\") and not out.exists()", "assert out.name.startswith(\"java-diff-mc-print-stream-output-stream-gate-\") and not out.exists()")
old_doc = '"""Generated-only full gate for bounded guest System.out.\n\nThe new System.out witness runs q1/q7/direct/reopen. All retained generated\ncontrols run direct/reopen only. It never reads an original JAR, Minecraft\ndata, network input, world, EULA, or Done marker.\n"""'
new_doc = '"""Generated-only gate for the canonical direct PrintStream -> OutputStream edge.\n\nThe focused generated subtype witness runs q1/q7/direct/reopen. Retained\ncontrols run direct/reopen only. No original artifact, resource, network,\nworld, EULA, or Done marker is read or claimed.\n"""'
expected_gate = exact(expected_gate, old_doc, new_doc)
old_sha = 'assert pins["bootstrapSHA256"] == {\n    "String": "04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231",\n    "System": "ad7a74cb7c5fdf1e79a26a7f18034c46f301fb94af6bf4f12648a3ca62f57576",\n}'
new_sha = 'assert pins["bootstrapSHA256"] == {\n    "String": "04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231",\n    "System": "ad7a74cb7c5fdf1e79a26a7f18034c46f301fb94af6bf4f12648a3ca62f57576",\n    "PrintStream": "' + IMAGE_SHA + '",\n}'
expected_gate = exact(expected_gate, old_sha, new_sha)
expected_gate = exact(expected_gate, 'assert pins["bootstrapRoot"] == "86dfeffdbb279e8b80834d4905ce6bd639074af4c82d12e6b8a4acf2cdb86542"', 'assert pins["bootstrapRoot"] == "' + record["bootstrapRoot"] + '"')
expected_gate = exact(expected_gate, '# Run the sole current q1/q7/direct witness before retained direct/reopen work.\nq_system_out()\n', '# System.out is retained direct/reopen; the new direct superclass focus follows.\nretained("system-out", "system-out", system_out_initialized)\n\n' + fragment.read_text())
expected_gate = exact(expected_gate, '"profile": "MC-RAW52-BYTE329162-P1"', '"profile": "MC-PRINT-STREAM-OUTPUT-STREAM-P1"')
old_limit = '"limitations": "Only raw capacity constants advance from raw51/328000/diagnostic145 to raw52/329162/diagnostic146. All 94 ordered bootstrap images and their runtime-derived root, native14, String-local11, System out/err, exception14, frame/checkpoint/selected-resource limits, toolchain, and every other semantic remain pinned. The exact raw52 generated focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. This gate uses only trusted generated Java-8 fixtures and reads no original artifact, JAR, resource, provider construction, factory execution, world, EULA, or Done input or claim. Parent alone owns genuine no binding and replay."'
new_limit = '"limitations": "Only canonical bootstrap image83 changes: PrintStream directly extends the retained OutputStream, chains its constructor there, retains guest println(String)/print(char) sinks, and declares the Java-required write(int) low-UTF-16-unit sink. OutputStream and every other ordered leaf remain runtime-derived; only leaf83 changes. Raw52/329162/diagnostic146, 94 images, native14, String-local11, System out/err, exception14, frame/checkpoint/selected-resource limits, toolchain, and all root-order rules remain pinned. The generated direct subtype focus runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. No host output, original artifact/JAR/resource, provider/factory, world, EULA, or Done input or claim exists. Parent replay remains deferred."'
expected_gate = exact(expected_gate, old_limit, new_limit)
assert (stage / "tools/gate.py").read_text() == expected_gate
assert not any(path.suffix in {".class", ".jar", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"phase": "built" if built else "prebuild", "imageBytes": len(image), "imageSHA256": IMAGE_SHA, "imageKeccak256": IMAGE_KECCAK, "directSuper": "java/io/OutputStream", "methods": ["<init>()V", "println(String)", "print(char)", "write(int)"], "changedRootLeaves": [83], "bootstrapRoot": record["bootstrapRoot"]}, indent=2))
