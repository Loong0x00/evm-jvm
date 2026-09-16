#!/usr/bin/env python3
"""One reproducible LOCAL source build for guest Properties.load(InputStream)."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-properties-load-build-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
if not node_modules.is_dir():
    raise RuntimeError("pinned local solc is unavailable; refusing shared or network dependencies")
out.mkdir(); (out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())


def pin(data):
    return {"bytes": len(data["deployedBytecode"]) // 2, **data["codeHashes"]}


run("source-verification-prebuild", [sys.executable, here / "verify_source.py", "--prebuild"])
parent_pins = json.loads((stage.parent / "parent-c96c326bc/pins.json").read_text())

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
engine_pin = pin(engine)
assert engine["compiler"] == parent_pins["compiler"]
assert engine_pin["bytes"] <= 393216
source = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
assert source.count('ENGINE_CODEHASH = hex"' + engine_pin["runtimeKeccak256"] + '"') == 1

coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
coordinator_pin = pin(coordinator)
assert coordinator["compiler"] == parent_pins["compiler"]
assert coordinator_pin["bytes"] <= 24576

main = out / "main.go"
shutil.copy2(stage / "tools/Go.txt", main)
text = main.read_text()
for needle in (
    engine_pin["runtimeSHA256"], "0x" + engine_pin["runtimeKeccak256"],
    "0x" + coordinator_pin["runtimeKeccak256"],
    "len(engineRun) != %d" % engine_pin["bytes"],
    "len(run) != %d" % engine_pin["bytes"],
    "len(coordRun) != %d" % coordinator_pin["bytes"],
):
    assert text.count(needle) == 1, needle
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)

properties_hex = (stage / "bootstrap/java/util/Properties.class.hex").read_text().strip()
pins = {
    "basis": "parent-c96c326bc", "parentEvidence": "parent-c96c326bc", "phase": "built",
    "domain": "MC-PROPERTIES-LOAD-P1", "runtimeCap": 393216, "bootstrapCount": 86,
    "bootstrapSHA256": {**parent_pins["bootstrapSHA256"],
                           "Properties": hashlib.sha256(bytes.fromhex(properties_hex)).hexdigest()},
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [32, 262144], "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 118,
    "address": "0x4d432d50524f50532d4c4f41442d50312d303030",
    "owner": "0x4d432d50524f50532d4c4f41442d4f574e455230",
    "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
    "engine": engine_pin, "coordinator": coordinator_pin,
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py", "--built", out / "pins.json"])
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
