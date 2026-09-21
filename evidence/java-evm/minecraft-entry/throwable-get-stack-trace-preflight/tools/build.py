#!/usr/bin/env python3
"""Rebuild the generated-only bounded Throwable.getStackTrace image5 stage."""
from pathlib import Path
import json, os, re, shutil, subprocess, sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-66b1622a2"
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-throwable-get-stack-trace-build-") and not out.exists()
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
run("source-verification-prebuild" if not persisted.exists() else "source-verification-prior", [
    sys.executable, here / "verify_source.py", "--prebuild" if not persisted.exists() else "--built",
    *([] if not persisted.exists() else [persisted]),
])

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

# Pin only the already-built EVM artifact facts into the isolated raw ABI driver.
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
    text, count = re.subn(pattern, replacement, text)
    assert count == 1

driver_source.write_text(text)

bootstrap = dict(parent_pins["bootstrapSHA256"])
bootstrap["Throwable"] = "6ea5d86706a5ac3aabc7a7452f746bd9c3209483ee16f1c83948dbe7bd2a0d79"
# Parent provenance is retained in basis/parentEvidence; do not carry its worker
# identity into this separate candidate evidence.
pins = {
    **{key: value for key, value in parent_pins.items() if key != "worker"},
    "basis": "66b1622a2",
    "parentEvidence": "parent-66b1622a2",
    "phase": "built",
    "domain": "MC-THROWABLE-STACK-TRACE-P2",
    "runtimeBaseline": 393007,
    "bootstrapCount": 94,
    "bootstrapSHA256": bootstrap,
    "diagnosticClassBound": 144,
    "address": "0x4d432d5448524f5741424c452d54524143452d31",
    "owner": "0x4d432d5448524f5741424c452d54524143452d32",
    "engine": engine,
    "coordinator": coordinator,
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
