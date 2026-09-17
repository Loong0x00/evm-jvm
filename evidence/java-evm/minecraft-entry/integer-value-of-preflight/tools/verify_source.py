#!/usr/bin/env python3
"""Strict source-only verifier for bounded ``Integer.valueOf(int)``.

The only accepted input is raw33 parent ``parent-1b7a30656``.  This stage
replaces exactly the existing ``java/lang/Integer`` bootstrap image; generated
fixtures are the sole Java inputs and no original artifact, class, JAR,
resource, checkpoint, or world is opened.
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
parent = stage.parent / "parent-1b7a30656"

PARENT_FILES = {
    "pins.json": "c40d56dad72baf4aa180d9714a508b2efe60198a9de1dc85ab7ce1fb9f4b36af",
    "artifacts/engine/MCEntryInterpreter.sol": "2463ac6c71d50a0a7091710bfea3cf8d87b6514f01f076fd44e41451a8c6b4c5",
    "artifacts/coordinator/MCEntryCoordinator.sol": "05643cdba3ee5bb8758e595420669c0fa45b2a0c6d4921ea029b79e0625d00c6",
    "executed-driver.go.txt": "7678c70c1c8aaa1c7a052c28a2354a1a38285cdb346d7ef12293a98eb5c971fc",
    "checkpoint_diagnostic.py": "a7d1b2314e0349f3cb2d302bb4733d0bf8eea117e358694612af4e39607ea5f7",
    "checkpoint_frames.py": "a7d1b2314e0349f3cb2d302bb4733d0bf8eea117e358694612af4e39607ea5f7",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
}
PARENT_DOMAIN = "MC-CLASSCOUNT33-BYTE262158-P2"
DOMAIN = "MC-INTEGER-VALUE-OF-P1"
PARENT_ENGINE = "4d432d434333332d42593236323135382d454e48"
ENGINE = "4d432d494e542d56414c55454f462d50312d4531"
PARENT_OWNER = "4d432d434333332d42593236323135382d4f574f"
OWNER = "4d432d494e542d56414c55454f462d50312d4f31"
PARENT_INTEGER_SHA256 = "bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537"
INTEGER_SHA256 = "1b0b1b25e935a2065f2af4d7e3bb1caa677fe08b16247c9d4a0cfbd0abd1d5c6"
VALUE_OF_SOURCE = "  public static Integer valueOf(int value) { return new Integer(value); }\n"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(text, name):
    match = re.search(r"function _bootstrap" + name + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


def initial_engine(text, image_hex):
    old_integer = bootstrap(text, "Integer")
    assert text.count(PARENT_DOMAIN) == 9
    assert hashlib.sha256(bytes.fromhex(old_integer)).hexdigest() == PARENT_INTEGER_SHA256
    assert len(bytes.fromhex(old_integer)) == 1667
    assert text.count(old_integer) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(old_integer, image_hex)
    assert result.count(DOMAIN) == 9 and result.count(image_hex) == 1
    return result


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    result = text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
    assert result.count(DOMAIN) == 4 and result.count(ENGINE) == 1
    return result


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count(PARENT_ENGINE) == text.count(PARENT_OWNER) == 1
    result = (text.replace(PARENT_DOMAIN, DOMAIN)
                  .replace(PARENT_ENGINE, ENGINE)
                  .replace(PARENT_OWNER, OWNER))
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
        (r"len\(engineRun\) != 392076", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 392076", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-1b7a30656", "parentEvidence": "parent-1b7a30656", "sha256": inputs,
}
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [33, 262158]
assert parent_pins["diagnosticClassBound"] == 119
assert parent_pins["engine"]["bytes"] == 392076
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

# Delete exactly the new method from the stage source and compile both forms.
# The old form must regenerate the parent byte image exactly, proving that no
# pre-existing Integer constructor or method changed.
source = (stage / "bootstrap/java/lang/Integer.java").read_text()
assert source.count(VALUE_OF_SOURCE) == 1
base_source = source.replace(VALUE_OF_SOURCE, "")
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="integer-value-of-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    for label, text in (("base", base_source), ("valueof", source)):
        src = tmp / label / "java/lang/Integer.java"
        src.parent.mkdir(parents=True)
        src.write_text(text)
        out = tmp / (label + "-out")
        out.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
        image = (out / "java/lang/Integer.class").read_bytes()
        if label == "base":
            parent_image = image
        else:
            valueof_image = image
assert len(parent_image) == 1667 and hashlib.sha256(parent_image).hexdigest() == PARENT_INTEGER_SHA256
assert parent_image.hex() == bootstrap((parent / "artifacts/engine/MCEntryInterpreter.sol").read_text(), "Integer")
assert len(valueof_image) == 1747 and hashlib.sha256(valueof_image).hexdigest() == INTEGER_SHA256
assert valueof_image.hex() == (stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip()
assert valueof_image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/lang/Integer", b"java/lang/Number", b"valueOf", b"(I)Ljava/lang/Integer;", b"<init>"):
    assert required in valueof_image, required
for forbidden in (b"IntegerCache", b"valueOf(Ljava/lang/String;)", b"(Ljava/lang/String;I)", b"toString"):
    assert forbidden not in valueof_image, forbidden

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine, valueof_image.hex())
assert hashlib.sha256(bytes.fromhex(bootstrap(engine, "Integer"))).hexdigest() == INTEGER_SHA256
assert len(bytes.fromhex(bootstrap(engine, "Integer"))) == 1747
for fixed in (
    "MAX_RAW_CLASSES = 33;", "MAX_RAW_BYTES = 262158;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](86)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(33), uint32(262158)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;",
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
assert (stage / "tools/checkpoint_diagnostic.py").read_bytes() == (parent / "checkpoint_diagnostic.py").read_bytes()
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

expected_args = sys.argv[1:]
prebuild = expected_args == ["--prebuild"]
if prebuild:
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
        "basis": "parent-1b7a30656", "parentEvidence": "parent-1b7a30656", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": bootstrap_sha,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [33, 262158], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 119, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
    "acceptedParent": "parent-1b7a30656", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "replacedBootstrap": "java/lang/Integer",
    "integer": {"oldBytes": len(parent_image), "oldSHA256": PARENT_INTEGER_SHA256,
                "bytes": len(valueof_image), "sha256": INTEGER_SHA256,
                "method": "valueOf(I)Ljava/lang/Integer;", "allocation": "new Integer(value)"},
    "rawLimits": [33, 262158], "diagnosticClassBound": 119,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
