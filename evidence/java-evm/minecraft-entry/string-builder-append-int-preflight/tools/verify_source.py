#!/usr/bin/env python3
"""Strict generated-only verifier for bounded StringBuilder.append(int).

The candidate is derived only from parent-6d49b4e57 plus the locally generated
Java-8 StringBuilder image.  It never opens an original artifact, JAR, class,
resource, or world.
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
parent = stage.parent / "parent-6d49b4e57"
DOMAIN = "MC-SB-APPEND-INT-0001"
PARENT_DOMAIN = "MC-THROWABLE-STACK-TRACE-P3"
ENGINE = "4d432d53422d415050454e442d494e542d303031"
OWNER = "4d432d53422d415050454e442d494e542d303032"
PARENT_ENGINE = "4d432d5448524f5741424c452d54524143452d33"
PARENT_OWNER = "4d432d5448524f5741424c452d54524143452d34"
STRING_BUILDER_SHA256 = "a3d2543ce4401a36011be7bdd8e24ef9ee475f5361c615ab8964456c94728020"
STRING_BUILDER_KECCAK = "e1bef25751c230c7a77ec819c98879e7bab61414b0448348955383e118ae691a"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def builder_function(image):
    return '''    // Exact image84 is retained in one private literal body; the impossible guard prevents viaIR literal duplication.
    function _bootstrapStringBuilder() private pure returns (bytes memory) {
        bytes memory image = hex"%s";
        if (image.length == type(uint256).max) return _bootstrapStringBuilder();
        return image;
    }''' % image.hex()


assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(PARENT_OWNER)) == 20
assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")

# The image is compiled only from this trusted local Java source. StackMapTable
# is Code-local parser-ignored metadata; stripping it leaves methods, CP links,
# fields, and every executable byte intact.
source = stage / "bootstrap/java/lang/StringBuilder.java"
source_text = source.read_text()
for exact in (
    "public StringBuilder append(int value)",
    "private StringBuilder appendNegative(int value)",
    "if (value < 0)", "value = -value;",
    "if (value <= -10)", "appendNegative(value / 10);",
    "return append((char) ('0' - value % 10));",
):
    assert source_text.count(exact) == 1, exact
assert source_text.count("public StringBuilder append(") == 4
assert "append(long" not in source_text and "append(Object" not in source_text
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
strip_spec = importlib.util.spec_from_file_location("strip_stackmap", here / "strip_stackmap.py")
strip_module = importlib.util.module_from_spec(strip_spec)
strip_spec.loader.exec_module(strip_module)
with tempfile.TemporaryDirectory(prefix="sb-append-int-image-", dir=root / "build") as temporary:
    classes = Path(temporary) / "classes"; classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source], check=True)
    generated = (classes / "java/lang/StringBuilder.class").read_bytes()
cleaned, removed = strip_module.strip_stackmap(generated)
assert len(generated) == 1180 and removed == 83 and len(cleaned) == 1097
assert hashlib.sha256(cleaned).hexdigest() == STRING_BUILDER_SHA256
image = bytes.fromhex("".join((stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().split()))
assert image == cleaned and image.hex() == (stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().strip()
assert b"append" in image and b"(I)Ljava/lang/StringBuilder;" in image
assert image.count(b"(I)Ljava/lang/StringBuilder;") == 1
assert b"(J)Ljava/lang/StringBuilder;" not in image and b"(Ljava/lang/Object;)Ljava/lang/StringBuilder;" not in image
assert b"java/lang/Integer" not in image and b"toString" in image

# Apart from the fresh domain and the one guarded StringBuilder literal, the
# interpreter is byte-for-byte parent source. The guard can never recurse:
# a bytes length cannot equal uint256.max. It exists only to keep solc/viaIR
# from duplicating the fixed literal body.
parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
old = re.search(r'    function _bootstrapStringBuilder\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}', parent_engine)
assert old is not None
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
expected_engine = expected_engine.replace(old.group(0), builder_function(image))
assert engine == expected_engine
assert engine.count("function _bootstrapStringBuilder()") == 1
assert engine.count("_bootstrapStringBuilder()") == 4  # root, materializer, declaration, unreachable guard
assert engine.count("image.length == type(uint256).max") == 2  # retained Throwable guard plus StringBuilder guard
assert engine.count("h[84] = keccak256(_bootstrapStringBuilder());") == 1
assert "DBOOT_STRING_BUILDER" not in engine
assert engine.count("h[0] = keccak256(_bootstrapObject());") == 1
assert engine.count("return keccak256(abi.encode(DBOOT, h));") == 1
assert engine.count("new bytes32[](94)") == 1
for fixed in (
    "MAX_RAW_CLASSES = 50;", "MAX_RAW_BYTES = 324338;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(50), uint32(324338)",
):
    assert engine.count(fixed) == 1, fixed

# The root is independently derived from ordered leaves. Only image84 changes;
# no whole root, Object leaf, or all-leaf folding is accepted.
parent_root = json.loads((stage / "parent-root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert parent_root["domain"] == PARENT_DOMAIN and parent_root["bootstrapCount"] == 94
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 94
assert record["order"] == parent_root["order"] and record["unchangedLeavesRuntimeDerived"] is True
changed = [i for i, (before, after) in enumerate(zip(parent_root["keccak256"], record["keccak256"])) if before != after]
assert changed == [84]
assert record["stringBuilder"] == {"slot": 84, "bytes": 1097, "sha256": STRING_BUILDER_SHA256, "keccak256": STRING_BUILDER_KECCAK}
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
for item in (parent_root, record):
    actual = json.loads(subprocess.check_output(["node", "-e", program], input=json.dumps({"domain": item["domain"], "hashes": item["keccak256"]}), text=True, env={**os.environ, "NODE_PATH": str(node)}))
    assert actual["dboot"] == item["dboot"] and actual["bootstrapRoot"] == item["bootstrapRoot"]
assert record["bootstrapRoot"] not in engine and parent_root["bootstrapRoot"] not in engine

parent_pins = json.loads((parent / "pins.json").read_text())
parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
pre_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
parent_driver = (parent / "canonical-driver.go.txt").read_text()
pre_driver = parent_driver.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)

if sys.argv[1] == "--prebuild":
    assert len(sys.argv) == 2
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == pre_coordinator
    assert (stage / "tools/Go.txt").read_text() == pre_driver
    phase = "prebuild"
else:
    assert len(sys.argv) == 3 and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
    pins = json.loads(Path(sys.argv[2]).read_text())
    bootstrap = dict(parent_pins["bootstrapSHA256"]); bootstrap["StringBuilder"] = STRING_BUILDER_SHA256
    expected = {
        **{key: value for key, value in parent_pins.items() if key != "worker"},
        "basis": "6d49b4e57", "parentEvidence": "parent-6d49b4e57", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393145, "bootstrapCount": 94,
        "bootstrapSHA256": bootstrap, "diagnosticClassBound": 144,
        "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
    assert pins["coordinator"]["bytes"] == parent_pins["coordinator"]["bytes"] == 5394
    coordinator = replace_exact(pre_coordinator, parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coordinator
    driver = pre_driver
    for before, after in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        driver = replace_exact(driver, before, after)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        driver, count = re.subn(pattern, replacement, driver)
        assert count == 1
    assert (stage / "tools/Go.txt").read_text() == driver
    phase = "built"

# Focused fixtures are trusted Java-8 sources only. The gate must exercise all
# required signed cases under q1/q7/direct/reopen and keep omitted long/Object
# overloads as atomic member-resolution refusals.
fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for label in (
    "stringbuilder-append-int-min", "stringbuilder-append-int-negative-one",
    "stringbuilder-append-int-zero", "stringbuilder-append-int-positive",
    "stringbuilder-append-int-max", "stringbuilder-append-int-existing-prefix",
    "stringbuilder-append-long-omitted", "stringbuilder-append-object-omitted",
):
    assert '"' + label + '"' in fixtures and '"' + label + '"' in gate
assert 'q_equivalent(label, label, stringbuilder_append_int_initialized)' in gate
assert "whole_gate_seconds <= 1200" in gate and "canonical-receipts" in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "phase": phase, "basis": "parent-6d49b4e57", "domain": DOMAIN,
    "bootstrapImages": 94, "bootstrapRoot": record["bootstrapRoot"],
    "stringBuilder": record["stringBuilder"], "rawLimits": [50, 324338],
    "diagnosticClassBound": 144, "runtimeBaseline": 393145, "runtimeCap": 393216,
}, indent=2))
