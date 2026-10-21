#!/usr/bin/env python3
"""Fresh LOCAL1M build for the Java 8 Math double min/max profile."""
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
ROOT = STAGE.parents[3]
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-math-double-min-max-")
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


shutil.copytree(STAGE / "engine", OUT / "engine")
run("engine-build", ["node", OUT / "engine/build.js"])
artifact = json.loads((OUT / "engine/MCEntryInterpreter.json").read_text())
engine_runtime = bytes.fromhex(artifact["deployedBytecode"].removeprefix("0x"))
pins = json.loads((STAGE / "pins.json").read_text())
assert len(engine_runtime) == pins["engineRuntimeBytes"], f"unexpected measured runtime size {len(engine_runtime)}"
assert len(engine_runtime) <= 1048576
assert artifact["sourceHashes"]["MCEntryInterpreter.sol"] == pins["engineSourceSHA256"]
assert artifact["codeHashes"]["runtimeSHA256"] == pins["engineRuntimeSHA256"]
assert artifact["codeHashes"]["runtimeKeccak256"].removeprefix("0x") == pins["engineRuntimeKeccak256"]
run("source-verification", [sys.executable, HERE / "verify_source.py"])
pins.update(
    engine={"bytes": len(engine_runtime), **artifact["codeHashes"]},
    runtimeCapBytes=1048576,
    checkpointCapBytes=1048576,
    bootstrapCount=100,
    diagnosticClassMaximum=250,
    status="LOCAL1M 100-image Java 8 Math min/max source proof compiled; generated full-IEEE behavior gates pending",
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
    "diagnosticClassMaximum": pins["diagnosticClassMaximum"],
    "engineRuntimeSHA256": artifact["codeHashes"]["runtimeSHA256"],
    "engineRuntimeKeccak256": artifact["codeHashes"]["runtimeKeccak256"],
    "scopedSourceProof": True,
}, indent=2))
