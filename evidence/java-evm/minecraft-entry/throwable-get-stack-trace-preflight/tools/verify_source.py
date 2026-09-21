#!/usr/bin/env python3
"""Strict generated-only pins for bounded Throwable.getStackTrace().

The candidate is derived from parent-66b1622a2.  Apart from fresh local
commitment domains and rebuilt EVM address/code-hash pins, image5 is the sole
interpreter delta.  This verifier never opens an original JAR, class, resource,
or world.
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
parent = stage.parent / "parent-66b1622a2"
parent_root = stage / "parent-root-commitment.json"
DOMAIN = "MC-THROWABLE-STACK-TRACE-P2"
PARENT_DOMAIN = "MC-SECURITY-MANAGER-LINK-P2"
ENGINE = "4d432d5448524f5741424c452d54524143452d31"
OWNER = "4d432d5448524f5741424c452d54524143452d32"
PARENT_ENGINE = "4d432d5345434d47522d4c494e4b2d50322d4558"
PARENT_OWNER = "4d432d5345434d47522d4c494e4b2d50322d4f58"
THROWABLE_SHA256 = "6ea5d86706a5ac3aabc7a7452f746bd9c3209483ee16f1c83948dbe7bd2a0d79"
THROWABLE_KECCAK = "8d0f6e80f1ee4a0a9713d4abb4149e703a6de72e9886e5e74e048c0c6a576533"
THROWABLE_SOURCE = """package java.lang;
public class Throwable implements java.io.Serializable {
    private String detailMessage;
    private Throwable cause;
    public Throwable() { super(); cause = this; }
    public Throwable(String message) { super(); cause = this; detailMessage = message; }
    public String getMessage() { return detailMessage; }
    public Throwable getCause() { return cause == this ? null : cause; }
    public void printStackTrace(java.io.PrintStream stream) { if (detailMessage != null) stream.println(detailMessage); }
    public StackTraceElement[] getStackTrace() { return new StackTraceElement[0]; }
}
"""


def read(relative):
    return (stage / relative).read_text()


def parent_read(relative):
    return (parent / relative).read_text()


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def throwable_hex(source):
    match = re.search(
        r"function _bootstrapThrowable\(\) private pure returns \(bytes memory\) \{\n\s*bytes memory image = hex\"([0-9a-f]+)\";\n\s*if \(image\.length == type\(uint256\)\.max\) return _bootstrapThrowable\(\);",
        source,
    )
    assert match
    return match.group(1)


# Java 8 source is generated locally; it is never executed on the host.  The
# compiler output proves the literal represents exactly this limited surface.
source = stage / "bootstrap/java/lang/Throwable.java"
hex_file = stage / "bootstrap/java/lang/Throwable.class.hex"
assert source.read_text() == THROWABLE_SOURCE
image = bytes.fromhex(hex_file.read_text().strip())
assert len(image) == 772 and hashlib.sha256(image).hexdigest() == THROWABLE_SHA256
assert image.hex() == hex_file.read_text().strip()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="throwable-get-stack-trace-image-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    classes = tmp / "classes"; classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source], check=True)
    rebuilt = (classes / "java/lang/Throwable.class").read_bytes()
assert rebuilt == image
assert b"getStackTrace" in image and b"()[Ljava/lang/StackTraceElement;" in image
assert image.count(b"getStackTrace") == 1 and image.count(b"StackTraceElement") == 2
# The sole new method has iconst_0, anewarray #5, areturn.  No frame/cause/
# suppression metadata or StackTraceElement member is present.
assert bytes.fromhex("03bd0005b0") in image
for forbidden in (b"fillInStackTrace", b"setStackTrace", b"getSuppressed", b"addSuppressed", b"getClassName", b"getMethodName"):
    assert forbidden not in image

# No interpreter behavior changed beyond the exact image5 bytes and the fresh
# local domain.  In particular the ordered root remains dynamically assembled:
# Object and every inherited materializing call retain the parent source form.
parent_engine = parent_read("artifacts/engine/MCEntryInterpreter.sol")
engine = read("engine/MCEntryInterpreter.sol")
old_image = throwable_hex(parent_engine)
assert len(bytes.fromhex(old_image)) == 657
expected_engine = replace_exact(parent_engine, PARENT_DOMAIN, DOMAIN, 9)
expected_engine = replace_exact(expected_engine, old_image, image.hex())
assert engine == expected_engine
assert engine.count("h[0] = keccak256(_bootstrapObject());") == 1
assert engine.count("h[5] = keccak256(_bootstrapThrowable());") == 1
assert "DBOOT_THROWABLE" not in engine and "DBOOT_OBJECT" not in engine
assert "bytes32[] memory h = new bytes32[](94);" in engine
assert "return keccak256(abi.encode(DBOOT, h));" in engine
for fixed in (
    "MAX_RAW_CLASSES = 50;", "MAX_RAW_BYTES = 324338;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(50), uint32(324338)",
):
    assert engine.count(fixed) == 1, fixed

# The preserved parent root record is a leaf-by-leaf commitment.  Only slot5
# changes; recompute this candidate root independently instead of accepting a
# folded whole-root value from Solidity.
base = json.loads(parent_root.read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert base["bootstrapCount"] == 94 and len(base["keccak256"]) == 94
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 94
assert record["order"] == base["order"] and record["unchangedLeavesRuntimeDerived"] is True
assert record["parentRootEvidence"] == "security-manager-link-preflight/root-commitment.json"
expected_hashes = list(base["keccak256"]); expected_hashes[5] = THROWABLE_KECCAK
assert record["keccak256"] == expected_hashes
assert record["throwable"] == {"slot": 5, "bytes": 772, "sha256": THROWABLE_SHA256, "keccak256": THROWABLE_KECCAK}
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const root=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,root}));'''
actual = json.loads(subprocess.check_output(["node", "-e", script], input=json.dumps({"domain": DOMAIN, "hashes": expected_hashes}), text=True, env={**os.environ, "NODE_PATH": str(node)}))
assert record["dboot"] == actual["dboot"] and record["bootstrapRoot"] == actual["root"]
assert record["bootstrapRoot"] not in engine

# Coordinator and raw ABI driver differ only in fresh identities plus rebuilt
# ordinary EVM code pins.  The prebuild form contains parent code hashes; the
# built form contains the pinned candidate artifact hashes.
parent_pins = json.loads(parent_read("pins.json"))
coordinator_parent = parent_read("artifacts/coordinator/MCEntryCoordinator.sol")
coordinator = read("coordinator/MCEntryCoordinator.sol")
coordinator_base = replace_exact(replace_exact(coordinator_parent, PARENT_DOMAIN, DOMAIN, 4), PARENT_ENGINE, ENGINE)
driver_parent = parent_read("canonical-driver.go.txt")
driver_base = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE).replace("0x" + PARENT_OWNER, "0x" + OWNER)

assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
if sys.argv[1] == "--prebuild":
    assert len(sys.argv) == 2
    assert coordinator == coordinator_base
    assert read("tools/Go.txt") == driver_base
    phase = "prebuild"
else:
    assert len(sys.argv) == 3 and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
    pins = json.loads(Path(sys.argv[2]).read_text())
    expected_pins = {
        **{key: value for key, value in parent_pins.items() if key != "worker"},
        "basis": "66b1622a2", "parentEvidence": "parent-66b1622a2", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393007, "bootstrapCount": 94,
        "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "Throwable": THROWABLE_SHA256},
        "diagnosticClassBound": 144, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
    assert pins["engine"]["bytes"] > 393007 and pins["coordinator"]["bytes"] == 5394
    expected_coordinator = replace_exact(coordinator_base, parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert coordinator == expected_coordinator
    expected_driver = driver_base
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        expected_driver = replace_exact(expected_driver, old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        expected_driver, changed = re.subn(pattern, replacement, expected_driver)
        assert changed == 1
    assert read("tools/Go.txt") == expected_driver
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

# Generated fixture/gate sources contain the focused q1/q7/direct/reopen,
# dormant-image, and raw-replacement checks.  No stage file may embed original
# program data; generated fixture classes exist only under ignored build/ paths.
fixtures = read("tools/generate_fixtures.py")
gate = read("tools/gate.py")
for label in ("throwable-get-stack-trace", "throwable-get-stack-trace-uninitialized", "raw-throwable-get-stack-trace"):
    assert '"' + label + '"' in fixtures and '"' + label + '"' in gate
assert 'q_equivalent("throwable-get-stack-trace", "throwable-get-stack-trace", throwable_get_stack_trace_initialized)' in gate
assert 'raw + 90 not in states' in gate and ' + 5 not in states' in gate
assert 'raw-throwable-get-stack-trace-replacement' in gate
assert "java-diff-mc-throwable-get-stack-trace-" in read("tools/build.py")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))

print(json.dumps({
    "phase": phase, "basis": "parent-66b1622a2", "domain": DOMAIN,
    "bootstrapImages": 94, "bootstrapRoot": record["bootstrapRoot"],
    "throwable": record["throwable"], "rawLimits": [50, 324338],
    "diagnosticClassBound": 144, "runtimeBaseline": 393007, "runtimeCap": 393216,
}, indent=2))
