#!/usr/bin/env python3
"""One reproducible LOCAL source build for raw34 / byte268053."""
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
assert out.name.startswith("java-diff-mc-classcount34-byte268053-build-") and not out.exists()
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


def pin(artifact_data):
    return {"bytes": len(artifact_data["deployedBytecode"]) // 2, **artifact_data["codeHashes"]}


parent_pins = json.loads((stage.parent / "parent-cc433baf7/pins.json").read_text())
persisted = stage / "build-pins.json"
if persisted.exists():
    run("source-verification-prior", [sys.executable, here / "verify_source.py", "--built", persisted])
else:
    run("source-verification-prebuild", [sys.executable, here / "verify_source.py", "--prebuild"])

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
engine_pin = pin(engine)
assert engine["compiler"] == parent_pins["compiler"]
assert engine_pin["bytes"] <= 393216
assert 393216 - engine_pin["bytes"] == 156

coordinator_source = stage / "coordinator/MCEntryCoordinator.sol"
text = coordinator_source.read_text()
old_engine = parent_pins["engine"]["runtimeKeccak256"]
if old_engine in text:
    assert text.count(old_engine) == 1
    text = text.replace(old_engine, engine_pin["runtimeKeccak256"])
else:
    assert text.count(engine_pin["runtimeKeccak256"]) == 1
coordinator_source.write_text(text)
coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
coordinator_pin = pin(coordinator)
assert coordinator["compiler"] == parent_pins["compiler"]
assert coordinator_pin["bytes"] <= 24576

driver_source = stage / "tools/Go.txt"
text = driver_source.read_text()
for old, new in (
    (parent_pins["engine"]["runtimeSHA256"], engine_pin["runtimeSHA256"]),
    ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + engine_pin["runtimeKeccak256"]),
    ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + coordinator_pin["runtimeKeccak256"]),
):
    if old in text:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    else:
        assert text.count(new) == 1, new
for pattern, replacement in (
    (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % coordinator_pin["bytes"]),
    (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % engine_pin["bytes"]),
    (r"len\(run\) != \d+", "len(run) != %d" % engine_pin["bytes"]),
):
    text, changed = re.subn(pattern, replacement, text)
    assert changed == 1, (pattern, changed)
driver_source.write_text(text)

pins = {
    "basis": "6032de1ac", "parentEvidence": "parent-cc433baf7", "phase": "built",
    "domain": "MC-CLASSCOUNT34-BYTE268053-P1", "runtimeCap": 393216, "bootstrapCount": 88,
    "bootstrapSHA256": parent_pins["bootstrapSHA256"],
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [34, 268053], "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 122,
    "address": "0x4d432d434333342d42593236383035332d454e47",
    "owner": "0x4d432d434333342d42593236383035332d4f574e",
    "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
    "engine": engine_pin, "coordinator": coordinator_pin,
}
if persisted.exists():
    assert json.loads(persisted.read_text()) == pins
else:
    persisted.write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py", "--built", out / "pins.json"])

main = out / "main.go"
shutil.copy2(driver_source, main)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
