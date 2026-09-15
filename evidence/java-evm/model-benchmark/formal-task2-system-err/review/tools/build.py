#!/usr/bin/env python3
"""One reproducible LOCAL384 System.err source build; generated inputs only."""
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
assert out.name.startswith("java-diff-mc-system-err-build-")
assert not out.exists()
# Do not fall through to a shared/sibling dependency tree. The task must build from
# this isolated worktree's pinned solc installation or stop before execution.
node_modules = root / "jvmevm/runtime/node_modules"
if not node_modules.is_dir():
    raise RuntimeError("pinned local solc is unavailable in this isolated worktree; refusing shared or network dependencies")
out.mkdir()
(out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")

parent_engine_sha = "3944c4392408f79070728acfa2976fed825ca7c07b8d0d7436fb19277ccf857b"
parent_engine_keccak = "e5baac0ddccaa86a471b2e0e53b63374db401f82ca6fe95643f1a64a21a0cb33"
parent_coordinator_keccak = "52cdb66227f1a3b7046336959d726059dc45e17d0b553659a7cad0627499c142"

def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)

def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())

# This also recompiles the two images with the pinned Java-8 compiler and proves the
# precise parent delta before any EVM artifact is made.
run("source-verification", [sys.executable, here / "verify_source.py"])

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
engine_pin = {"bytes": len(engine["deployedBytecode"]) // 2, **engine["codeHashes"]}
if engine_pin["bytes"] > 393216:
    raise RuntimeError("LOCAL384 runtime cap exceeded: %d > 393216" % engine_pin["bytes"])

# The source template remains parent-pinned. Only this disposable compiler input is
# rebound to the candidate engine hash.
coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
coordinator_source = coordinator_dir / "MCEntryCoordinator.sol"
text = coordinator_source.read_text()
assert text.count(parent_engine_keccak) == 1
coordinator_source.write_text(text.replace(parent_engine_keccak, engine_pin["runtimeKeccak256"]))
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
coordinator_pin = {"bytes": len(coordinator["deployedBytecode"]) // 2, **coordinator["codeHashes"]}
assert coordinator_pin["bytes"] == 4146

# The driver source is likewise immutable: substitutions are made only in the build
# copy after both runtime hashes are known.
driver_source = (stage / "tools/Go.txt").read_text()
for old, new in (
    (parent_engine_sha, engine_pin["runtimeSHA256"]),
    ("0x" + parent_engine_keccak, "0x" + engine_pin["runtimeKeccak256"]),
    ("0x" + parent_coordinator_keccak, "0x" + coordinator_pin["runtimeKeccak256"]),
):
    assert driver_source.count(old) == 1, old
    driver_source = driver_source.replace(old, new)
for pattern, replacement, expected in (
    (r"len\(engineRun\) != 393205", "len(engineRun) != %d" % engine_pin["bytes"], 1),
    (r"len\(run\) != 393205", "len(run) != %d" % engine_pin["bytes"], 1),
):
    driver_source, count = re.subn(pattern, replacement, driver_source)
    assert count == expected, (pattern, count)
main = out / "main.go"
main.write_text(driver_source)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)

pins = {
    "basis": "de60a3245", "parentEvidence": "parent-de60a3245", "phase": "built",
    "domain": "MC-SYSTEM-ERR-PRNT1", "runtimeCap": 393216,
    "bootstrapCount": 84,
    "bootstrapSHA256": {
        "System": "4b0c92d2908cf30aa4df0bd0ee6f737d4fa8f7aff1872be3d882bc729d4e5e6e",
        "PrintStream": "ab20e0463e529c30c6f6c5668561145ae57f8c9b735a7cc95b5863a0d5db6fa0",
        "EnumSet": "ab36a2f498e571717f53554bb485b5d84a38616fc376f1af7a0f5a66846ff230",
    },
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [30, 262144], "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 114,
    "address": "0x4d432d53595354454d2d4552522d50524e543100",
    "owner": "0x4d432d53595354454d2d4552522d4f574e523100",
    "limitsCommitment": "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e",
    "engine": engine_pin, "coordinator": coordinator_pin,
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
