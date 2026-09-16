#!/usr/bin/env python3
"""One reproducible LOCAL cap31 source build from accepted TreeMap source only."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-classcount31-build-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
if not node_modules.is_dir():
    raise RuntimeError("pinned local solc is unavailable; refusing shared or network dependencies")
out.mkdir(); (out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")

PARENT_ENGINE_SHA = "4ed10a7ac3b3760f05aa7052cc94ed571bed156ca84c52c71fabbfbfea7f1d5f"
PARENT_ENGINE_KECCAK = "062db6774c081faeb4d0c28f593d854ee8d0996662fb4649e52c555361c5150b"
PARENT_COORDINATOR_KECCAK = "c6e7af78a9b2072a600fdd57444b1668be59c3b59f40f0bc1bfcc9c4875c3ea3"
COMPILER = {
    "version": "0.8.30+commit.73712a01.Emscripten.clang",
    "optimizer": {"enabled": True, "runs": 200}, "viaIR": True, "evmVersion": "cancun",
    "metadata": {"appendCBOR": False, "bytecodeHash": "none"},
}


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())


def pin(artifact_data):
    return {"bytes": len(artifact_data["deployedBytecode"]) // 2, **artifact_data["codeHashes"]}


# A source checkout can be built first from the exact parent placeholders, or
# rebuilt after the first run from final immutable source pins. Neither route
# accesses original Minecraft input.
run("source-verification-prebuild" if not (stage / "pins.json").exists() else "source-verification", [
    sys.executable, here / "verify_source.py", *( ["--prebuild"] if not (stage / "pins.json").exists() else []),
])

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
assert engine["compiler"] == COMPILER
engine_pin = pin(engine)
assert engine_pin["bytes"] <= 393216

# Seal the stage source with the one derived engine hash before compiling the
# coordinator. This is a pin update, not a semantic source change.
coordinator_source = stage / "coordinator/MCEntryCoordinator.sol"
text = coordinator_source.read_text()
if PARENT_ENGINE_KECCAK in text:
    assert text.count(PARENT_ENGINE_KECCAK) == 1
    text = text.replace(PARENT_ENGINE_KECCAK, engine_pin["runtimeKeccak256"])
else:
    assert text.count(engine_pin["runtimeKeccak256"]) == 1
coordinator_source.write_text(text)
coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
assert coordinator["compiler"] == COMPILER
coordinator_pin = pin(coordinator)
assert coordinator_pin["bytes"] <= 24576

# Rebind only the immutable code/size pins in the copied TreeMap transport.
driver_source = stage / "tools/Go.txt"
text = driver_source.read_text()
for old, new in (
    (PARENT_ENGINE_SHA, engine_pin["runtimeSHA256"]),
    ("0x" + PARENT_ENGINE_KECCAK, "0x" + engine_pin["runtimeKeccak256"]),
    ("0x" + PARENT_COORDINATOR_KECCAK, "0x" + coordinator_pin["runtimeKeccak256"]),
):
    if old in text:
        assert text.count(old) == 1
        text = text.replace(old, new)
    else:
        assert text.count(new) == 1
for pattern, replacement in (
    (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % coordinator_pin["bytes"]),
    (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % engine_pin["bytes"]),
    (r"len\(run\) != \d+", "len(run) != %d" % engine_pin["bytes"]),
):
    text, changed = re.subn(pattern, replacement, text)
    assert changed == 1, (pattern, changed)
driver_source.write_text(text)

parent_pins = json.loads((stage.parent / "parent-4fc3c418b/pins.json").read_text())
pins = {
    "basis": "parent-4fc3c418b", "parentEvidence": "parent-4fc3c418b", "phase": "built",
    "domain": "MC-CLASSCOUNT31-C31", "runtimeCap": 393216, "bootstrapCount": 86,
    "bootstrapSHA256": parent_pins["bootstrapSHA256"],
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [31, 262144], "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 117,
    "address": "0x4d432d434c415353434f554e5433312d43333101",
    "owner": "0x4d432d434c415353434f554e5433312d4f333102",
    "limitsCommitment": parent_pins["limitsCommitment"], "compiler": COMPILER,
    "engine": engine_pin, "coordinator": coordinator_pin,
}
(stage / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py"])

main = out / "main.go"
shutil.copy2(driver_source, main)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
