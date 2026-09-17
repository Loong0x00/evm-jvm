#!/usr/bin/env python3
"""Strict generated-only source invariants for raw33/byte262158.

The only accepted starting point is the bounded String.startsWith parent. This
script reads its source pins plus local generated fixture/gate sources; it never
opens an original artifact, JAR, class, resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-1709f8e18"

PARENT_FILES = {
    "pins.json": "cc2b6540d4506b459b539daaa90ecf374854a7bb1f2ae42a8b2a78714f81b7fe",
    "artifacts/engine/MCEntryInterpreter.sol": "1377ef6d48160e9fee9676dc1014756c91bc04784677206c7e7a2eb32f2b3409",
    "artifacts/coordinator/MCEntryCoordinator.sol": "369840f15e93d928ede1eb4976e6d8a26697c8744e8b89a9e76c40279ab0b0f7",
    "executed-driver.go.txt": "f5b4c4299f4161398572982af8e8c1876105f3e94c36b68f9a69c84cc1fef8b9",
    "checkpoint_diagnostic.py": "53ffb820a44df128a8f684a985d5d05a281a1e7ac04158faa9f11a78ba187fa0",
    "checkpoint_frames.py": "53ffb820a44df128a8f684a985d5d05a281a1e7ac04158faa9f11a78ba187fa0",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
}
PARENT_DOMAIN = "MC-STRING-STARTS-WITH-P2"
DOMAIN = "MC-CLASSCOUNT33-BYTE262158-P1"
PARENT_ENGINE = "4d432d535452494e472d53544152545357495449"
ENGINE = "4d432d434333332d42593236323135382d454e47"
PARENT_OWNER = "4d432d535452494e472d5354415254532d4f574f"
OWNER = "4d432d434333332d42593236323135382d4f574e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstraps(text):
    pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
    return dict(re.findall(pattern, text))


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 32;") == 1
    assert text.count("MAX_RAW_BYTES = 262144;") == 1
    assert text.count("uint32(32), uint32(262144)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 32;", "MAX_RAW_CLASSES = 33;")
            .replace("MAX_RAW_BYTES = 262144;", "MAX_RAW_BYTES = 262158;")
            .replace("uint32(32), uint32(262144)", "uint32(33), uint32(262158)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    assert text.count("[32]") == 4 and text.count("n > 32") == 1
    # These are the only coordinator raw-byte guards: per-member (derivable
    # from the aggregate cap) and aggregate construction admission.
    assert text.count("262144") == 2
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[32]", "[33]").replace("n > 32", "n > 33")
            .replace("262144", "262158"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count("0x" + PARENT_ENGINE) == 1 and text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 32") == 1 and text.count("len(parts) > 32") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 32", "len(m.Decoders) > 33")
            .replace("len(parts) > 32", "len(parts) > 33"))


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
    "basis": "parent-1709f8e18", "parentEvidence": "parent-1709f8e18", "sha256": inputs,
}
assert len(DOMAIN) == 29 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [32, 262144]
assert parent_pins["diagnosticClassBound"] == 118
assert parent_pins["engine"]["bytes"] == 392076
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine)
parent_images = bootstraps(parent_engine)
images = bootstraps(engine)
# One fixed bootstrap body uses a multiline return form, so this lightweight
# literal extractor sees 85 of the parent-pinned 86 images. Full engine equality
# to initial_engine above proves all 86 image bytes and positions unchanged.
assert len(parent_images) == len(images) == 85 and images == parent_images
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
assert coordinator.count("4096") == parent_coordinator.count("4096")

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 33") == 1 and driver.count("len(parts) > 33") == 1
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_diagnostic.py").read_text().replace("classes<=118", "classes<=119")
assert (stage / "tools/checkpoint_frames.py").read_text() == (parent / "checkpoint_frames.py").read_text().replace("classes<=118", "classes<=119")
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
    expected_pins = {
        "basis": "parent-1709f8e18", "parentEvidence": "parent-1709f8e18", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
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
    "acceptedParent": "parent-1709f8e18", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "unchangedBootstrapImages": 86,
    "rawLimits": [33, 262158], "diagnosticClassBound": 119,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
