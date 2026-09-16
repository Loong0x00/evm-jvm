#!/usr/bin/env python3
"""Strict source verifier for the generated-only raw-class cap32 stage.

It reads only accepted lockInterruptibly parent source evidence and local pinned
source files. It never opens an original artifact, JAR, class, resource,
checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-850386373"

PARENT_FILES = {
    "pins.json": "9280593658b8bab64e050d9bb49b4d6470241d54c31586b2ba2711c6c2f46bdd",
    "artifacts/engine/MCEntryInterpreter.sol": "209e806ebd50207cb137a82682e522e56aa7ea4374aaaa6cd075ff12f54d7c8e",
    "artifacts/coordinator/MCEntryCoordinator.sol": "d26717afaf84b2132c63ca0c3e561b5888d17882ba29b7675d4fc9bfc157785d",
    "executed-driver.go.txt": "e8ce760e483f6bf6582a0b05a930c9271f0b212d0ee0b64e76982ce46f811d07",
    "checkpoint_diagnostic.py": "26b98ae108509da714b77c8887eaebc222f90983730c361b1fbe8af46ebb45a4",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-LOCK-INTERRUPTIBLY-P2"
DOMAIN = "MC-CLASSCOUNT32-C32"
PARENT_ENGINE = "4d432d4c4f434b2d494e544552525550542d5032"
ENGINE = "4d432d434c415353434f554e5433322d43333201"
PARENT_OWNER = "4d432d4c4f434b2d494e544552525550542d4f32"
OWNER = "4d432d434c415353434f554e5433322d4f333202"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstraps(text):
    pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
    return dict(re.findall(pattern, text))


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 31") == 1
    assert text.count("uint32(31), uint32(262144)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 31", "MAX_RAW_CLASSES = 32")
            .replace("uint32(31), uint32(262144)", "uint32(32), uint32(262144)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 3 and text.count(PARENT_ENGINE) == 1
    assert text.count("[31]") == 4 and text.count("n > 31") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[31]", "[32]").replace("n > 31", "n > 32"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 5
    assert text.count("0x" + PARENT_ENGINE) == 1 and text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 31") == 1 and text.count("len(parts) > 31") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 31", "len(m.Decoders) > 32")
            .replace("len(parts) > 31", "len(parts) > 32"))


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 4146", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 387394", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 387394", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-850386373", "parentEvidence": "parent-850386373", "sha256": inputs,
}
assert len(DOMAIN) == 19 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [31, 262144]
assert parent_pins["diagnosticClassBound"] == 117
assert parent_pins["engine"]["bytes"] == 387394
assert parent_pins["coordinator"]["bytes"] == 4146
assert parent_pins["globalNativeBindings"] == 12
assert parent_pins["exceptionKinds"] == 14

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine)
parent_images = bootstraps(parent_engine)
images = bootstraps(engine)
assert len(parent_images) == len(images) == 86 and images == parent_images
for fixed in (
    "MAX_RAW_CLASSES = 32;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](86)", "new uint256[](14)", "return 12;", "uint32[11] memory limits",
    "uint32(32), uint32(262144)",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator(parent_coordinator)
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[32]") == 4 and coordinator.count("n > 32") == 1
assert "262144" in coordinator

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 5 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 32") == 1 and driver.count("len(parts) > 32") == 1
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_diagnostic.py").read_text().replace("classes<=117", "classes<=118")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

prebuild = sys.argv[1:] == ["--prebuild"]
pins_path = stage / "pins.json"
if prebuild:
    assert not pins_path.exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    pins = json.loads(pins_path.read_text())
    expected_pins = {
        "basis": "parent-850386373", "parentEvidence": "parent-850386373", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [32, 262144], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 118, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-850386373", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "unchangedBootstrapImages": 86,
    "rawLimits": [32, 262144], "diagnosticClassBound": 118,
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "address": "0x" + ENGINE,
}, indent=2))
