#!/usr/bin/env python3
"""Strict source verifier for the generated-only lockInterruptibly image replacement.

It reads only accepted cap31 source evidence and the local Java-8 toolchain.  It
never opens original artifacts, JARs, classes, resources, checkpoints, or worlds.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-1e0e9e9aa"

PARENT_FILES = {
    "pins.json": "751e3afcfba8e7e81add4073ce7e919e96bdb4e16f8c34031dcf84029162994b",
    "artifacts/engine/MCEntryInterpreter.sol": "af27b9063fa2010f140b39e98d404b8f4480d28de07277b7103f6a12241eb1ef",
    "artifacts/coordinator/MCEntryCoordinator.sol": "782bd04647579569b06f82dcaa49999738817d4b46606e75c9cae20b86e55f0f",
    "executed-driver.go.txt": "9fae536fa06e6d846a90a326d3622bf89103e0198d77b3726382c5799b7a9c39",
    "checkpoint_diagnostic.py": "26b98ae108509da714b77c8887eaebc222f90983730c361b1fbe8af46ebb45a4",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-CLASSCOUNT31-P31"
DOMAIN = "MC-LOCK-INTERRUPTIBLY-P1"
PARENT_ENGINE = "4d432d434c415353434f554e5433312d50333101"
ENGINE = "4d432d4c4f434b2d494e544552525550542d5031"
PARENT_OWNER = "4d432d434c415353434f554e5433312d4f333202"
OWNER = "4d432d4c4f434b2d494e544552525550542d4f31"
COMPILER = {
    "version": "0.8.30+commit.73712a01.Emscripten.clang",
    "optimizer": {"enabled": True, "runs": 200}, "viaIR": True, "evmVersion": "cancun",
    "metadata": {"appendCBOR": False, "bytecodeHash": "none"},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_map(source):
    pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";\s*\}'
    return dict(re.findall(pattern, source))


def replace_image(source, name, data):
    pattern = r'(function _bootstrap%s\(\) private pure returns \(bytes memory\) \{\s*return hex")[0-9a-f]+(";\s*\})' % name
    source, changed = re.subn(pattern, r'\g<1>' + data.hex() + r'\g<2>', source)
    assert changed == 1, (name, changed)
    return source


def rebuild_images():
    javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
    rt = Path("/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar")
    assert javac.is_file() and rt.is_file()
    sources = sorted(stage.glob("bootstrap/**/*.java"))
    assert [p.relative_to(stage).as_posix() for p in sources] == [
        "bootstrap/java/util/concurrent/locks/Lock.java",
        "bootstrap/java/util/concurrent/locks/ReentrantLock.java",
    ]
    with tempfile.TemporaryDirectory(dir=root / "build") as td:
        td = Path(td)
        api = td / "rt.jar"
        out = td / "classes"
        out.mkdir()
        shutil.copyfile(rt, api)
        subprocess.run(["zip", "-q", "-d", api,
                        "java/util/concurrent/locks/Lock.class",
                        "java/util/concurrent/locks/ReentrantLock.class"], check=True)
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none",
                        "-bootclasspath", api, "-d", out, *sources], check=True)
        images = {
            "Lock": (out / "java/util/concurrent/locks/Lock.class").read_bytes(),
            "ReentrantLock": (out / "java/util/concurrent/locks/ReentrantLock.class").read_bytes(),
        }
    assert images["Lock"][:8] == bytes.fromhex("cafebabe00000034")
    assert images["ReentrantLock"][:8] == bytes.fromhex("cafebabe00000034")
    for data in images.values():
        assert b"lockInterruptibly" in data and b"java/lang/InterruptedException" in data
    return images


inputs = {name: digest(parent / name) for name in PARENT_FILES}
expected_parent_input = {"basis": "parent-1e0e9e9aa", "parentEvidence": "parent-1e0e9e9aa", "sha256": inputs}
assert json.loads((stage / "parent-input.json").read_text()) == expected_parent_input
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [31, 262144]
assert parent_pins["diagnosticClassBound"] == 117
assert parent_pins["engine"]["bytes"] == 386844
assert parent_pins["coordinator"]["bytes"] == 4146
assert parent_pins["globalNativeBindings"] == 12
assert parent_pins["exceptionKinds"] == 14
assert parent_pins["compiler"] == COMPILER

rebuilt = rebuild_images()
parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
for name in ("Lock", "ReentrantLock"):
    expected_engine = replace_image(expected_engine, name, rebuilt[name])
assert engine == expected_engine
parent_images = image_map(parent_engine)
images = image_map(engine)
assert len(parent_images) == len(images) == 86
changed = {name for name in images if images[name] != parent_images[name]}
assert changed == {"_bootstrapLock", "_bootstrapReentrantLock"}
for name in ("Lock", "ReentrantLock"):
    assert bytes.fromhex(images["_bootstrap" + name]) == rebuilt[name]
for fixed in (
    "MAX_RAW_CLASSES = 31;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](86)", "new uint256[](14)", "return 12;", "uint32[11] memory limits",
    "uint32(31), uint32(262144)",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
assert parent_coordinator.count(PARENT_DOMAIN) == 3 and parent_coordinator.count(PARENT_ENGINE) == 1
preliminary_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (here / "Go.txt").read_text()
assert parent_driver.count(PARENT_DOMAIN) == 5
assert parent_driver.count("0x" + PARENT_ENGINE) == 1 and parent_driver.count("0x" + PARENT_OWNER) == 1
preliminary_driver = (parent_driver.replace(PARENT_DOMAIN, DOMAIN)
                      .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
                      .replace("0x" + PARENT_OWNER, "0x" + OWNER))


def final_driver(text, pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 4146", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 386844", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 386844", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text

prebuild = sys.argv[1:] == ["--prebuild"]
pins_path = stage / "pins.json"
if prebuild:
    assert not pins_path.exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    pins = json.loads(pins_path.read_text())
    image_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in rebuilt.items()}
    expected_pins = {
        "basis": "parent-1e0e9e9aa", "parentEvidence": "parent-1e0e9e9aa", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], **image_hashes},
        "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [31, 262144], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 117, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": COMPILER,
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins)
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-1e0e9e9aa", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "unchangedBootstrapImages": 84,
    "replacedImages": {name: hashlib.sha256(data).hexdigest() for name, data in rebuilt.items()},
    "rawLimits": [31, 262144], "diagnosticClassBound": 117,
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "address": "0x" + ENGINE,
}, indent=2))
