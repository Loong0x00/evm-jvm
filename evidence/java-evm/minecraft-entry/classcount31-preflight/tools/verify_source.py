#!/usr/bin/env python3
"""Strict source verifier for the generated-only raw-class cap31 stage.

It pins only accepted TreeMap parent source evidence and generated stage source.
It never opens an original artifact, JAR, class, resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-4fc3c418b"

PARENT_FILES = {
    "pins.json": "b96b8540ae91f88835ffda128d055501ca63433f2108aefd46ff7099810e82c1",
    "artifacts/engine/MCEntryInterpreter.sol": "33eefa22f6421fd274900fbe6adbef9b6aad20370a217292ebafcc0eff56cfdb",
    "artifacts/coordinator/MCEntryCoordinator.sol": "e41d5673b86861fe0cca060879987d8d0bcf18fb3d309b1769e02b5ecbcf1656",
    "executed-driver.go.txt": "a88f65408b16a50ef284bdc5c93acd0d7690ca7e776c0e6b42c83c7994c21b2d",
    "checkpoint_frames.py": "d7532b64f397f68ac64b3d3b5048e1461caeb047cf712922187d29f886c7deb9",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-TREE-MAP-P2"
DOMAIN = "MC-CLASSCOUNT31-C31"
PARENT_ENGINE = "4d432d545245452d4d41502d5032000000000000"
ENGINE = "4d432d434c415353434f554e5433312d43333101"
PARENT_OWNER = "4d432d545245452d4d41502d4f32000000000000"
OWNER = "4d432d434c415353434f554e5433312d4f333102"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstraps(text):
    pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
    return dict(re.findall(pattern, text))


def initial_engine(parent_engine):
    assert parent_engine.count(PARENT_DOMAIN) == 9
    assert parent_engine.count("MAX_RAW_CLASSES = 30") == 1
    assert parent_engine.count("uint32(30), uint32(262144)") == 1
    return (parent_engine.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 30", "MAX_RAW_CLASSES = 31")
            .replace("uint32(30), uint32(262144)", "uint32(31), uint32(262144)"))


def initial_coordinator(parent_coordinator):
    assert parent_coordinator.count(PARENT_DOMAIN) == 3
    assert parent_coordinator.count(PARENT_ENGINE) == 1
    assert parent_coordinator.count("[30]") == 4
    assert parent_coordinator.count("n > 30") == 1
    return (parent_coordinator.replace(PARENT_DOMAIN, DOMAIN)
            .replace(PARENT_ENGINE, ENGINE)
            .replace("[30]", "[31]")
            .replace("n > 30", "n > 31"))


def initial_driver(parent_driver):
    assert parent_driver.count(PARENT_DOMAIN) == 5
    assert parent_driver.count("0x" + PARENT_ENGINE) == 1
    assert parent_driver.count("0x" + PARENT_OWNER) == 1
    assert parent_driver.count("> 30") == 2
    return (parent_driver.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("> 30", "> 31"))


def final_driver(preliminary, pins, parent_pins):
    text = preliminary
    replacements = (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    )
    for old, new in replacements:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 4134", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 386844", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 386844", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-4fc3c418b", "parentEvidence": "parent-4fc3c418b", "sha256": inputs,
}
assert len(DOMAIN) == 19 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [30, 262144]
assert parent_pins["diagnosticClassBound"] == 116
assert parent_pins["engine"]["bytes"] == 386844
assert parent_pins["coordinator"]["bytes"] == 4134
assert parent_pins["globalNativeBindings"] == 12
assert parent_pins["exceptionKinds"] == 14

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine)
parent_images = bootstraps(parent_engine)
images = bootstraps(engine)
assert len(parent_images) == len(images) == 86 and images == parent_images
assert engine.count("new bytes32[](86)") == 1
for fixed in (
    "MAX_RAW_CLASSES = 31;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 12;", "uint32[11] memory limits",
):
    assert engine.count(fixed) == 1, fixed
assert engine.count("uint32(31), uint32(262144)") == 1

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator(parent_coordinator)
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[31]") == 4 and coordinator.count("n > 31") == 1
assert "262144" in coordinator

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 5 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("> 31") == 2
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_frames.py").read_text().replace("classes<=116", "classes<=117")
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
        "basis": "parent-4fc3c418b", "parentEvidence": "parent-4fc3c418b", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [31, 262144], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 117, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-4fc3c418b", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "rawLimits": [31, 262144],
    "diagnosticClassBound": 117, "globalNativeBindings": 12, "stringLocalBinding": 10,
    "exceptionKinds": 14, "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "address": "0x" + ENGINE,
}, indent=2))
