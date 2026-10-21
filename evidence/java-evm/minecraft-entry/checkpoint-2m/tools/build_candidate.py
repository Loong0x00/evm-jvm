#!/usr/bin/env python3
"""Reproducibly build the append-only P33 2 MiB checkpoint-only profile."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
BASE = STAGE.parent / "checkpoint-2m-base-p33"
ROOT = STAGE.parents[3]
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-checkpoint-2m-")
assert not OUT.exists()
OUT.mkdir()
(OUT / "tmp").mkdir()
env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"),
           TMPDIR=str(OUT / "tmp"), GOPROXY="off", GOSUMDB="off",
           PYTHONDONTWRITEBYTECODE="1")


def run(label: str, args: list[object]) -> None:
    with (OUT / f"{label}.log").open("w") as stream:
        subprocess.run(list(map(str, args)), cwd=ROOT, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=900)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

pins = json.loads((STAGE / "pins.json").read_text())
shutil.copytree(STAGE / "engine", OUT / "engine")
run("engine-build", ["node", OUT / "engine/build.js"])
engine_artifact_path = OUT / "engine/MCEntryInterpreter.json"
artifact = json.loads(engine_artifact_path.read_text())
engine_runtime = bytes.fromhex(artifact["deployedBytecode"].removeprefix("0x"))
assert len(engine_runtime) == pins["engineRuntimeBytes"]
assert len(engine_runtime) <= pins["runtimeCapBytes"] == 1048576
assert artifact["sourceHashes"]["MCEntryInterpreter.sol"] == pins["engineSourceSHA256"]
assert artifact["codeHashes"]["runtimeSHA256"] == pins["engineRuntimeSHA256"]
assert artifact["codeHashes"]["runtimeKeccak256"].removeprefix("0x") == pins["engineRuntimeKeccak256"]

# Constant-only interpreter changes must preserve the accepted ABI and storage layout.
base_artifact = json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())
assert artifact["abi"] == base_artifact["abi"]
assert artifact["storageLayout"] == base_artifact["storageLayout"]
run("source-verification", [sys.executable, HERE / "verify_source.py"])

coordinator_dir = OUT / "coordinator"
shutil.copytree(STAGE / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator_artifact_path = coordinator_dir / "MCEntryCoordinator.json"
coordinator_artifact = json.loads(coordinator_artifact_path.read_text())
coordinator_runtime = bytes.fromhex(coordinator_artifact["deployedBytecode"].removeprefix("0x"))
assert len(coordinator_runtime) == pins["coordinatorRuntimeBytes"]
assert len(coordinator_runtime) <= 24576
assert coordinator_artifact["sourceHashes"]["MCEntryCoordinator.sol"] == pins["coordinatorSourceSHA256"]
assert coordinator_artifact["codeHashes"]["runtimeSHA256"] == pins["coordinatorRuntimeSHA256"]
assert coordinator_artifact["codeHashes"]["runtimeKeccak256"].removeprefix("0x") == pins["coordinatorRuntimeKeccak256"]
assert sha(coordinator_runtime) == pins["coordinatorRuntimeSHA256"]

# Runtime remains 1 MiB-capped; only the distinct application checkpoint budget is 2 MiB.
pins.update(
    engine={"bytes": len(engine_runtime), **artifact["codeHashes"]},
    coordinator={"bytes": len(coordinator_runtime), **coordinator_artifact["codeHashes"]},
    runtimeCapBytes=1048576,
    checkpointCapBytes=2097152,
    bootstrapCount=100,
    diagnosticClassMaximum=250,
    rawClassLimit=150,
    rawByteLimit=1063930,
    status="P33 checkpoint-only 2 MiB source proof compiled; generated-only positive/refusal/reopen gates pending",
)
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({
    "profile": pins["profile"],
    "runtimeBytes": len(engine_runtime),
    "runtimeCapBytes": pins["runtimeCapBytes"],
    "checkpointCapBytes": pins["checkpointCapBytes"],
    "rawClassLimit": pins["rawClassLimit"],
    "rawByteLimit": pins["rawByteLimit"],
    "bootstrapCount": pins["bootstrapCount"],
    "globalNativeBindings": pins["globalNativeBindings"],
    "engineRuntimeSHA256": artifact["codeHashes"]["runtimeSHA256"],
    "engineRuntimeKeccak256": artifact["codeHashes"]["runtimeKeccak256"],
    "coordinatorRuntimeBytes": len(coordinator_runtime),
    "coordinatorRuntimeKeccak256": coordinator_artifact["codeHashes"]["runtimeKeccak256"],
    "sourceDeltaOnlyCheckpointBudget": True,
}, indent=2))
