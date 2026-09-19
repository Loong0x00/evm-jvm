#!/usr/bin/env python3
"""Strict source invariants for the bounded StringBuilder CharSequence range stage.

The accepted parent is parent-baeda70ed.  This verifier opens only checked-in
parent/stage sources and the pinned local JDK/compiler dependency.  The only
semantic guest-image change is bootstrap slot84.  The narrowly listed
unchecked increments are layout-only: their pre-existing bounded guards make
uint256 overflow unreachable, and their exact source replacement is checked
against the parent below.
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
parent = stage.parent / "parent-baeda70ed"

PARENT = {
    "artifacts/engine/MCEntryInterpreter.sol": "9f3913701c3fc7900a79d4ba4f7eb48ba0a18e5226d80183fd204b65c2185d53",
    "artifacts/coordinator/MCEntryCoordinator.sol": "75eca38f3b3b466551199757322859704a6074672088b802eaba2c9a0dc9bb71",
    "canonical-driver.go.txt": "8722ecd1011df241238e538fc1a5a79109fdb381949ab31a152765474cd19d5c",
    "checkpoint_diagnostic.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "checkpoint_frames.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-SB-SETLENGTH-ZERO-Q"
DOMAIN = "MC-SB-CHARSEQ-RANGE0-P"
PARENT_ENGINE = "4d432d53422d5345544c454e475448302d454e48"
PARENT_OWNER = "4d432d53422d5345544c454e475448302d4f574f"
ENGINE = "4d432d53422d434841525345512d52414e474530"
OWNER = "4d432d53422d434841525345512d52414e474531"
STRINGBUILDER_SHA256 = "22ca3088c0cebccc5714beefd40cf187dbaebe5930477559e20ab8709249ffa4"
STRINGBUILDER_KECCAK = "6069d70bb5d5e461adeea43ae48b2be1d2f582dfdd5fd97a159b8a03492c354c"
ROOT = "cd603ccfebe00cbc0df9b81f65165af6c411d18470cf2839e00ff08abde524fb"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_images(text):
    result = {}
    for name, image in re.findall(
        r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{[\s\S]*?return hex\"([0-9a-f]+)\";",
        text, re.S,
    ):
        assert name not in result
        result[name] = image
    return result


def root_rows(text):
    begin = text.index("    function _bootstrapRoot() private pure returns (bytes32) {")
    end = text.index("\n    function _prepare(", begin)
    rows = re.findall(r"h\[(\d+)\] = ([^;]+);", text[begin:end])
    assert len(rows) == 90
    assert [int(index) for index, _ in rows] == list(range(90))
    return rows, text[begin:end]


def root_order(rows):
    special = {"DBOOT_ENUMSET": "EnumSet", "DBOOT_ITERABLE": "Iterable", "DBOOT_MATH": "Math"}
    result = []
    for _, value in rows:
        found = re.search(r"_bootstrap(\w+)\(\)", value)
        result.append(found.group(1) if found else special[value.strip()])
    return result


def commitment(images, order):
    node_modules = root / "jvmevm/runtime/node_modules"
    assert node_modules.is_dir(), "refusing shared or network Node dependencies"
    payload = {"domain": DOMAIN, "images": [images["_bootstrap" + name] for name in order]}
    script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8"));const word=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};
const h=x.images.map(v=>keccak256(Buffer.from(v,"hex")));const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));
const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),word(64),word(h.length),...h.map(v=>Buffer.from(v,"hex"))]));
process.stdout.write(JSON.stringify({dboot:d,root:r,hashes:h}));'''
    result = subprocess.run(
        ["node", "-e", script], input=json.dumps(payload), text=True, capture_output=True, check=True,
        env={**os.environ, "NODE_PATH": str(node_modules)},
    )
    return json.loads(result.stdout)


SOURCE = """package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), append of a
 * validated String-backed CharSequence range, reset, and copy-producing toString.
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
        int prefix = value.length;
        int length = input.length();
        char[] next = new char[prefix + length];
        while (prefix != 0) {
            next[--prefix] = value[prefix];
        }
        while (length != 0) {
            next[value.length + --length] = input.charAt(length);
        }
        value = next;
        return this;
    }

    public StringBuilder append(CharSequence input, int start, int end) {
        if (!(input instanceof String) || start < 0 || end < start || end > ((String) input).length()) {
            throw new IllegalArgumentException();
        }
        char[] slice = new char[end - start];
        while (end != start) {
            slice[--end - start] = ((String) input).charAt(end);
        }
        return append(new String(slice));
    }

    public String toString() {
        return new String(value);
    }

    public void setLength(int length) {
        if (length != 0) {
            throw new IllegalArgumentException();
        }
        value = new char[0];
    }
}
"""

inputs = {name: digest(parent / name) for name in PARENT}
assert inputs == PARENT
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "baeda70ed", "parentEvidence": "parent-baeda70ed", "sha256": inputs,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(PARENT_OWNER)) == 20
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["engine"]["bytes"] == 393206 and parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [37, 282358]
assert parent_pins["diagnosticClassBound"] == 127 and parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10 and parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/StringBuilder.java").read_text()
assert source == SOURCE
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-builder-charsequence-range-verify-", dir=root / "build") as temp_name:
    temp = Path(temp_name); src = temp / "java/lang/StringBuilder.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = temp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/StringBuilder.class").read_bytes()
assert len(image) == 914 and hashlib.sha256(image).hexdigest() == STRINGBUILDER_SHA256
assert image.hex() == (stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"append", b"java/lang/CharSequence", b"java/lang/String", b"setLength", b"java/lang/IllegalArgumentException"):
    assert required in image
for forbidden in (b"append(I", b"append(Ljava/lang/CharSequence;)L", b"substring", b"StringBuffer", b"AbstractStringBuilder", b"ensureCapacity", b"capacity", b"Serializable"):
    assert forbidden not in image

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_images = source_images(parent_engine); images = source_images(engine)
old_stringbuilder = parent_images["_bootstrapStringBuilder"]
assert len(bytes.fromhex(old_stringbuilder)) == 736
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN).replace(old_stringbuilder, image.hex())
for old, new, expected in (
    ("++f.pc;", "unchecked { ++f.pc; }", 6),
    ("++depth;", "unchecked { ++depth; }", 8),
    ("++executedInternalSteps;", "unchecked { ++executedInternalSteps; }", 3),
    ("++state.totalInternalSteps;", "unchecked { ++state.totalInternalSteps; }", 3),
    ("++executedJvmSteps;", "unchecked { ++executedJvmSteps; }", 1),
    ("++state.totalJvmSteps;", "unchecked { ++state.totalJvmSteps; }", 1),
    ("++nextHandle;", "unchecked { ++nextHandle; }", 5),
    ("++arena.ordinaryObjectCount;", "unchecked { ++arena.ordinaryObjectCount; }", 6),
    ("++arena.ordinaryArrayCount;", "unchecked { ++arena.ordinaryArrayCount; }", 5),
    ("++arena.objectCount;", "unchecked { ++arena.objectCount; }", 1),
):
    assert expected_engine.count(old) == expected
    expected_engine = expected_engine.replace(old, new)
assert engine == expected_engine
assert set(images) == set(parent_images)
for name, old in parent_images.items():
    assert images[name] == (image.hex() if name == "_bootstrapStringBuilder" else old), name
rows, root_source = root_rows(engine)
parent_rows, _ = root_rows(parent_engine)
assert rows == parent_rows and root_order(rows)[84] == "StringBuilder"
assert "h[84] = keccak256(_bootstrapStringBuilder());" in root_source
assert "return keccak256(abi.encode(DBOOT, h));" in root_source
assert 'return hex"' + ROOT + '";' not in engine
# Counter caps precede the layout-only unchecked increments.  The exact source
# equality above prevents any other engine edit or commitment weakening.
for fixed in (
    "MAX_RAW_CLASSES = 37;", "MAX_RAW_BYTES = 282358;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(37), uint32(282358)", "_appendStringBuilderBootstrap(p.classes, classSlot + 45);",
):
    assert engine.count(fixed) == 1, fixed
record = commitment(images, root_order(rows))
root_record = json.loads((stage / "root-commitment.json").read_text())
assert record["root"] == ROOT == root_record["bootstrapRoot"]
assert record["dboot"] == root_record["dboot"] and record["hashes"] == root_record["keccak256"]
assert root_record["domain"] == DOMAIN and root_record["order"] == root_order(rows)
assert root_record["stringBuilder"] == {"slot": 84, "bytes": 914, "sha256": STRINGBUILDER_SHA256, "keccak256": STRINGBUILDER_KECCAK}
assert record["hashes"][84] == STRINGBUILDER_KECCAK

coordinator_parent = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = coordinator_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1

driver_parent = (parent / "canonical-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE).replace("0x" + PARENT_OWNER, "0x" + OWNER)
assert driver.count(DOMAIN) == 6 and driver.count("0x" + ENGINE) == 1 and driver.count("0x" + OWNER) == 1
for stage_name, parent_name in (("checkpoint_diagnostic.py", "checkpoint_diagnostic.py"), ("checkpoint_frames.py", "checkpoint_frames.py"), ("verify_receipts.js", "verify_receipts.js")):
    assert (stage / "tools" / stage_name).read_bytes() == (parent / parent_name).read_bytes()
for stage_name, parent_name in (("engine/build.js", "artifacts/engine/build.js"), ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / stage_name).read_bytes() == (parent / parent_name).read_bytes()

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for text in (fixtures, gate):
    assert "original" in text  # inherited generated-only guard wording; no input is opened.
for label in ("stringbuilder-charsequence-range", "stringbuilder-charsequence-refusal", "stringbuilder-append-charsequence-omitted"):
    assert 'build("' + label + '"' in fixtures
assert 'q_equivalent("stringbuilder-charsequence-range", "stringbuilder-charsequence-range", stringbuilder_charsequence_initialized)' in gate
assert 'q_equivalent("stringbuilder-charsequence-refusal", "stringbuilder-charsequence-refusal", stringbuilder_charsequence_initialized)' in gate
assert STRINGBUILDER_SHA256 in gate

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
        "basis": "baeda70ed", "parentEvidence": "parent-baeda70ed", "phase": "built", "domain": DOMAIN,
        "runtimeBaseline": 393206, "runtimeCap": 393216, "bootstrapCount": 90,
        "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "StringBuilder": STRINGBUILDER_SHA256},
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
        "externalLocalGas": 1000000000, "reserve": 25000000, "rawLimits": [37, 282358],
        "checkpointCap": 1048576, "headCap": 32768, "diagnosticClassBound": 127,
        "address": "0x" + ENGINE, "owner": "0x" + OWNER, "limitsCommitment": parent_pins["limitsCommitment"],
        "compiler": parent_pins["compiler"], "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
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
    assert driver == final_driver and json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-baeda70ed", "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "stringBuilder": {"slot": 84, "bytes": 914, "sha256": STRINGBUILDER_SHA256},
    "bootstrapRoot": ROOT, "rawLimits": [37, 282358], "diagnosticClassBound": 127,
    "runtimeBaseline": 393206, "runtimeCap": 393216, "globalNativeBindings": 13,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
