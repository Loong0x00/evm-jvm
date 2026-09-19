#!/usr/bin/env python3
"""Strict source invariants for bounded directly-created ThreadLocal.set.

The accepted parent is parent-15aa4b8b0. Apart from a fresh equal-width stage
namespace/address, the only engine semantic delta is image89's exact Java-8
ThreadLocal class. This verifier reads only pinned local stage/parent sources
and toolchains; it never opens an original artifact, JAR, class, resource,
checkpoint, or world.
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
parent = stage.parent / "parent-15aa4b8b0"

PARENT = {
    "artifacts/engine/MCEntryInterpreter.sol": "e1decc98db075bc52960438b55a853b8e47f4a769a448fa1f33980029beadda9",
    "artifacts/coordinator/MCEntryCoordinator.sol": "2024367ecaa15df493371607fc3d3b677934c0c1a50cbfcbefb3b6f8a7950d5c",
    "executed-driver.go.txt": "c0499284255e9bb40cea960e01f68f83ed33e25c4bd6e3afe85b80608f609627",
    "checkpoint_diagnostic.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "checkpoint_frames.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-SB-CAPACITY-CTOR-P2"
DOMAIN = "MC-THREAD-LOCAL-SET-P1"
PARENT_ENGINE = "4d432d53422d43415041434954592d4354522d46"
ENGINE = "4d432d5448524541444c4f43414c2d5345542d45"
OWNER = "4d432d5448524541444c4f43414c2d5345542d4f"
THREADLOCAL_SHA256 = "041db70026c508194d1b13ccdc988e82fb07316a4900c3955b2d5aa3e0664d9b"
THREADLOCAL_KECCAK = "93a0007b6336f667890f5afa2b01572278a7e39ab93b2faf1095e054317f538a"
ROOT = "85fbf6a9abd54f7fbc872c0387cc129782adb52f753bc448bc099dabeef62ab1"


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


def root_rows(text):
    begin = text.index("    function _bootstrapRoot() private pure returns (bytes32) {")
    end = text.index("\n    function _prepare(", begin)
    rows = re.findall(r"h\[(\d+)\] = ([^;]+);", text[begin:end])
    assert len(rows) == 90
    assert [int(index) for index, _ in rows] == list(range(90))
    return rows, text[begin:end]


def root_order(rows):
    special = {"DBOOT_ENUMSET": "EnumSet", "DBOOT_ITERABLE": "Iterable", "DBOOT_MATH": "Math"}
    out = []
    for _, value in rows:
        found = re.search(r"_bootstrap(\w+)\(\)", value)
        name = found.group(1) if found else special.get(value.strip())
        assert name is not None, value
        out.append(name)
    return out


def commitment(images, order):
    node_modules = root / "jvmevm/runtime/node_modules"
    assert node_modules.is_dir(), "refusing shared or network Node dependencies"
    payload = {"domain": DOMAIN, "images": [images["_bootstrap" + name] for name in order]}
    script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8")); const word=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};
const h=x.images.map(v=>keccak256(Buffer.from(v,"hex"))); const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));
const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),word(64),word(h.length),...h.map(v=>Buffer.from(v,"hex"))]));
process.stdout.write(JSON.stringify({dboot:d,root:r,hashes:h}));'''
    result = subprocess.run(["node", "-e", script], input=json.dumps(payload), text=True,
                            capture_output=True, check=True,
                            env={**os.environ, "NODE_PATH": str(node_modules)})
    return json.loads(result.stdout)


def expected_engine(parent_engine, old_image, new_image):
    assert parent_engine.count(PARENT_DOMAIN) == 9
    assert parent_engine.count(old_image) == 1
    return parent_engine.replace(PARENT_DOMAIN, DOMAIN).replace(old_image, new_image)


inputs = {name: digest(parent / name) for name in PARENT}
assert inputs == PARENT
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "b0dd39568", "parentEvidence": "parent-15aa4b8b0", "sha256": inputs,
}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [37, 282358]
assert parent_pins["diagnosticClassBound"] == 127 and parent_pins["engine"]["bytes"] == 392934
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/ThreadLocal.java").read_text()
assert source == """package java.lang;
public final class ThreadLocal {
  private Object value;
  public ThreadLocal() {}
  public Object get() { return value; }
  public void set(Object value) { this.value = value; }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="thread-local-set-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name); src = tmp / "java/lang/ThreadLocal.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/ThreadLocal.class").read_bytes()
assert len(image) == 305 and hashlib.sha256(image).hexdigest() == THREADLOCAL_SHA256
assert image.hex() == (stage / "bootstrap/java/lang/ThreadLocal.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert bytes.fromhex("00310003000400000001") in image  # public final direct Object class, one field.
assert bytes.fromhex("2ab40002b0") in image and bytes.fromhex("2a2bb50002b1") in image
for forbidden in (b"remove", b"withInitial", b"initialValue", b"ThreadLocalMap", b"ThreadLocal$", b"Thread;"):
    assert forbidden not in image
for required in (b"value", b"get", b"set", b"java/lang/Object"):
    assert required in image

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_images = source_images(parent_engine); images = source_images(engine)
old_threadlocal = parent_images["_bootstrapThreadLocal"]
assert len(bytes.fromhex(old_threadlocal)) == 193
assert engine == expected_engine(parent_engine, old_threadlocal, image.hex())
assert set(images) == set(parent_images)
for name, old in parent_images.items():
    assert images[name] == (image.hex() if name == "_bootstrapThreadLocal" else old), name
rows, root_source = root_rows(engine)
parent_rows, _ = root_rows(parent_engine)
assert rows == parent_rows and root_order(rows)[88] == "ThreadLocal"
assert "h[88] = keccak256(_bootstrapThreadLocal());" in root_source
assert "return keccak256(abi.encode(DBOOT, h));" in root_source
assert 'return hex"' + ROOT + '";' not in engine
assert engine.count("_validateInitialMainRoot(s);") == 1
assert engine.count("function _validateInitialMainRoot(RuntimeState memory s)") == 1
for fixed in (
    "MAX_RAW_CLASSES = 37;", "MAX_RAW_BYTES = 282358;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(37), uint32(282358)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "classes[at + 2].data = _bootstrapThreadLocal();",
):
    assert engine.count(fixed) == 1, fixed
record = commitment(images, root_order(rows))
root_record = json.loads((stage / "root-commitment.json").read_text())
assert record["root"] == ROOT == root_record["bootstrapRoot"]
assert record["dboot"] == root_record["dboot"] and record["hashes"] == root_record["keccak256"]
assert root_record["domain"] == DOMAIN and root_record["order"] == root_order(rows)
assert root_record["threadLocal"] == {"slot": 88, "bytes": 305, "sha256": THREADLOCAL_SHA256, "keccak256": THREADLOCAL_KECCAK}
assert record["hashes"][88] == THREADLOCAL_KECCAK

coordinator_parent = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = coordinator_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1

driver_parent = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
assert driver.count(DOMAIN) == 6 and driver.count("0x" + ENGINE) == 1
for stage_name, parent_name in (("checkpoint_diagnostic.py", "checkpoint_diagnostic.py"),
                                ("checkpoint_frames.py", "checkpoint_frames.py"),
                                ("verify_receipts.js", "verify_receipts.js")):
    assert (stage / "tools" / stage_name).read_bytes() == (parent / parent_name).read_bytes()
for stage_name, parent_name in (("engine/build.js", "artifacts/engine/build.js"),
                                ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / stage_name).read_bytes() == (parent / parent_name).read_bytes()

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for text in (fixtures, gate):
    assert "original" in text
assert "ThreadLocalSetMain" in fixtures and 'build("threadlocal-set"' in fixtures
assert "threadlocal-set-omitted" not in fixtures and "threadlocal-get-default" not in fixtures
for label in ("threadlocal-remove-omitted", "threadlocal-withinitial-omitted", "threadlocal-initialvalue-omitted",
              "threadlocal-overridden-initialvalue-omitted", "threadlocal-multithread-omitted", "raw-threadlocal"):
    assert label in fixtures and label in gate
assert 'q_equivalent("threadlocal-set", "threadlocal-set", threadlocal_set_initialized)' in gate
assert THREADLOCAL_SHA256 in gate

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
        "basis": "b0dd39568", "parentEvidence": "parent-15aa4b8b0", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 392934, "runtimeCap": 393216,
        "bootstrapCount": 90, "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "ThreadLocal": THREADLOCAL_SHA256},
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [37, 282358], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 127, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= 393216
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
    "acceptedParent": "parent-15aa4b8b0", "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "threadLocal": {"bytes": 305, "sha256": THREADLOCAL_SHA256, "slot": 88},
    "bootstrapRoot": ROOT, "rawLimits": [37, 282358], "diagnosticClassBound": 127,
    "runtimeBaseline": 392934, "runtimeCap": 393216, "globalNativeBindings": 13,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
