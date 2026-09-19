#!/usr/bin/env python3
"""Strict source invariants for the bounded directly-created ThreadLocal.get stage.

The sole runtime basis is accepted raw37. This verifier reads only generated
stage/parent sources and pinned local compiler tooling; it never opens an
original artifact, JAR, class, resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount37-byte282358-preflight"

PARENT = {
    "engine/MCEntryInterpreter.sol": "d74baa3d9b7549c327b763e25b8b7d9141893bc860f67b0fe29138a357cfc383",
    "coordinator/MCEntryCoordinator.sol": "62fde39b0d0b28f86db70e147641c7e533d27b5499a29dfc34473d09dd0b1bb4",
    "tools/Go.txt": "78fc3cc1ca1edcc53c000ab57a418188ebf0e665470b6ed3378bcd6c05b9fb6b",
    "tools/checkpoint_diagnostic.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "tools/checkpoint_frames.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "tools/verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bdc258fdf06eb0d290ef08ca", # replaced below
}
# The last digest is intentionally assigned separately: it is the pinned
# coordinator build script, not an inferred artifact hash.
PARENT["coordinator/build.js"] = "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e"
PARENT_DOMAIN = "MC-RAW37-BYTE282358-P1"
DOMAIN = "MC-THREAD-LOCAL-GET-P1"
PARENT_ENGINE = "4d432d52415733372d4259544532383233353845"
ENGINE = "4d432d5448524541444c4f43414c2d4745542d45"
PARENT_OWNER = "4d432d52415733372d425954453238323335384f"
OWNER = "4d432d5448524541444c4f43414c2d4745542d4f"
THREADLOCAL_SHA256 = "cc0a43a9627fd7f6a1ec1b85711e4cb1ba3d988dab06e3fd5fbe795e175b1289"
THREADLOCAL_HEX = "cafebabe00000034000c0a0003000907000a07000b0100063c696e69743e010003282956010004436f646501000367657401001428294c6a6176612f6c616e672f4f626a6563743b0c000400050100156a6176612f6c616e672f5468726561644c6f63616c0100106a6176612f6c616e672f4f626a656374003100020003000000000002000100040005000100060000001100010001000000052ab70001b100000000000100070008000100060000000e000100010000000201b0000000000000"
ROOT = "1aa769a912931967ca44cec129ff505741409aecaee7536a85a586213deb4a7b"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_images(text):
    out = {}
    for name, image in re.findall(
        r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{[\s\S]*?return hex\"([0-9a-f]+)\";",
        text, re.S,
    ):
        assert name not in out
        out[name] = image
    return out


def parent_order(text):
    begin = text.index("    function _bootstrapRoot() private pure returns (bytes32) {")
    end = text.index("\n    function _prepare(", begin)
    rows = re.findall(r"h\[(\d+)\] = ([^;]+);", text[begin:end])
    assert len(rows) == 90
    special = {"DBOOT_ENUMSET": "EnumSet", "DBOOT_ITERABLE": "Iterable", "DBOOT_MATH": "Math"}
    names = []
    for index, value in rows:
        assert int(index) == len(names)
        found = re.search(r"_bootstrap(\w+)\(\)", value)
        name = found.group(1) if found else special.get(value.strip())
        assert name is not None, value
        names.append(name)
    return names


def keccak_commitment(images, order):
    """Compute exact EVM keccak/ABI root through pinned local js-sha3 only."""
    payload = {"domain": DOMAIN, "images": [images["_bootstrap" + name] for name in order]}
    node = root / "jvmevm/runtime/node_modules"
    assert node.is_dir(), "refusing shared or network Node dependencies"
    script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8")); const word=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};
const h=x.images.map(v=>keccak256(Buffer.from(v,"hex")));
const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));
const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),word(64),word(h.length),...h.map(v=>Buffer.from(v,"hex"))]));
process.stdout.write(JSON.stringify({dboot:d,root:r,hashes:h}));'''
    env = dict(os.environ, NODE_PATH=str(node))
    result = subprocess.run(["node", "-e", script], input=json.dumps(payload), text=True,
                            capture_output=True, check=True, env=env)
    return json.loads(result.stdout)


def expected_engine(parent_engine):
    assert parent_engine.count(PARENT_DOMAIN) == 9
    text = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
    old = "cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100156a6176612f6c616e672f5468726561644c6f63616c0100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"
    assert text.count(old) == 1
    text = text.replace(old, THREADLOCAL_HEX)
    begin = text.index("    function _bootstrapRoot() private pure returns (bytes32) {")
    end = text.index("\n    function _prepare(", begin)
    dynamic_root = parent_engine[begin:end]
    assert dynamic_root.count("h[0] = keccak256(_bootstrapObject());") == 1
    dynamic_root = dynamic_root.replace(
        "h[0] = keccak256(_bootstrapObject());", "h[0] = _objectImageHash();"
    )
    helper = '''

    // This remains a runtime Keccak over the exact Object image bytes. Keeping the
    // image materializer single-sited avoids duplicating that immutable literal.
    function _objectImageHash() private pure returns (bytes32) {
        return keccak256(_bootstrapObject());
    }
'''
    return text[:begin] + dynamic_root + helper + text[end:]


inputs = {name: digest(parent / name) for name in PARENT}
assert inputs == PARENT
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-24250cb9d", "parentEvidence": "classcount37-byte282358-preflight", "sha256": inputs,
}
parent_pins = json.loads((parent / "build-pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [37, 282358]
assert parent_pins["diagnosticClassBound"] == 127 and parent_pins["engine"]["bytes"] == 393208
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/ThreadLocal.java").read_text()
assert source == """package java.lang;
public final class ThreadLocal {
  public ThreadLocal() {}
  public Object get() { return null; }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="thread-local-get-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name); src = tmp / "java/lang/ThreadLocal.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/ThreadLocal.class").read_bytes()
assert len(image) == 193 and hashlib.sha256(image).hexdigest() == THREADLOCAL_SHA256
assert image.hex() == THREADLOCAL_HEX == (stage / "bootstrap/java/lang/ThreadLocal.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert b"get" in image and b"()Ljava/lang/Object;" in image and b"initialValue" not in image
assert b"set" not in image and b"remove" not in image and b"withInitial" not in image
# ACC_PUBLIC|ACC_FINAL|ACC_SUPER is the exact direct-only image header.
assert bytes.fromhex("003100020003") in image

parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(parent_engine)
old_images = source_images(parent_engine); images = source_images(engine)
assert set(images) == set(old_images)
for name, value in old_images.items():
    if name == "_bootstrapThreadLocal":
        assert images[name] == THREADLOCAL_HEX
    else:
        assert images[name] == value, name
order = parent_order(parent_engine)
assert order[88] == "ThreadLocal" and len(order) == 90
commitment = keccak_commitment(images, order)
root_record = json.loads((stage / "root-commitment.json").read_text())
assert commitment["root"] == ROOT == root_record["bootstrapRoot"]
assert commitment["dboot"] == root_record["dboot"]
assert commitment["hashes"] == root_record["keccak256"]
assert root_record["order"] == order and root_record["threadLocal"] == {
    "bytes": 193, "sha256": THREADLOCAL_SHA256, "keccak256": commitment["hashes"][88],
}
layout = json.loads((stage / "layout-recovery.json").read_text())
assert layout["runtimeCap"] == 393216
assert layout["rejectedPrecomputedRootLayout"] == {
    "root": "return a precomputed full keccak256(abi.encode(DBOOT, ordered bytes32[90])) commitment",
    "runtimeBytes": 351723,
    "reason": "rejected: the full bootstrap root must remain runtime-derived from exact image bytes",
}
assert layout["rejectedUnsharedDynamicRootLayout"] == {
    "root": "allocate ordered bytes32[90], keccak each immutable bootstrap image, then keccak256(abi.encode(DBOOT, h))",
    "runtimeBytes": 393291, "overCapBytes": 75,
}
assert layout["acceptedRuntimeDerivedLayout"] == {
    "root": "keccak256(abi.encode(DBOOT, h)) with raw37's ordered runtime image hashes and retained isolated constants",
    "objectHash": "runtime keccak256(_bootstrapObject()) through a single-sited helper; not a precomputed commitment",
    "bootstrapRoot": ROOT, "runtimeBytes": 392959, "savedBytes": 332, "headroomBytes": 257,
    "runtimeSHA256": "94bd54ce277258129466e80252f7599b0fdd6666ca086385f5ba06b881e97993",
}
for fixed in (
    "MAX_RAW_CLASSES = 37;", "MAX_RAW_BYTES = 282358;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(37), uint32(282358)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "classes[at + 2].data = _bootstrapThreadLocal();",
):
    assert engine.count(fixed) == 1, fixed
root_begin = engine.index("    function _bootstrapRoot() private pure returns (bytes32) {")
root_end = engine.index("\n    function _prepare(", root_begin)
root_source = engine[root_begin:root_end]
parent_root_begin = parent_engine.index("    function _bootstrapRoot() private pure returns (bytes32) {")
parent_root_end = parent_engine.index("\n    function _prepare(", parent_root_begin)
parent_rows = re.findall(r"h\[(\d+)\] = ([^;]+);", parent_engine[parent_root_begin:parent_root_end])
root_rows = re.findall(r"h\[(\d+)\] = ([^;]+);", root_source)
assert len(parent_rows) == len(root_rows) == 90
assert [int(index) for index, _ in root_rows] == list(range(90))
assert root_rows[0] == ("0", "_objectImageHash()")
assert root_rows[1:] == parent_rows[1:]
assert "return keccak256(abi.encode(DBOOT, h));" in root_source
assert 'return hex"' + ROOT + '";' not in engine
assert engine.count("function _objectImageHash() private pure returns (bytes32) {") == 1
assert engine.count("return keccak256(_bootstrapObject());") == 1

expected_coordinator = (parent / "coordinator/MCEntryCoordinator.sol").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
expected_driver = (parent / "tools/Go.txt").read_text().replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE).replace("0x" + PARENT_OWNER, "0x" + OWNER)
driver = (stage / "tools/Go.txt").read_text()
assert driver.count(DOMAIN) == 6 and driver.count("0x" + ENGINE) == driver.count("0x" + OWNER) == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js", "engine/build.js", "coordinator/build.js"):
    assert (stage / ("tools/" + name) if name.endswith(".py") or name.endswith(".js") and name == "verify_receipts.js" else stage / name).read_bytes() == (parent / ("tools/" + name) if name.endswith(".py") or name.endswith(".js") and name == "verify_receipts.js" else parent / name).read_bytes()

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for text in (fixtures, gate):
    assert "original" in text
assert "threadlocal-get-default" in fixtures and "ThreadLocalGetDefaultMain" in fixtures
assert "threadlocal-get-omitted" not in fixtures
for label in ("threadlocal-set-omitted", "threadlocal-remove-omitted", "threadlocal-withinitial-omitted", "threadlocal-overridden-initialvalue-omitted", "threadlocal-multithread-omitted"):
    assert label in fixtures and label in gate
assert 'q_equivalent("threadlocal-get-default"' in gate
assert 'cc0a43a9627fd7f6a1ec1b85711e4cb1ba3d988dab06e3fd5fbe795e175b1289' in gate

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert coordinator == expected_coordinator
    assert driver == expected_driver
    assert not (stage / "build-pins.json").exists()
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected = {
        "basis": "parent-24250cb9d", "parentEvidence": "classcount37-byte282358-preflight", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393208, "runtimeCap": 393216,
        "bootstrapCount": 90, "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "ThreadLocal": THREADLOCAL_SHA256},
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [37, 282358], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 127, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= 393216 and pins["engine"]["bytes"] <= 393208
    assert pins["coordinator"]["bytes"] == 5394
    assert coordinator == expected_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    final_driver = expected_driver
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
    assert driver == final_driver
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "classcount37-byte282358-preflight", "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "threadLocal": {"bytes": 193, "sha256": THREADLOCAL_SHA256, "slot": 88},
    "bootstrapRoot": ROOT, "rawLimits": [37, 282358], "diagnosticClassBound": 127,
    "runtimeBaseline": 393208, "runtimeCap": 393216, "globalNativeBindings": 13,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
