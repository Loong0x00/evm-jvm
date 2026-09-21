#!/usr/bin/env python3
"""Verify the sole image83 constructor/root-leaf delta before or after local build."""
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
parent = stage.parent / "parent-3aa2fed0a"
previous = stage.parent / "print-stream-output-stream-preflight"
DOMAIN = "MC-PRINT-STREAM-OUTPUT-STREAM-CONSTRUCTOR-001"
PARENT_DOMAIN = "MC-PRINT-STREAM-OUTPUT-STREAM-002"
ADDRESS = "0x4d432d5052494e542d53545245414d2d43543031"
OWNER = "0x4d432d5052494e542d53545245414d2d43543032"
PARENT_ADDRESS = "0x4d432d5052494e542d53545245414d2d4f555403"
PARENT_OWNER = "0x4d432d5052494e542d53545245414d2d4f555404"
IMAGE_SHA = "cd053e0847ae7c3a740a54e246fbc3dd3c42635bb44bf6fcdc317004b411a41c"
IMAGE_KECCAK = "6587de63639fa1c563fc0b4f84dc0e0355cdbffdfd6d355c1f758b83873884b9"

assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
built = sys.argv[1] == "--built"
if built:
    assert len(sys.argv) == 3
    pins_path = Path(sys.argv[2]).resolve()
else:
    assert len(sys.argv) == 2 and not (stage / "build-pins.json").exists()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def u2(data, at):
    return int.from_bytes(data[at:at + 2], "big"), at + 2

def u4(data, at):
    return int.from_bytes(data[at:at + 4], "big"), at + 4

def class_info(data):
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8; count, at = u2(data, at); cp = [None] * count; index = 1
    while index < count:
        tag = data[at]; at += 1
        if tag == 1:
            size, at = u2(data, at); cp[index] = (tag, data[at:at + size]); at += size
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; index += 1
        elif tag in (7, 8, 16, 19, 20): value, at = u2(data, at); cp[index] = (tag, value)
        elif tag in (9, 10, 11, 12, 18): left, at = u2(data, at); right, at = u2(data, at); cp[index] = (tag, left, right)
        elif tag == 15: at += 3
        else: raise AssertionError(("constant-pool-tag", tag))
        index += 1
    access, at = u2(data, at); this, at = u2(data, at); super_, at = u2(data, at)
    interfaces, at = u2(data, at); at += 2 * interfaces
    def utf(index): assert cp[index][0] == 1; return cp[index][1]
    def cls(index): assert cp[index][0] == 7; return utf(cp[index][1])
    def members():
        nonlocal at
        amount, at = u2(data, at); items = []
        for _ in range(amount):
            member_access, at = u2(data, at); name, at = u2(data, at); desc, at = u2(data, at); attributes, at = u2(data, at); values = []
            for _ in range(attributes):
                attr_name, at = u2(data, at); size, at = u4(data, at); values.append((utf(attr_name), data[at:at + size])); at += size
            items.append((member_access, utf(name), utf(desc), values))
        return items
    fields = members(); methods = members(); attributes, at = u2(data, at)
    for _ in range(attributes):
        _, at = u2(data, at); size, at = u4(data, at); at += size
    assert at == len(data)
    return {"count": count, "cp": cp, "access": access, "this": cls(this), "super": cls(super_), "fields": fields, "methods": methods}

def code(method):
    attributes = method[3]; assert len(attributes) == 1 and attributes[0][0] == b"Code"
    data = attributes[0][1]; at = 0; maximum_stack, at = u2(data, at); maximum_locals, at = u2(data, at); size, at = u4(data, at); value = data[at:at + size]; at += size
    handlers, at = u2(data, at); at += 8 * handlers; nested, at = u2(data, at)
    for _ in range(nested): _, at = u2(data, at); length, at = u4(data, at); at += length
    assert at == len(data)
    return maximum_stack, maximum_locals, value

def class_name(info, index):
    cp = info["cp"]; assert cp[index][0] == 7; return cp[cp[index][1]][1]

def method_name_type(info, index):
    cp = info["cp"]; assert cp[index][0] == 12; return cp[cp[index][1]][1], cp[cp[index][2]][1]

inputs = {
    "parent-3aa2fed0a/artifacts/engine/MCEntryInterpreter.sol": parent / "artifacts/engine/MCEntryInterpreter.sol",
    "parent-3aa2fed0a/artifacts/coordinator/MCEntryCoordinator.sol": parent / "artifacts/coordinator/MCEntryCoordinator.sol",
    "parent-3aa2fed0a/canonical-driver.go.txt": parent / "canonical-driver.go.txt",
    "parent-3aa2fed0a/checkpoint_diagnostic.py": parent / "checkpoint_diagnostic.py",
    "parent-3aa2fed0a/checkpoint_frames.py": parent / "checkpoint_frames.py",
    "parent-3aa2fed0a/verify_receipts.js": parent / "verify_receipts.js",
    "parent-3aa2fed0a/generated_gate.py": parent / "generated_gate.py",
    "parent-3aa2fed0a/pins.json": parent / "pins.json",
    "parent-3aa2fed0a/artifacts/engine/build.js": parent / "artifacts/engine/build.js",
    "parent-3aa2fed0a/artifacts/coordinator/build.js": parent / "artifacts/coordinator/build.js",
    "print-stream-output-stream-preflight/tools/generate_focused_fixtures.py": previous / "tools/generate_focused_fixtures.py",
    "print-stream-output-stream-preflight/tools/generate_retained_fixtures.py": previous / "tools/generate_retained_fixtures.py",
    "print-stream-output-stream-preflight/root-commitment.json": previous / "root-commitment.json",
}
assert json.loads((stage / "parent-input.json").read_text()) == {"basis": "3aa2fed0a", "sha256": {name: sha(path) for name, path in inputs.items()}}

spec = importlib.util.spec_from_file_location("printstream_image", stage / "bootstrap/build_print_stream.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
image = module.build()
assert len(image) == 507 and hashlib.sha256(image).hexdigest() == IMAGE_SHA
assert image.hex() == "".join((stage / "bootstrap/java/io/PrintStream.class.hex").read_text().split())
info = class_info(image)
assert info["count"] == 31 and info["access"] == 0x21
assert info["this"] == b"java/io/PrintStream" and info["super"] == b"java/io/OutputStream"
assert [(x[0], x[1], x[2]) for x in info["fields"]] == [(2, b"println", b"Ljava/lang/String;"), (2, b"print", b"C")]
assert [(x[0], x[1], x[2]) for x in info["methods"]] == [
    (1, b"<init>", b"()V"), (1, b"<init>", b"(Ljava/io/OutputStream;)V"),
    (1, b"println", b"(Ljava/lang/String;)V"), (1, b"print", b"(C)V"), (1, b"write", b"(I)V")]
assert code(info["methods"][0]) == (1, 1, bytes.fromhex("2ab70001b1"))
assert code(info["methods"][1]) == (1, 2, bytes.fromhex("2ab700012bb6001857b1"))
assert code(info["methods"][2]) == (2, 2, bytes.fromhex("2bc22bc32a2bb50002b1"))
assert code(info["methods"][3]) == (2, 2, bytes.fromhex("2a1bb5000fb1"))
assert code(info["methods"][4]) == (3, 2, bytes.fromhex("2a1b1100ff7e92b5000fb1"))
cp = info["cp"]
assert cp[1][0] == 10 and class_name(info, cp[1][1]) == b"java/io/OutputStream" and method_name_type(info, cp[1][2]) == (b"<init>", b"()V")
assert cp[24][0] == 10 and class_name(info, cp[24][1]) == b"java/lang/Object" and method_name_type(info, cp[24][2]) == (b"getClass", b"()Ljava/lang/Class;")
assert cp[30] == (1, b"(Ljava/io/OutputStream;)V")
source = (stage / "bootstrap/java/io/PrintStream.java").read_text()
for exact in ("class PrintStream extends OutputStream", "public PrintStream() { super(); }", "public PrintStream(OutputStream sink) { super(); sink.getClass(); }", "public void println(String line)", "public void print(char codeUnit)", "public void write(int value)"):
    assert source.count(exact) == 1, exact
assert "FilterOutputStream" not in source and "sink =" not in source

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
assert parent_engine.count(PARENT_DOMAIN) == 9
old_leaf = json.loads((parent / "pins.json").read_text())["bootstrapSHA256"]["PrintStream"]
assert old_leaf == "f6b60f173a697b6b9ec39919cc307180feefa5ef35c7aad44e3bfa1366d5d726"
old_image = "".join((previous / "bootstrap/java/io/PrintStream.class.hex").read_text().split())
assert expected_engine.count("c1ff3f8133bf58b9aa931dd43f2c3a952bd796af365edfc723ff1006c20f12a6") == 1
expected_engine = expected_engine.replace("c1ff3f8133bf58b9aa931dd43f2c3a952bd796af365edfc723ff1006c20f12a6", IMAGE_KECCAK)
pattern = r"(function _bootstrapPrintStream\(\) private pure returns \(bytes memory\) \{ return hex\")[0-9a-f]+(\"; \})"
assert len(re.findall(pattern, expected_engine)) == 1 and expected_engine.count(old_image) == 1
expected_engine, count = re.subn(pattern, r"\g<1>" + image.hex() + r"\g<2>", expected_engine)
assert count == 1 and (stage / "engine/MCEntryInterpreter.sol").read_text() == expected_engine
for invariant in ("MAX_RAW_CLASSES = 52;", "MAX_RAW_BYTES = 329162;", "new bytes32[](94)", "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "h[35] = keccak256(_bootstrapOutputStream());", "h[83] = DBOOT_PRINT_STREAM;"):
    assert expected_engine.count(invariant) == 1, invariant

base_root = json.loads((previous / "root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
leaves = list(base_root["keccak256"]); leaves[83] = IMAGE_KECCAK
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.leaves.length),...x.leaves.map(v=>Buffer.from(v,"hex"))]));console.log(JSON.stringify({d,r}));'''
calculated = json.loads(subprocess.run(["node", "-e", node], input=json.dumps({"domain": DOMAIN, "leaves": leaves}), text=True, capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert record == {"domain": DOMAIN, "bootstrapCount": 94, "dboot": calculated["d"], "bootstrapRoot": calculated["r"], "order": base_root["order"], "keccak256": leaves}
assert [i for i, (before, after) in enumerate(zip(base_root["keccak256"], record["keccak256"])) if before != after] == [83]
assert record["keccak256"][0] == base_root["keccak256"][0] and record["keccak256"][35] == base_root["keccak256"][35]

parent_pins = json.loads((parent / "pins.json").read_text())
initial_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ADDRESS[2:], ADDRESS[2:])
initial_driver = (parent / "canonical-driver.go.txt").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ADDRESS, ADDRESS).replace(PARENT_OWNER, OWNER)
if not built:
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord
    assert (stage / "tools/Go.txt").read_text() == initial_driver
else:
    pins = json.loads(pins_path.read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"]); bootstrap_sha["PrintStream"] = IMAGE_SHA
    expected_pins = {"phase": "built", "basis": "3aa2fed0a", "parentEvidence": "parent-3aa2fed0a/artifacts/{engine,coordinator}/MCEntry*.sol", "domain": DOMAIN, "bootstrapCount": 94, "bootstrapRoot": record["bootstrapRoot"], "bootstrapSHA256": bootstrap_sha, "globalNativeBindings": 14, "stringLocalBinding": 11, "exceptionKinds": 14, "maxFrames": 128, "rawLimits": [52, 329162], "diagnosticClassBound": 146, "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000, "runtimeCap": 393216, "address": ADDRESS, "owner": OWNER, "engine": pins["engine"], "coordinator": pins["coordinator"], "worker": "print-stream-output-stream-constructor"}
    assert pins == expected_pins == json.loads((stage / "build-pins.json").read_text())
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    expected_driver = initial_driver
    for old, new in ((parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"])):
        assert expected_driver.count(old) == 1; expected_driver = expected_driver.replace(old, new)
    for pattern, replacement in ((r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]), (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]), (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"])):
        expected_driver, count = re.subn(pattern, replacement, expected_driver); assert count == 1
    assert (stage / "tools/Go.txt").read_text() == expected_driver

assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes(), name
fixture_source = (stage / "tools/generate_focused_fixtures.py").read_text()
assert "PrintStreamOutputStreamConstructorMain" in fixture_source
assert "public PrintStream(OutputStream sink) {}" in fixture_source
assert "forwarded != 0" in fixture_source
assert "printstream-outputstream-constructor" in (stage / "tools/gate.py").read_text()
assert not any(path.suffix in {".class", ".jar", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"phase": "built" if built else "prebuild", "imageBytes": len(image), "imageSHA256": IMAGE_SHA, "imageKeccak256": IMAGE_KECCAK, "directSuper": "java/io/OutputStream", "methods": ["<init>()V", "<init>(OutputStream)", "println(String)", "print(char)", "write(int)"], "changedRootLeaves": [83], "bootstrapRoot": record["bootstrapRoot"]}, indent=2))
