#!/usr/bin/env python3
"""Offline build of the sparse-checkpoint candidate and its bounded EVM harness."""
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-sparse-array-build-") and not out.exists()
baseline = json.loads((stage / "baseline-pins.json").read_text())
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "offline build requires already-pinned node_modules"
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node), "PYTHONDONTWRITEBYTECODE": "1"}

def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)

run("source-invariants", [sys.executable, here / "verify_source.py"])
engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_code = bytes.fromhex(engine_artifact["deployedBytecode"])
engine = {"bytes": len(engine_code), **engine_artifact["codeHashes"]}
assert engine["bytes"] <= baseline["runtimeCap"] == 393216

coord_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coord_dir)
coord_source = coord_dir / "MCEntryCoordinator.sol"
text = coord_source.read_text()
old_hash = baseline["engine"]["runtimeKeccak256"]
assert text.count(old_hash) == 1
text = text.replace(old_hash, engine["runtimeKeccak256"])
coord_source.write_text(text)
run("coordinator-build", ["node", coord_dir / "build.js"])
coord_artifact = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord = {"bytes": len(bytes.fromhex(coord_artifact["deployedBytecode"])),
         **coord_artifact["codeHashes"]}
assert coord["bytes"] == baseline["coordinator"]["bytes"]

main = (stage / "tools/Go.txt").read_text()
for old, new in (
    (baseline["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
    ("0x" + baseline["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
    ("0x" + baseline["coordinator"]["runtimeKeccak256"], "0x" + coord["runtimeKeccak256"]),
):
    assert main.count(old) == 1, (old, main.count(old))
    main = main.replace(old, new)
main, count = re.subn(r"len\(engineRun\) != 383245", f"len(engineRun) != {engine['bytes']}", main)
assert count == 1
main, count = re.subn(r"len\(run\) != 383245", f"len(run) != {engine['bytes']}", main)
assert count == 1
main_path = out / "main.go"
main_path.write_text(main)
for label, command in (("gofmt", ["gofmt", "-w", main_path]),
                       ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main_path]),
                       ("go-vet", ["go", "vet", main_path])):
    run(label, command)

pins = dict(baseline)
pins.update({"phase": "built-sparse-primitive-array-candidate",
             "baselineCommit": "511c20c4b", "sparseWire": {"flag": "0x80000000",
             "minimumLength": 1024, "savingRule": "(4+12*nonzero)*4 <= (8*length)*3"},
             "engine": engine, "coordinator": coord})
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coord,
                  "runtimeCap": pins["runtimeCap"], "externalLocalGas": pins["externalLocalGas"]}, indent=2))
