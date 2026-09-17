#!/usr/bin/env python3
"""Strict source verifier for bounded ``Integer.valueOf(String)``.

The only accepted basis is the accepted WeakReference parent ``parent-cb0c15e54``.
Only the existing Java-8 Integer bootstrap image is replaced; generated fixtures
are the sole Java inputs. No original artifact, class, JAR, resource, checkpoint,
or world is opened.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-cb0c15e54"

PARENT_FILES = {
    "pins.json": "81c1628f0424f96afa56f2a1401dded9ab67d68d674d7a03c13d001bd156b33c",
    "artifacts/engine/MCEntryInterpreter.sol": "879a911f812e59d3a1ba302d290150ccae922db8a1194efc1633b6b9eacc9848",
    "artifacts/coordinator/MCEntryCoordinator.sol": "a3732e5a1c6f1720fa102a2f03dc8557a66472143871fdca409f7f61f427631f",
    "executed-driver.go.txt": "86d55dce962bfd19325382797025a03eca8e08bd253d21ba3263bd4897be935d",
    "checkpoint_diagnostic.py": "a0936f5451b3771110ff83df6e912a2d9fc627a81aec44bad4faad8e30faa808",
    "checkpoint_frames.py": "a0936f5451b3771110ff83df6e912a2d9fc627a81aec44bad4faad8e30faa808",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-WEAK-REFERENCE-P2"
DOMAIN = "MC-INTEGER-VALUE-OF-STRING-P1"
PARENT_ENGINE = "4d432d5745414b2d5245464552454e43452d5032"
ENGINE = "4d432d494e54454745522d535452494e472d5031"
PARENT_OWNER = "4d432d5745414b2d5245464552454e43452d4f32"
OWNER = "4d432d494e54454745522d535452494e472d4f31"
INTEGER_SHA256 = "0fb2a617951eb2228ac6277a85ae44da1c59647904d82c2cb68b613c6e33ba03"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(text, name):
    match = re.search(r"function _bootstrap" + name + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


def initial_engine(text, image_hex):
    assert text.count(PARENT_DOMAIN) == 9
    old = re.search(r"function _bootstrapInteger\(\) private pure returns \(bytes memory\) \{ return hex\"([0-9a-f]+)\"; \}", text)
    assert old and hashlib.sha256(bytes.fromhex(old.group(1))).hexdigest() == "1b0b1b25e935a2065f2af4d7e3bb1caa677fe08b16247c9d4a0cfbd0abd1d5c6"
    replacement = 'function _bootstrapInteger() private pure returns (bytes memory) { return hex"' + image_hex + '"; }'
    result = text[:old.start()] + replacement + text[old.end():]
    result = result.replace(PARENT_DOMAIN, DOMAIN)
    assert result.count(DOMAIN) == 9
    return result


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
    assert result.count(DOMAIN) == 4 and result.count(ENGINE) == 1
    return result


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)
    assert result.count(DOMAIN) == 6 and result.count(ENGINE) == result.count(OWNER) == 1
    return result


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 5394", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 391765", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 391765", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-cb0c15e54", "parentEvidence": "parent-cb0c15e54", "sha256": inputs,
}
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 87
assert parent_pins["rawLimits"] == [33, 262158]
assert parent_pins["diagnosticClassBound"] == 120
assert parent_pins["engine"]["bytes"] == 391765
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

source = (stage / "bootstrap/java/lang/Integer.java").read_text()
assert source == """package java.lang;
public final class Integer extends Number implements Comparable<Integer>, java.io.Serializable {
  public static final int MIN_VALUE = 0x80000000;
  public static final int MAX_VALUE = 0x7fffffff;
  public static final int SIZE = 32;
  public static final int BYTES = 4;
  private final int value;
  public Integer(int value) { this.value = value; }
  public Integer(String s) { this.value = parseInt(s); }
  public static Integer valueOf(int value) { return new Integer(value); }
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
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="integer-value-of-string-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/Integer.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    integer_image = (out / "java/lang/Integer.class").read_bytes()
assert len(integer_image) == 1827 and hashlib.sha256(integer_image).hexdigest() == INTEGER_SHA256
assert integer_image.hex() == (stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip()
assert integer_image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/lang/Integer", b"java/lang/Number", b"java/lang/NumberFormatException", b"valueOf",
                 b"(I)Ljava/lang/Integer;", b"(Ljava/lang/String;)Ljava/lang/Integer;", b"parseInt",
                 b"(Ljava/lang/String;)I", b"java/lang/String", b"length", b"charAt"):
    assert required in integer_image, required
for forbidden in (b"(Ljava/lang/String;I)Ljava/lang/Integer;", b"IntegerCache", b"toString", b"decode", b"getInteger"):
    assert forbidden not in integer_image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine, integer_image.hex())
assert len(bytes.fromhex(bootstrap(engine, "Integer"))) == 1827
assert hashlib.sha256(bytes.fromhex(bootstrap(engine, "Integer"))).hexdigest() == INTEGER_SHA256
for fixed in (
    "MAX_RAW_CLASSES = 33;", "MAX_RAW_BYTES = 262158;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](87)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(33), uint32(262158)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[70] = keccak256(_bootstrapInteger());",
    "h[86] = keccak256(_bootstrapWeakReference());", "p.classes[classSlot + 31].data = _bootstrapInteger();",
    "p.classes[classSlot + 47].data = _bootstrapWeakReference();",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator(parent_coordinator)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert coordinator.count("[33]") == 4 and coordinator.count("n > 33") == 1
assert coordinator.count("if (size == 0 || size > 262158)") == 1
assert coordinator.count("if (uint256(total) + size > 262158)") == 1

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 33") == 1 and driver.count("len(parts) > 33") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

expected_args = sys.argv[1:]
if expected_args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(expected_args) == 2 and expected_args[0] == "--built"
    pins = json.loads(Path(expected_args[1]).read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
    bootstrap_sha["Integer"] = INTEGER_SHA256
    expected_pins = {
        "basis": "parent-cb0c15e54", "parentEvidence": "parent-cb0c15e54", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 87,
        "bootstrapSHA256": bootstrap_sha,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [33, 262158], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 120, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    persistent = stage / "build-pins.json"
    assert persistent.is_file() and json.loads(persistent.read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-cb0c15e54", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 87, "replacedBootstrap": "java/lang/Integer",
    "integer": {"bytes": len(integer_image), "sha256": INTEGER_SHA256,
                "preserved": "valueOf(int), constructors, conversions, equality/hash/compare, decimal parseInt",
                "added": "valueOf(String) delegates to parseInt then constructs Integer"},
    "rawLimits": [33, 262158], "diagnosticClassBound": 120,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
