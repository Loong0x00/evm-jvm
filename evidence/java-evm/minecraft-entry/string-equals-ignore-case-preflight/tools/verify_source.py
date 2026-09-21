#!/usr/bin/env python3
'''Verify the exact generated-only String.equalsIgnoreCase(String) delta.

This verifier accepts no original artifact, JAR, class, resource, or world input.
It rebuilds the checked-in Java-8 String image and mechanically derives both
interpreter layouts from the accepted image93 Objects parent evidence.
'''
from pathlib import Path
import copy
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
parent = stage.parent / "objects-require-non-null-preflight"
OLD = "MC-OBJECTS-REQUIRE-NON-NULL-P1"
DOMAIN = "MC-STRING-EQUALS-IGNORE-CASE-P1"
OLD_ENGINE = "4d432d4f424a454354532d5245514e4e2d393350"
ENGINE = "4d432d5354522d45512d49434153452d50314500"
OLD_OWNER = "4d432d4f424a454354532d5245514e4e2d39334f"
OWNER = "4d432d5354522d45512d49434153452d50314f00"
STRING_SHA256 = "4cff1fc7c1ee49c0e070a7aec64963193e34206838c509003715f972aa8d58a0"
STRING_KECCAK = "970f2e6e9f56ce52831febe44b4dc85a0198431d206a7dff6b9dbe2f9cffe974"
ENGINE_PIN = {"bytes": 391507, "initSHA256": "54f0f24b7acaf77e4bebe8923bc3441bded346ef8561a5db618be99a35ac4df4", "runtimeSHA256": "956604c414ee79b3282ad9a041cc081237684c90fd2642569f5a8ca76f5b40f4", "runtimeKeccak256": "a6368e9d348da3c63fe15573fc50b79e460db4670c4ed77dc95537c871af7903"}
COORDINATOR_PIN = {"bytes": 5394, "initSHA256": "118a3ba559c19be1c84d861ac7d9e8aeda71344e4a46e07ffec1f1a7cfc216ad", "runtimeSHA256": "83348e171f5d464c044f87272aa59f69f48a27e01a10689978e24f0a375dd737", "runtimeKeccak256": "42bc08b3f713a87cd36226f3395b67a7bb9fa4060039afc582c03a8200be712e"}


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:100], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


STRING_SOURCE = '''package java.lang;
public final class String implements java.io.Serializable, Comparable<String>, CharSequence {
  private final char[] value;
  private int hash;
  private String() { value = null; }
  public String(char[] source) {
    char[] copy = new char[source.length];
    for (int i = 0; i < source.length; i++) copy[i] = source[i];
    value = copy;
  }
  public String(String source) { value = source.value; hash = source.hash; }
  public native int length();
  public native boolean isEmpty();
  public native char charAt(int index);
  public native boolean equals(Object other);
  public native int hashCode();
  public native String toString();
  public native int compareTo(String other);
  public native String intern();
  public native CharSequence subSequence(int start, int end);
  public int lastIndexOf(String target) {
    int targetLength = target.length();
    int receiverLength = length();
    if (targetLength == 0) return receiverLength;
    if (targetLength > receiverLength) return -1;
    for (int start = receiverLength - targetLength; start >= 0; start--) {
      int index = 0;
      while (index < targetLength && charAt(start + index) == target.charAt(index)) index++;
      if (index == targetLength) return start;
    }
    return -1;
  }
  public boolean startsWith(String prefix) {
    int prefixLength = prefix.length();
    if (prefixLength > length()) return false;
    for (int index = 0; index < prefixLength; index++) {
      if (charAt(index) != prefix.charAt(index)) return false;
    }
    return true;
  }
  // Deliberately bounded to UTF-16 unit equality and ASCII A-Z/a-z folding.
  // This is not a general Unicode case-folding implementation.
  public boolean equalsIgnoreCase(String other) {
    if (other == null) return false;
    int receiverLength = length();
    if (receiverLength != other.length()) return false;
    for (int index = 0; index < receiverLength; index++) {
      char left = charAt(index);
      char right = other.charAt(index);
      if (left == right) continue;
      if (left >= 'A' && left <= 'Z') left = (char) (left + ('a' - 'A'));
      if (right >= 'A' && right <= 'Z') right = (char) (right + ('a' - 'A'));
      if (left != right) return false;
    }
    return true;
  }
  public native String[] split(String regex);
}
'''
assert stage_text("bootstrap/java/lang/String.java") == STRING_SOURCE
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-equals-ignore-case-verify-", dir=root / "build") as temp:
    temp = Path(temp)
    src = temp / "java/lang/String.java"
    src.parent.mkdir(parents=True)
    src.write_text(STRING_SOURCE)
    out = temp / "out"
    out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/String.class").read_bytes()
assert len(image) == 1503 and hashlib.sha256(image).hexdigest() == STRING_SHA256
assert image.hex() == stage_text("bootstrap/java/lang/String.class.hex").strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
for required in (
    b"equalsIgnoreCase", b"(Ljava/lang/String;)Z", b"lastIndexOf", b"startsWith",
    b"java/lang/String", b"java/lang/CharSequence",
):
    assert required in image, required
for forbidden in (
    b"equalsIgnoreCaseAscii", b"toLowerCase", b"toUpperCase", b"regionMatches",
    b"Locale", b"Character",
):
    assert forbidden not in image, forbidden


def bootstrap_hex(text):
    marker = '    function _bootstrapString() private pure returns (bytes memory) {\n        return hex"'
    start = text.index(marker) + len(marker)
    end = text.index('";', start)
    return text[start:end]


def engine_expected(text, string_hex):
    text = replace_exact(text, OLD, DOMAIN, 9)
    original = bootstrap_hex(parent_text("engine/MCEntryInterpreter.sol"))
    assert len(bytes.fromhex(original)) == 1315
    text = replace_exact(text, original, string_hex)
    assert text.count("function _bootstrapString() private pure returns (bytes memory)") == 1
    return text


for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(relative) == engine_expected(parent_text(relative), image.hex()), relative

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = replace_exact(coordinator, OLD, DOMAIN, 4)
coordinator = replace_exact(coordinator, OLD_ENGINE, ENGINE)
coordinator = replace_exact(coordinator, "1767996b5436be6c2b763dec84ddbfd9b63e4b40a0252c41adf598c26d7ab864", ENGINE_PIN["runtimeKeccak256"])
assert stage_text("coordinator/MCEntryCoordinator.sol") == coordinator

transport = parent_text("tools/Go.txt")
for old, new in (
    (OLD, DOMAIN), (OLD_OWNER, OWNER), (OLD_ENGINE, ENGINE),
    ("6f3f9dd1ae1dbac37fb20423b64f3ce83ef406d0cefbe1c069eba7b5dc4d9b4d", ENGINE_PIN["runtimeSHA256"]),
    ("0x1767996b5436be6c2b763dec84ddbfd9b63e4b40a0252c41adf598c26d7ab864", "0x" + ENGINE_PIN["runtimeKeccak256"]),
    ("0xa836de09bb8adfa4aff13c83ade6e38672a93d7f27003f3fbea594ea5a4b8c0a", "0x" + COORDINATOR_PIN["runtimeKeccak256"]),
    ("len(engineRun) != 390985", "len(engineRun) != 391507"),
    ("len(run) != 390985", "len(run) != 391507"),
):
    assert old in transport, old
    transport = transport.replace(old, new)
assert stage_text("tools/Go.txt") == transport

# The diagnostic bound, raw capacity, all retained bootstrap leaves, native13,
# and all runtime limits are unchanged. Only zero-based String root-leaf26 and
# domain-derived
# commitments differ from image93 Objects parent evidence.
pins = json.loads(stage_text("build-pins.json"))
parent_pins = json.loads(parent_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "7c7c0fb6b", "parentEvidence": "objects-require-non-null-preflight",
    "phase": "built", "domain": DOMAIN, "runtimeBaseline": 390985,
    "address": "0x" + ENGINE, "owner": "0x" + OWNER,
    "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN,
})
expected_pins["bootstrapSHA256"]["String"] = STRING_SHA256
assert pins == expected_pins
assert pins["bootstrapCount"] == 93 and pins["diagnosticClassBound"] == 141
assert pins["rawLimits"] == [48, 314425] and pins["globalNativeBindings"] == 13
assert pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768

record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 93
assert record["order"] == parent_record["order"]
assert record["keccak256"][:26] == parent_record["keccak256"][:26]
assert record["keccak256"][26] == STRING_KECCAK
assert record["keccak256"][27:] == parent_record["keccak256"][27:]
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir()
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output([
    "node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1",
], cwd=root, env=env, text=True))
assert actual == {"d": record["dboot"], "r": record["bootstrapRoot"]}
assert len(record["keccak256"]) == len(record["order"]) == 93

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert stage_text(relative) == parent_text(relative), relative
for relative in ("tools/build.py", "tools/generate_fixtures.py", "tools/gate.py"):
    for required in ("string-equals-ignore-case", "equalsIgnoreCase"):
        assert required in stage_text(relative), (relative, required)
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({
    "phase": "built", "domain": DOMAIN, "bootstrapImages": 93,
    "bootstrapRoot": record["bootstrapRoot"], "stringBytes": len(image),
    "stringSHA256": STRING_SHA256, "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": 141, "runtimeBaseline": 390985,
    "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
    "coordinatorBytes": COORDINATOR_PIN["bytes"],
}, indent=2))
