#!/usr/bin/env python3
"""Build the Object.hashCode candidate and pinned generated-only runner offline."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 3, "build.py BUILD_DIR FIXTURES_DIR"
out, fixtures = (Path(value).resolve() for value in sys.argv[1:])
assert out.parent == fixtures.parent == root / "build"
assert out.name.startswith("java-diff-mc-object-hash-code-build-") and not out.exists()
assert fixtures.name.startswith("java-diff-mc-object-hash-code-fixtures-") and fixtures.is_dir()
root_build = root / "build"; root_build.mkdir(exist_ok=True)
baseline = json.loads((stage / "baseline-pins.json").read_text())
source_pre = json.loads((stage / "results/source-verification.json").read_text())
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "pinned local solc unavailable; no network fallback"
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules),
       "PYTHONDONTWRITEBYTECODE": "1"}


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())


def runtime_pin(value):
    runtime = bytes.fromhex(value["deployedBytecode"])
    return {"bytes": len(runtime), **value["codeHashes"]}


run("source-verification-prebuild", [sys.executable, here / "verify_source.py"])
source_pre = json.loads((stage / "results/source-verification.json").read_text())

engine_dir = out / "engine"; shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = artifact(engine_dir, "MCEntryInterpreter")
engine = runtime_pin(engine_artifact)
assert engine_artifact["compiler"] == baseline["compiler"]
assert engine["bytes"] <= baseline["runtimeCap"] == 393216

# Preserve the accepted coordinator exactly except its constructor-bound engine
# runtime codehash. Accept both the pristine and already-patched tracked source
# so reruns from a completed worktree are deterministic.
coord_source = stage / "coordinator/MCEntryCoordinator.sol"
coord_text = coord_source.read_text()
old_coord = (stage.parent / "parent-cd8122975/artifacts/coordinator/MCEntryCoordinator.sol").read_text()
old_hash = baseline["engineRuntimeKeccak256"]
new_hash = engine["runtimeKeccak256"]
assert coord_text in (old_coord, old_coord.replace(old_hash, new_hash))
if old_hash in coord_text:
    assert coord_text.count(old_hash) == 1
    coord_text = coord_text.replace(old_hash, new_hash)
coord_source.write_text(coord_text)

coordinator_dir = out / "coordinator"; shutil.copytree(stage / "coordinator", coordinator_dir)
shutil.copy2(coord_source, coordinator_dir / "MCEntryCoordinator.sol")
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator_artifact = artifact(coordinator_dir, "MCEntryCoordinator")
coordinator = runtime_pin(coordinator_artifact)
assert coordinator_artifact["compiler"] == baseline["compiler"]
assert coordinator["bytes"] == baseline["coordinatorBytes"]

# Re-pin only the accepted canonical driver to candidate engine/coordinator
# hashes and compiled engine length; all Local budgets and transport controls
# remain byte-identical.
p12_driver = (stage.parent / "parent-cd8122975/canonical-driver.go.txt").read_text()
driver_path = stage / "tools/Go.txt"
driver_text = driver_path.read_text()
expected_driver = p12_driver
for old, new in (
    (baseline["engineRuntimeSHA256"], engine["runtimeSHA256"]),
    ("0x" + baseline["engineRuntimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
    ("0x" + baseline["coordinatorRuntimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
):
    if old in expected_driver:
        assert expected_driver.count(old) == 1
        expected_driver = expected_driver.replace(old, new)
    else:
        assert expected_driver.count(new) == 1
expected_driver, changed = re.subn(
    r"len\(engineRun\) != " + str(baseline["engineBytes"]),
    "len(engineRun) != %d" % engine["bytes"], expected_driver)
assert changed == 1
expected_driver, changed = re.subn(
    r"len\(run\) != " + str(baseline["engineBytes"]),
    "len(run) != %d" % engine["bytes"], expected_driver)
assert changed == 1
assert driver_text in (p12_driver, expected_driver)
driver_path.write_text(expected_driver)
main = out / "main.go"; main.write_text(expected_driver)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)

pins = {
    "phase": "generated-only bounded Object.hashCode()I",
    "basis": baseline["basis"], "domain": baseline["domain"],
    "bootstrapCount": baseline["bootstrapCount"],
    "bootstrapRoot": source_pre["bootstrapRoot"],
    "changedBootstrapIndices": [0], "unchangedOtherBootstrapImages": 96,
    "object": {"slot": 0, "bytes": source_pre["objectImageBytes"],
        "sha256": source_pre["objectImageSHA256"],
        "keccak256": source_pre["objectImageKeccak256"],
        "surface": "accepted Object constructor/equals/getClass plus ordinary hashCode()I returning System.identityHashCode(this)",
        "java8": "javac -source 8 -target 8 -g:none"},
    "globalNativeBindings": baseline["globalNativeBindings"],
    "stringLocalBinding": baseline["stringLocalBinding"],
    "rawLimits": baseline["rawLimits"],
    "diagnosticClassBound": baseline["diagnosticClassBound"],
    "checkpointCap": baseline["checkpointCap"], "headCap": baseline["headCap"],
    "reserve": baseline["reserve"], "ordinaryGas": baseline["ordinaryGas"],
    "runtimeCap": baseline["runtimeCap"], "maxFrames": baseline["maxFrames"],
    "exceptionKinds": baseline["exceptionKinds"], "sparseWire": baseline["sparseWire"],
    "address": baseline["engineAddress"], "owner": baseline["ownerAddress"],
    "compiler": baseline["compiler"], "engine": engine, "coordinator": coordinator,
    "sourceVerification": source_pre,
    "transport": "accepted P12 canonical driver, only candidate bytecode hashes/engine length re-pinned",
}
(stage / "build-pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(stage / "results/build-pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py", "--built"])
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coordinator,
                  "bootstrapRoot": pins["bootstrapRoot"], "object": pins["object"],
                  "ordinaryGas": pins["ordinaryGas"], "runtimeCap": pins["runtimeCap"]}, indent=2))
