#!/usr/bin/env python3
"""Strict source-only verifier for bounded String.lastIndexOf(String).

It consumes only accepted parent-31e5a573c engine/coordinator/driver sources and
this stage's generated Java-8 String input. It never opens an original server
artifact, class, resource, checkpoint, or world.
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
parent = stage.parent / "parent-31e5a573c"

PARENT_FILES = {
    "pins.json": "f00a01eaba710616ba8d2339e3143905a2d33981e30952fc476a7a6045ee59d3",
    "artifacts/engine/MCEntryInterpreter.sol": "1950e1439be4024d6db80aebcb8bf0b1307d2db7cfb2a494b4c9a17cb07f27dd",
    "artifacts/coordinator/MCEntryCoordinator.sol": "c0395ade3dd64e9ac0403e6e19eb7d2e404241d201d65030e5cf4437a8383a30",
    "executed-driver.go.txt": "97e8d0c2ab134c1dd21860f33949ce494503c07b044aede98f49e54276bfdbb1",
    "checkpoint_frames.py": "13fe08107dba926f0134dbd1c1b5b958987149b78c947df2ae30054f8141629b",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-STRING-BUILDER-P2"
DOMAIN = "MC-STRING-LAST-INDEX-P1"
PARENT_ENGINE = "4d432d535452494e472d4255494c4445522d5032"
ENGINE = "4d432d535452494e472d4c415354494e44455831"
PARENT_OWNER = "4d432d535452494e472d4255494c4445522d4f32"
OWNER = "4d432d535452494e472d4c415354494e4445584f"
PARENT_RUNTIME_SHA = "098e854db81e0aef65c0d57690cc88476e25767194c30eedc227c46af7623893"
PARENT_RUNTIME_KECCAK = "37c6ea22b2a9bc365faf68c35b20ef9f45d3639ace83e47f22e237232ca79c78"
PARENT_COORDINATOR_KECCAK = "90941b52203e5fa852c1028e4e9700f715c996de4482131a4f6947f99e12bb47"
PARENT_STRING_SHA = "c412caea1d48baade8aa9d2653c6a23bb319a49deefe729ac99089f0c5248eba"
STRING_SHA = "2fbfe5d57906f5ebd4f2eeaceb209edf8d4a619afb21d1531f7aaea121506033"
LIMITS_COMMITMENT = "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_image(text, name):
    found = re.search(
        r"function _bootstrap" + re.escape(name)
        + r"\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";\s*\}",
        text,
    )
    assert found, name
    return found.group(1)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-31e5a573c", "parentEvidence": "parent-31e5a573c", "sha256": inputs,
}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["bootstrapCount"] == 85
assert parent_pins["engine"]["bytes"] == 386100
assert parent_pins["engine"]["runtimeSHA256"] == PARENT_RUNTIME_SHA
assert parent_pins["engine"]["runtimeKeccak256"] == PARENT_RUNTIME_KECCAK
assert parent_pins["coordinator"]["runtimeKeccak256"] == PARENT_COORDINATOR_KECCAK
assert parent_pins["limitsCommitment"] == LIMITS_COMMITMENT
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20

EXPECTED_SOURCE = """package java.lang;
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
  public native String[] split(String regex);
}
"""
source = (stage / "bootstrap/java/lang/String.java").read_text()
assert source == EXPECTED_SOURCE
pins = json.loads((stage / "bootstrap/pins.json").read_text())
assert pins == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "String": {
        "source": "java/lang/String.java", "classHex": "java/lang/String.class.hex",
        "bytes": 1187, "sha256": STRING_SHA,
        "surface": "preserved accepted String surface plus lastIndexOf(String) only",
        "nullTarget": "ordinary guest NullPointerException from target.length() before receiver inspection",
    },
}

# Java compilation is provenance only; the generated class image is consumed by
# Solidity and later executed by EVM, never by a host Java execution path.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-last-index-of-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/String.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/String.class").read_bytes()
assert len(image) == 1187 and hashlib.sha256(image).hexdigest() == STRING_SHA
assert image.hex() == (stage / "bootstrap/java/lang/String.class.hex").read_text().strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert image.count(b"lastIndexOf") == 1
assert image.count(b"(Ljava/lang/String;)I") == 1
assert b"(Ljava/lang/String;I)I" not in image
for forbidden in (b"substring", b"regex", b"encode", b"decode"):
    assert forbidden not in image, forbidden
# This exact source sequence is the null contract: no explicit host/null helper
# precedes the first ordinary guest target.length invokevirtual.
assert "int targetLength = target.length();\n    int receiverLength = length();" in source

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_string = bootstrap_image(parent_engine, "String")
assert len(bytes.fromhex(parent_string)) == 1015
assert hashlib.sha256(bytes.fromhex(parent_string)).hexdigest() == PARENT_STRING_SHA
assert parent_engine.count(PARENT_DOMAIN) == 9 and parent_engine.count(parent_string) == 1
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN).replace(parent_string, image.hex())
assert engine == expected_engine
pattern = r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";"
parent_images = dict(re.findall(pattern, parent_engine))
images = dict(re.findall(pattern, engine))
assert len(parent_images) == len(images) == 85
assert set(parent_images) == set(images)
for name, value in parent_images.items():
    assert images[name] == (image.hex() if name == "_bootstrapString" else value), name
assert engine.count("h[26] = keccak256(_bootstrapString());") == 1
assert engine.count("new bytes32[](85)") == 1
assert engine.count("function _appendTailBootstraps(Program memory p, uint256 at, bool suppliedRunnable) private pure") == 1
assert engine.count("_appendStringBuilderBootstrap(p.classes, classSlot + 45);") == 1
assert engine.count('bytes("java/lang/StringBuilder")') == 1
assert engine.count("uint256 count = inputCount + 79 +") == 1
for fixed in (
    "MAX_RAW_CLASSES = 30;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 12;", "uint32[11] memory limits",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
assert coordinator == expected_coordinator
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[30]") == 4 and coordinator.count("n > 30") == 1 and "262144" in coordinator

driver_parent = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)
assert driver == expected_driver
assert driver.count(DOMAIN) == 5 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert PARENT_RUNTIME_SHA in driver and ("0x" + PARENT_RUNTIME_KECCAK) in driver
assert ("0x" + PARENT_COORDINATOR_KECCAK) in driver and driver.count("386100") == 2
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

print(json.dumps({
    "acceptedParent": "parent-31e5a573c", "parentInputsVerified": len(inputs),
    "parentEngineSourceSHA256": PARENT_FILES["artifacts/engine/MCEntryInterpreter.sol"],
    "parentRuntimeSHA256": PARENT_RUNTIME_SHA, "parentRuntimeKeccak256": PARENT_RUNTIME_KECCAK,
    "domain": DOMAIN, "bootstrapImages": 85, "stringSlot": 26,
    "soleBootstrapReplacement": "java/lang/String", "rawLimits": [30, 262144],
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "string": {"bytes": len(image), "sha256": STRING_SHA, "method": "lastIndexOf(String):int"},
    "limitsCommitment": LIMITS_COMMITMENT,
}, indent=2))
