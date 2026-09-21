#!/usr/bin/env python3
"""Strict generated-only verifier for bounded ``Integer.toString(int)``.

Only the accepted StringBuilder.append(int) parent and this stage's generated
Java-8 Integer source are inputs. It never opens an original artifact, JAR,
class, resource, checkpoint, or world.
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
parent = stage.parent / "parent-12bfded16"

PARENT_DOMAIN = "MC-SB-APPEND-INT-0002"
DOMAIN = "MC-INTEGER-TO-STRING-P1"
PARENT_ENGINE = "4d432d53422d415050454e442d494e542d303033"
ENGINE = "4d432d494e542d544f535452494e472d30303031"
PARENT_OWNER = "4d432d53422d415050454e442d494e542d303034"
OWNER = "4d432d494e542d544f535452494e472d30303032"
INTEGER_SHA256 = "56b891f66fbab31669688a128b8a888291183461adb3aaf667aba394cd1455a8"
INTEGER_KECCAK = "d850fbfd897244a29a754d0c512a52689db64ecccab14e29e5debb4a09c14225"

PARENT_FILES = {
    "pins.json": "84ef21ec67e50a87d21589eb94293670905438099bcab2e99424c81a167747f0",
    "artifacts/engine/MCEntryInterpreter.sol": "1a92fb787a8099d465f9addb7d61c740df356526f15d15cbc807f90b37dd33dd",
    "artifacts/coordinator/MCEntryCoordinator.sol": "fab36f171e9a42d2e44640373335de0dec23ab59654a6859aff8a92a523df009",
    "canonical-driver.go.txt": "16c3e53dda3baba575d02081c62fbec7ba1cead906be5ea04d90d5029ed8443c",
    "checkpoint_diagnostic.py": "be1651f1dfaa34ccdc4f2947e2669797cf7ea7ea6c72a1612b075b8ad1d0ef6d",
    "checkpoint_frames.py": "be1651f1dfaa34ccdc4f2947e2669797cf7ea7ea6c72a1612b075b8ad1d0ef6d",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(text, old, new):
    assert text.count(old) == 1, (old[:96], text.count(old))
    return text.replace(old, new)


def bootstrap_hex(text, name):
    match = re.search(r"function _bootstrap" + re.escape(name) + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-12bfded16", "parentEvidence": "parent-12bfded16", "sha256": inputs,
}

# This is the entire new guest surface. It delegates only through the retained
# Java-8 StringBuilder append(int) and String conversion path; no formatter,
# radix, unsigned, native, or host code is present.
source = (stage / "bootstrap/java/lang/Integer.java").read_text()
expected_source = """package java.lang;
public final class Integer extends Number implements Comparable<Integer>, java.io.Serializable {
  public static final int MIN_VALUE = 0x80000000;
  public static final int MAX_VALUE = 0x7fffffff;
  public static final int SIZE = 32;
  public static final int BYTES = 4;
  private final int value;
  public Integer(int value) { this.value = value; }
  public Integer(String s) { this.value = parseInt(s); }
  public static Integer valueOf(int value) { return new Integer(value); }
  public static String toString(int value) { return new StringBuilder().append(value).toString(); }
  public static Integer valueOf(String s) { return new Integer(parseInt(s)); }
  public int intValue() { return value; }
  public long longValue() { return (long)value; }
  public float floatValue() { return (float)value; }
  public double doubleValue() { return (double)value; }
  public byte byteValue() { return (byte)value; }
  public short shortValue() { return (short)value; }
  public boolean equals(Object obj) { return obj instanceof Integer && value == ((Integer)obj).value; }
  public int hashCode() { return value; }
  public static int hashCode(int value) { return value; }
  public static int compare(int x, int y) { return x < y ? -1 : (x == y ? 0 : 1); }
  public int compareTo(Integer other) { return compare(value, other.value); }
  public static int parseInt(String s) {
    if (s == null) throw new NumberFormatException();
    int len = s.length();
    if (len == 0) throw new NumberFormatException();
    int i = 0, limit = -MAX_VALUE;
    char first = s.charAt(0);
    if (first == '-') { limit = MIN_VALUE; i++; }
    else if (first == '+') i++;
    if (i == len) throw new NumberFormatException();
    int multmin = limit / 10;
    int result = 0;
    while (i < len) {
      int digit = s.charAt(i++) - '0';
      if (digit < 0 || digit > 9 || result < multmin) throw new NumberFormatException();
      result *= 10;
      if (result < limit + digit) throw new NumberFormatException();
      result -= digit;
    }
    return first == '-' ? result : -result;
  }
}
"""
assert source == expected_source
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
strip_spec = importlib.util.spec_from_file_location("strip_stackmap", here / "strip_stackmap.py")
strip_module = importlib.util.module_from_spec(strip_spec)
strip_spec.loader.exec_module(strip_module)
(root / "build").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="integer-to-string-image-", dir=root / "build") as temporary:
    classes = Path(temporary) / "classes"; classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, stage / "bootstrap/java/lang/Integer.java"], check=True)
    generated = (classes / "java/lang/Integer.class").read_bytes()
cleaned, removed = strip_module.strip_stackmap(generated)
assert len(generated) == 2020 and removed == 61 and len(cleaned) == 1959
assert hashlib.sha256(cleaned).hexdigest() == INTEGER_SHA256
image = bytes.fromhex((stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip())
assert image == cleaned
assert image.count(b"toString") == 1 and image.count(b"(I)Ljava/lang/String;") == 1
assert b"java/lang/StringBuilder" in image and b"append" in image
assert b"(II)Ljava/lang/String;" not in image and b"toUnsignedString" not in image

# Exact source derivation: one existing Integer literal changes, every other
# runtime-derived bootstrap leaf remains dynamic and the accepted parent is
# otherwise byte-for-byte retained except for domain/address identity.
parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
old = re.search(r'    function _bootstrapInteger\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', parent_engine)
assert old and hashlib.sha256(bytes.fromhex(old.group(1))).hexdigest() == "0fb2a617951eb2228ac6277a85ae44da1c59647904d82c2cb68b613c6e33ba03"
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
expected_engine = replace_exact(expected_engine, old.group(0), '    function _bootstrapInteger() private pure returns (bytes memory) { return hex"' + image.hex() + '"; }')
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
assert engine.count(PARENT_DOMAIN) == 0 and engine.count(DOMAIN) == 9
assert engine.count("h[70] = keccak256(_bootstrapInteger());") == 1
assert engine.count("h[0] = keccak256(_bootstrapObject());") == 1
assert engine.count("return keccak256(abi.encode(DBOOT, h));") == 1
assert engine.count("new bytes32[](94)") == 1
assert "DBOOT_INTEGER" not in engine
for fixed in (
    "MAX_RAW_CLASSES = 50;", "MAX_RAW_BYTES = 324338;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(50), uint32(324338)",
):
    assert engine.count(fixed) == 1, fixed

parent_root = json.loads((stage / "parent-root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert parent_root["domain"] == PARENT_DOMAIN and record["domain"] == DOMAIN
assert parent_root["bootstrapCount"] == record["bootstrapCount"] == 94
assert parent_root["order"] == record["order"] and record["order"][70] == "Integer"
assert record["unchangedLeavesRuntimeDerived"] is True
# Node is the pinned local Keccak implementation also used by the artifact build.
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
for item, text in ((parent_root, parent_engine), (record, engine)):
    actual_hashes = []
    for name in item["order"]:
        actual_hashes.append(subprocess.check_output(["node", "-e", 'const {keccak256}=require("js-sha3");process.stdout.write(keccak256(Buffer.from(process.argv[1],"hex")));', bootstrap_hex(text, name)], text=True, env={**os.environ, "NODE_PATH": str(node)}))
    assert actual_hashes == item["keccak256"]
    actual = json.loads(subprocess.check_output(["node", "-e", program], input=json.dumps({"domain": item["domain"], "hashes": actual_hashes}), text=True, env={**os.environ, "NODE_PATH": str(node)}))
    assert actual["dboot"] == item["dboot"] and actual["bootstrapRoot"] == item["bootstrapRoot"]
changed = [i for i, (before, after) in enumerate(zip(parent_root["keccak256"], record["keccak256"])) if before != after]
assert changed == [70]
assert record["integer"] == {"slot": 70, "bytes": 1959, "sha256": INTEGER_SHA256, "keccak256": INTEGER_KECCAK}
assert record["bootstrapRoot"] not in engine and parent_root["bootstrapRoot"] not in engine

parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN and parent_pins["bootstrapCount"] == 94
assert parent_pins["rawLimits"] == [50, 324338] and parent_pins["diagnosticClassBound"] == 144
assert parent_pins["engine"]["bytes"] == 367072 and parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10 and parent_pins["exceptionKinds"] == 14
pre_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
pre_driver = (parent / "canonical-driver.go.txt").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)

if sys.argv[1] == "--prebuild":
    assert len(sys.argv) == 2
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == pre_coordinator
    assert (stage / "tools/Go.txt").read_text() == pre_driver
    phase = "prebuild"
else:
    assert len(sys.argv) == 3 and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
    pins = json.loads(Path(sys.argv[2]).read_text())
    bootstrap = dict(parent_pins["bootstrapSHA256"]); bootstrap["Integer"] = INTEGER_SHA256
    expected = {
        **{key: value for key, value in parent_pins.items() if key != "worker"},
        "basis": "12bfded16", "parentEvidence": "parent-12bfded16", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 367072, "bootstrapCount": 94,
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

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for label in (
    "integer-to-string-min", "integer-to-string-negative-one", "integer-to-string-zero",
    "integer-to-string-positive", "integer-to-string-max", "integer-to-string-uninitialized",
    "integer-to-string-radix-omitted", "integer-to-string-unsigned-omitted",
):
    assert '"' + label + '"' in fixtures and '"' + label + '"' in gate
assert "q_equivalent(label, label, integer_to_string_initialized)" in gate
assert "whole_gate_seconds <= 1200" in gate and "canonical-receipts" in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "phase": phase, "basis": "parent-12bfded16", "domain": DOMAIN,
    "bootstrapImages": 94, "bootstrapRoot": record["bootstrapRoot"],
    "integer": record["integer"], "rawLimits": [50, 324338],
    "diagnosticClassBound": 144, "runtimeBaseline": 367072, "runtimeCap": 393216,
}, indent=2))
