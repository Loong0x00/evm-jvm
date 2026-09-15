#!/usr/bin/env python3
"""One reproducible StringBuilder image85 build from only local pinned inputs."""
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-string-builder-build-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
if not node_modules.is_dir():
    raise RuntimeError("pinned local solc is unavailable; refusing shared or network dependencies")
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
out.mkdir(); (out / "tmp").mkdir()

PARENT_ENGINE_SHA = "15e17e3d6ad5674f30bc6daa64f88609d1376021ed79168e5cbc19afc83a0f6e"
PARENT_ENGINE_KECCAK = "fcdbb9f1ff129f17085127e6b4713ae41f8d8fd00a538d958ac0ad6863b616fc"
PARENT_COORDINATOR_KECCAK = "0372a7d0bf067705f86a72e7168485bfb1da856ac1212905a64b8f27cd2d004e"
COMPILER = {
    "version": "0.8.30+commit.73712a01.Emscripten.clang",
    "optimizer": {"enabled": True, "runs": 200}, "viaIR": True, "evmVersion": "cancun",
    "metadata": {"appendCBOR": False, "bytecodeHash": "none"},
}

def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)

def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())

run("source-verification", [sys.executable, here / "verify_source.py"])
engine_dir = out / "engine"; shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
assert engine["compiler"] == COMPILER
engine_pin = {"bytes": len(engine["deployedBytecode"]) // 2, **engine["codeHashes"]}
assert engine_pin["bytes"] <= 393216

coordinator_dir = out / "coordinator"; shutil.copytree(stage / "coordinator", coordinator_dir)
coordinator_source = coordinator_dir / "MCEntryCoordinator.sol"
text = coordinator_source.read_text()
assert text.count(PARENT_ENGINE_KECCAK) == 1
coordinator_source.write_text(text.replace(PARENT_ENGINE_KECCAK, engine_pin["runtimeKeccak256"]))
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
assert coordinator["compiler"] == COMPILER
coordinator_pin = {"bytes": len(coordinator["deployedBytecode"]) // 2, **coordinator["codeHashes"]}
assert coordinator_pin["bytes"] == 4146

# The immutable parent driver is rebound only in this disposable build copy after
# both local runtime hashes are known.
driver_source = (stage / "tools/Go.txt").read_text()
for old, new in (
    (PARENT_ENGINE_SHA, engine_pin["runtimeSHA256"]),
    ("0x" + PARENT_ENGINE_KECCAK, "0x" + engine_pin["runtimeKeccak256"]),
    ("0x" + PARENT_COORDINATOR_KECCAK, "0x" + coordinator_pin["runtimeKeccak256"]),
):
    assert driver_source.count(old) == 1, old
    driver_source = driver_source.replace(old, new)
for pattern, replacement in (
    (r"len\(engineRun\) != 392775", "len(engineRun) != %d" % engine_pin["bytes"]),
    (r"len\(run\) != 392775", "len(run) != %d" % engine_pin["bytes"]),
):
    driver_source, count = re.subn(pattern, replacement, driver_source)
    assert count == 1, (pattern, count)
main = out / "main.go"; main.write_text(driver_source)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)

pins = {
    "basis": "89928ece8", "parentEvidence": "parent-89928ece8", "phase": "built",
    "domain": "MC-STRING-BUILDER-P1", "runtimeCap": 393216, "bootstrapCount": 85,
    "bootstrapSHA256": {
        "System": "4b0c92d2908cf30aa4df0bd0ee6f737d4fa8f7aff1872be3d882bc729d4e5e6e",
        "PrintStream": "ab20e0463e529c30c6f6c5668561145ae57f8c9b735a7cc95b5863a0d5db6fa0",
        "EnumSet": "ab36a2f498e571717f53554bb485b5d84a38616fc376f1af7a0f5a66846ff230",
        "StringBuilder": "463d7859579627eff6065316f7c9759fb4648768c80ed29656e988db0a662832",
    },
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [30, 262144], "checkpointCap": 1048576, "headCap": 32768,
    "diagnosticClassBound": 115,
    "address": "0x4d432d535452494e472d4255494c4445522d5031",
    "owner": "0x4d432d535452494e472d4255494c4445522d4f31",
    "limitsCommitment": "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e",
    "compiler": COMPILER, "engine": engine_pin, "coordinator": coordinator_pin,
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
