#!/usr/bin/env python3
"""Build the disposable P22 coordinator/driver around the MAX_ARRAYS candidate."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NODE_MODULES = ROOT / "jvmevm/runtime/node_modules"
BASE = ROOT / "evidence/java-evm/minecraft-entry/parent-max-objects-2048"
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-max-arrays-4096-build-") and not OUT.exists()


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def run(label: str, command: list[str], env: dict[str, str]) -> None:
    with (OUT / (label + ".log")).open("w") as stream:
        subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=900)


OUT.mkdir()
engine_dir = OUT / "engine"
shutil.copytree(HERE / "engine", engine_dir)
engine = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_bytes = len(engine["deployedBytecode"]) // 2
assert engine_bytes == 392090 and engine_bytes <= 393216
engine_keccak = engine["codeHashes"]["runtimeKeccak256"]
engine_sha = engine["codeHashes"]["runtimeSHA256"]

coord_dir = OUT / "coordinator"
shutil.copytree(HERE / "coordinator", coord_dir)
base_coord_source = (BASE / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord_source_path = coord_dir / "MCEntryCoordinator.sol"
coord_source = coord_source_path.read_text()
old_engine_hash = "ef0e7eaeadaee06b0fe3ea84d6d53e49d36a5f9534ab6c23312b08688c8de295"
assert coord_source == base_coord_source
assert coord_source.count(old_engine_hash) == 1
coord_source = coord_source.replace(old_engine_hash, engine_keccak, 1)
coord_source_path.write_text(coord_source)

env = {**os.environ, "NODE_PATH": str(NODE_MODULES), "npm_config_offline": "true",
       "GOPROXY": "off", "GOSUMDB": "off", "PYTHONDONTWRITEBYTECODE": "1"}
run("coordinator-build", ["node", coord_dir / "build.js"], env)
coord = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord_bytes = len(coord["deployedBytecode"]) // 2
assert coord_bytes == 5394
coord_keccak = coord["codeHashes"]["runtimeKeccak256"]
coord_sha = coord["codeHashes"]["runtimeSHA256"]
parent_coord_artifact = json.loads((BASE / "artifacts/coordinator/MCEntryCoordinator.json").read_text())
assert coord["abi"] == parent_coord_artifact["abi"]
assert coord["storageLayout"] == parent_coord_artifact["storageLayout"]

# The coordinator's sole source delta is the newly compiled engine code hash.
assert coord_source == base_coord_source.replace(old_engine_hash, engine_keccak, 1)

# Use the retained canonical public-API driver, updating only immutable artifacts.
driver_source = (BASE / "canonical-driver.go.txt").read_text()
replacements = {
    'const immutableEngineSHA256 = "cb750e9f0e938f9e195ee66ba38c0ff0a70db1833bd14402b8247deabf8efd70"':
        f'const immutableEngineSHA256 = "{engine_sha}"',
    'const immutableEngineKeccak = "0xef0e7eaeadaee06b0fe3ea84d6d53e49d36a5f9534ab6c23312b08688c8de295"':
        f'const immutableEngineKeccak = "0x{engine_keccak}"',
    'const immutableCoordinatorKeccak = "0x7647539b6cf3ffb1ed4c309da3bc8c10e7e08ca0fdc3e9d9305c6f12a70a84d4"':
        f'const immutableCoordinatorKeccak = "0x{coord_keccak}"',
}
for old, new in replacements.items():
    assert driver_source.count(old) == 1, old
    driver_source = driver_source.replace(old, new, 1)
assert 'const format = "MC-RANDOM-CLASS-P22-BOUNDED-1"' in driver_source
assert 'len(run) != 392090' in driver_source
assert 'len(coordRun) != 5394' in driver_source
(out_dir := OUT / "main.go").write_text(driver_source)
run("gofmt", ["gofmt", "-w", out_dir], env)
run("go-build", ["go", "build", "-trimpath", "-o", OUT / "driver", out_dir], env)
run("go-vet", ["go", "vet", out_dir], env)

parent_pins = json.loads((BASE / "artifacts/parent-build-pins.json").read_text())
pins = {**parent_pins,
        "profile": "MC-RANDOM-CLASS-P22-MAX-ARRAYS-4096-worker-candidate",
        "maxArrays": 4096, "maxObjects": 2048, "maxHandles": 6401,
        "engine": {"bytes": engine_bytes,
                   "initSHA256": engine["codeHashes"]["initSHA256"],
                   "runtimeSHA256": engine_sha, "runtimeKeccak256": engine_keccak},
        "coordinator": {"bytes": coord_bytes,
                        "initSHA256": coord["codeHashes"]["initSHA256"],
                        "runtimeSHA256": coord_sha, "runtimeKeccak256": coord_keccak},
        "sourceInvariants": {"normalizedDelta": "MAX_ARRAYS2048->4096 only",
                             "parentBootstrapRoot": parent_pins["bootstrapRoot"],
                             "orderedLeaves": 97}}
pins["expectedBootstrapRoot"] = parent_pins["bootstrapRoot"]
pins["driverSHA256"] = sha(driver_source.encode())
pins["coordinatorSourceSHA256"] = sha(coord_source.encode())
pins["candidateSourceSHA256"] = engine["sourceHashes"]["MCEntryInterpreter.sol"]
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"buildDir": str(OUT), "engine": pins["engine"],
                  "coordinator": pins["coordinator"], "driverSHA256": pins["driverSHA256"],
                  "maxArrays": pins["maxArrays"], "maxObjects": pins["maxObjects"],
                  "maxHandles": pins["maxHandles"], "domain": pins["domain"]}, indent=2))
