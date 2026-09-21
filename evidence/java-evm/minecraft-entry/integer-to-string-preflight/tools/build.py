#!/usr/bin/env python3
"""Rebuild the generated-only bounded Integer.toString(int) stage."""
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
parent = stage.parent / "parent-12bfded16"
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-integer-to-string-build-") and not out.exists()
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node), "PYTHONDONTWRITEBYTECODE": "1"}


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def pin(directory, contract):
    artifact = json.loads((directory / (contract + ".json")).read_text())
    return {"bytes": len(artifact["deployedBytecode"]) // 2, **artifact["codeHashes"]}


persisted = stage / "build-pins.json"
run("source-verification-prior" if persisted.exists() else "source-verification-prebuild", [
    sys.executable, here / "verify_source.py", "--built", persisted
] if persisted.exists() else [sys.executable, here / "verify_source.py", "--prebuild"])

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = pin(engine_dir, "MCEntryInterpreter")
assert engine["bytes"] <= 393216

parent_pins = json.loads((parent / "pins.json").read_text())
coordinator_source = stage / "coordinator/MCEntryCoordinator.sol"
text = coordinator_source.read_text()
old = parent_pins["engine"]["runtimeKeccak256"]
if old in text:
    assert text.count(old) == 1
    text = text.replace(old, engine["runtimeKeccak256"])
else:
    assert text.count(engine["runtimeKeccak256"]) == 1
coordinator_source.write_text(text)
coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = pin(coordinator_dir, "MCEntryCoordinator")
assert coordinator["bytes"] == parent_pins["coordinator"]["bytes"] == 5394

# The raw ABI driver records only facts from freshly rebuilt EVM artifacts.
driver_source = stage / "tools/Go.txt"
text = driver_source.read_text()
for old, new in (
    (parent_pins["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
    ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
    ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
):
    if old in text:
        assert text.count(old) == 1
        text = text.replace(old, new)
    else:
        assert text.count(new) == 1
for pattern, replacement in (
    (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % coordinator["bytes"]),
    (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % engine["bytes"]),
    (r"len\(run\) != \d+", "len(run) != %d" % engine["bytes"]),
):
    text, changed = re.subn(pattern, replacement, text)
    assert changed == 1
driver_source.write_text(text)

image = bytes.fromhex((stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip())
bootstrap = dict(parent_pins["bootstrapSHA256"])
bootstrap["Integer"] = hashlib.sha256(image).hexdigest()
pins = {
    **{key: value for key, value in parent_pins.items() if key != "worker"},
    "basis": "12bfded16", "parentEvidence": "parent-12bfded16", "phase": "built",
    "domain": "MC-INTEGER-TO-STRING-P1", "runtimeBaseline": 367072,
    "bootstrapCount": 94, "bootstrapSHA256": bootstrap,
    "diagnosticClassBound": 144,
    "address": "0x4d432d494e542d544f535452494e472d30303031",
    "owner": "0x4d432d494e542d544f535452494e472d30303032",
    "engine": engine, "coordinator": coordinator,
}
if persisted.exists():
    assert json.loads(persisted.read_text()) == pins
else:
    persisted.write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py", "--built", persisted])

main = out / "main.go"
shutil.copy2(driver_source, main)
for label, command in (
    ("gofmt", ["gofmt", "-w", main]),
    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
    ("go-vet", ["go", "vet", main]),
):
    run(label, command)
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coordinator}, indent=2))
