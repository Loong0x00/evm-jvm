#!/usr/bin/env python3
"""Strict generated-source invariants for bounded Java 8 StringBuilder(int).

The only runtime semantic delta from accepted parent-7227a13b1 is bootstrap
slot84's StringBuilder image. This verifier reads generated stage/parent sources
and pinned local tools only; it never opens an original artifact, JAR, class,
resource, checkpoint, or world.
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
parent = stage.parent / "thread-local-get-preflight"

PARENT = {
    "engine/MCEntryInterpreter.sol": "761bd06928879ebda9defdffaa6d1e1c25fa8871e6c5886b0e894798008ba593",
    "coordinator/MCEntryCoordinator.sol": "96f1d313f85dc341eb21f9908a94b4e0649ea7495c632c431d9ddf65d86b07aa",
    "tools/Go.txt": "016d58c299729883dae633217b280ef22418839dd5fb6f70a4f032d6f510d858",
    "tools/checkpoint_diagnostic.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "tools/checkpoint_frames.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "tools/verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-THREAD-LOCAL-GET-P1"
DOMAIN = "MC-SB-CAPACITY-CTOR-P1"
PARENT_ENGINE = "4d432d5448524541444c4f43414c2d4745542d45"
ENGINE = "4d432d53422d43415041434954592d4354522d45"
PARENT_OWNER = "4d432d5448524541444c4f43414c2d4745542d4f"
OWNER = "4d432d53422d43415041434954592d4354522d4f"
STRING_BUILDER_SHA256 = "57eac8ab607a23fbb0a06a6af655321b7cf634b3d8c448d4c36fbaac99994fd9"
STRING_BUILDER_KECCAK = "a215af9a57e80a3de173a5909687cab6068a4e4922fbbe798c96eaadc9cb23f7"
ROOT = "842464491035a9f67034b5c943f785230649c0d5c59e66532a91826192bc5945"


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


def expected_engine(parent_engine, old_builder, new_builder):
    assert parent_engine.count(PARENT_DOMAIN) == 9
    assert parent_engine.count(old_builder) == 1
    changed = parent_engine.replace(PARENT_DOMAIN, DOMAIN).replace(old_builder, new_builder)
    return changed


inputs = {name: digest(parent / name) for name in PARENT}
assert inputs == PARENT
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == 20
assert len(bytes.fromhex(PARENT_OWNER)) == len(bytes.fromhex(OWNER)) == 20
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-7227a13b1", "parentEvidence": "thread-local-get-preflight", "sha256": inputs,
}
parent_pins = json.loads((parent / "build-pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [37, 282358]
assert parent_pins["diagnosticClassBound"] == 127 and parent_pins["engine"]["bytes"] == 392834
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/StringBuilder.java").read_text()
assert source == """package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), and toString.
 * Logical content owns an exact-length char array; capacity remains unexposed.
 */
public final class StringBuilder {
    private char[] value;

    public StringBuilder() {
        value = new char[0];
    }

    public StringBuilder(int capacity) {
        if (capacity < 0) {
            value = new char[capacity];
        } else {
            value = new char[0];
        }
    }

    public StringBuilder append(String input) {
        char[] next = new char[value.length + input.length()];
        for (int index = 0; index < value.length; index++) {
            next[index] = value[index];
        }
        for (int index = 0; index < input.length(); index++) {
            next[value.length + index] = input.charAt(index);
        }
        value = next;
        return this;
    }

    public String toString() {
        return new String(value);
    }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-builder-capacity-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/StringBuilder.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/StringBuilder.class").read_bytes()
assert len(image) == 624 and hashlib.sha256(image).hexdigest() == STRING_BUILDER_SHA256
assert image.hex() == (stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
# The capacity constructor has only the logical-content representation: it
# allocates char[0] for every nonnegative argument and uses ordinary newarray
# for a negative argument, so the guest interpreter raises NASE itself.
assert bytes.fromhex("1b9c") in image and bytes.fromhex("1bbc05") in image and bytes.fromhex("2a03bc05") in image
for forbidden in (b"capacity", b"ensureCapacity", b"setLength", b"AbstractStringBuilder", b"Serializable"):
    assert forbidden not in image
for required in (b"append", b"toString", b"java/lang/String", b"java/lang/Object", b"[C"):
    assert required in image

parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_images = source_images(parent_engine)
images = source_images(engine)
old_builder = parent_images["_bootstrapStringBuilder"]
assert len(bytes.fromhex(old_builder)) == 542
assert engine == expected_engine(parent_engine, old_builder, image.hex())
assert set(images) == set(parent_images)
for name, old in parent_images.items():
    assert images[name] == (image.hex() if name == "_bootstrapStringBuilder" else old), name
rows, root_source = root_rows(engine)
parent_rows, _ = root_rows(parent_engine)
assert rows == parent_rows and root_order(rows)[84] == "StringBuilder"
assert "h[84] = keccak256(_bootstrapStringBuilder());" in root_source
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
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "classes[at].data = _bootstrapStringBuilder();",
):
    assert engine.count(fixed) == 1, fixed
record = commitment(images, root_order(rows))
assert record["root"] == ROOT and record["hashes"][84] == STRING_BUILDER_KECCAK

coordinator_parent = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = coordinator_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1

driver_parent = (parent / "tools/Go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = (driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
                   .replace("0x" + PARENT_OWNER, "0x" + OWNER))
assert driver.count(DOMAIN) == 6 and driver.count("0x" + ENGINE) == driver.count("0x" + OWNER) == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / "tools" / name).read_bytes()
for name in ("engine/build.js", "coordinator/build.js"):
    assert (stage / name).read_bytes() == (parent / name).read_bytes()

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for text in (fixtures, gate):
    assert "original" in text
assert 'for capacity in (0, 1, 255):' in fixtures and 'stringbuilder-capacity-%d' in fixtures
for label in ("stringbuilder-capacity-negative", "stringbuilder-capacity-omitted",
              "stringbuilder-ensurecapacity-omitted", "stringbuilder-setlength-omitted", "stringbuilder-append-int-omitted"):
    assert label in fixtures and label in gate
for label in ("stringbuilder-capacity-0", "stringbuilder-capacity-1", "stringbuilder-capacity-255"):
    assert label in gate
assert 'q_equivalent(label, label, stringbuilder_capacity_initialized)' in gate
assert STRING_BUILDER_SHA256 in gate

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
        "basis": "parent-7227a13b1", "parentEvidence": "thread-local-get-preflight", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 392834, "runtimeCap": 393216,
        "bootstrapCount": 90, "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "StringBuilder": STRING_BUILDER_SHA256},
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
    "acceptedParent": "parent-7227a13b1", "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "stringBuilder": {"bytes": 624, "sha256": STRING_BUILDER_SHA256, "slot": 84},
    "bootstrapRoot": ROOT, "rawLimits": [37, 282358], "diagnosticClassBound": 127,
    "runtimeBaseline": 392834, "runtimeCap": 393216, "globalNativeBindings": 13,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
