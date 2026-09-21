#!/usr/bin/env python3
"""Build the exact bounded System.setOut stage with local pinned tools only."""
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
parent = stage.parent / "parent-1b178a6eb"
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-system-set-out-build-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1"}
def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
def artifact(directory, name): return json.loads((directory / (name + ".json")).read_text())
def pin(value): return {"bytes": len(value["deployedBytecode"]) // 2, **value["codeHashes"]}
def image_sha(path): return hashlib.sha256(bytes.fromhex("".join(path.read_text().split()))).hexdigest()

persisted = stage / "build-pins.json"
run("source-verification-prior" if persisted.exists() else "source-verification-prebuild",
    [sys.executable, here / "verify_source.py", "--built", persisted] if persisted.exists()
    else [sys.executable, here / "verify_source.py", "--prebuild"])
parent_pins = json.loads((parent / "pins.json").read_text())
engine_dir = out / "engine"; shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = pin(artifact(engine_dir, "MCEntryInterpreter")); assert engine["bytes"] <= 393216, engine

coordinator_source = stage / "coordinator/MCEntryCoordinator.sol"
text = coordinator_source.read_text(); old_engine = parent_pins["engine"]["runtimeKeccak256"]
if old_engine in text:
    assert text.count(old_engine) == 1; text = text.replace(old_engine, engine["runtimeKeccak256"])
else:
    assert text.count(engine["runtimeKeccak256"]) == 1
old_address = parent_pins["address"][2:]; new_address = "4d432d53595354454d2d5345542d4f55542d3031"
if old_address in text:
    assert text.count(old_address) == 1; text = text.replace(old_address, new_address)
else:
    assert text.count(new_address) == 1
old_domain = parent_pins["domain"]; new_domain = "MC-SYSTEM-SET-OUT-001"
if old_domain in text:
    assert text.count(old_domain) == 4; text = text.replace(old_domain, new_domain)
else:
    assert text.count(new_domain) == 4
coordinator_source.write_text(text)
coordinator_dir = out / "coordinator"; shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = pin(artifact(coordinator_dir, "MCEntryCoordinator")); assert coordinator["bytes"] == parent_pins["coordinator"]["bytes"] == 5394

driver = stage / "tools/Go.txt"; text = driver.read_text()
for old, new in ((parent_pins["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
                 ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
                 ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
                 (parent_pins["address"], "0x4d432d53595354454d2d5345542d4f55542d3031"),
                 (parent_pins["owner"], "0x4d432d53595354454d2d5345542d4f55542d3032")):
    if old in text:
        assert text.count(old) == 1; text = text.replace(old, new)
    else: assert text.count(new) == 1
old_domain = parent_pins["domain"]; new_domain = "MC-SYSTEM-SET-OUT-001"
if old_domain in text:
    assert text.count(old_domain) == 6; text = text.replace(old_domain, new_domain)
else:
    assert text.count(new_domain) == 6
for pattern, replacement in ((r"len\(coordRun\) != \d+", "len(coordRun) != %d" % coordinator["bytes"]),
                             (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % engine["bytes"]),
                             (r"len\(run\) != \d+", "len(run) != %d" % engine["bytes"])):
    text, count = re.subn(pattern, replacement, text); assert count == 1, (pattern, count)
driver.write_text(text)

bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
bootstrap_sha["System"] = image_sha(stage / "bootstrap/java/lang/System.class.hex")
root_commitment = json.loads((stage / "root-commitment.json").read_text())
pins = {
    "phase": "built", "basis": "1b178a6eb",
    "parentEvidence": "parent-1b178a6eb/artifacts/{engine,coordinator}/MCEntry*.sol",
    "domain": "MC-SYSTEM-SET-OUT-001", "bootstrapCount": 94,
    "bootstrapRoot": root_commitment["bootstrapRoot"], "bootstrapSHA256": bootstrap_sha,
    "globalNativeBindings": 16, "stringLocalBinding": 11, "exceptionKinds": 14,
    "maxFrames": 128, "rawLimits": [52, 329162], "diagnosticClassBound": 146,
    "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000,
    "runtimeCap": 393216,
    "address": "0x4d432d53595354454d2d5345542d4f55542d3031",
    "owner": "0x4d432d53595354454d2d5345542d4f55542d3032",
    "engine": engine, "coordinator": coordinator, "worker": "system-set-out",
}
if persisted.exists(): assert json.loads(persisted.read_text()) == pins
else: persisted.write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
run("source-verification-final", [sys.executable, here / "verify_source.py", "--built", out / "pins.json"])
main = out / "main.go"; shutil.copy2(driver, main)
for label, command in (("gofmt", ["gofmt", "-w", main]), ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]), ("go-vet", ["go", "vet", main])):
    run(label, command)
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coordinator}, indent=2))
