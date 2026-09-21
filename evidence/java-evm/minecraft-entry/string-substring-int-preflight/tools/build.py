#!/usr/bin/env python3
"""Rebuild the isolated generated-only String.substring(int) stage."""
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
assert out.name.startswith("java-diff-mc-string-substring-int-build-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
out.mkdir(); (out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")

def run(label, command):
    with (out / (label + ".log")).open("w") as log:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

def pin(directory, contract):
    artifact = json.loads((directory / (contract + ".json")).read_text())
    return {"bytes": len(artifact["deployedBytecode"]) // 2, **artifact["codeHashes"]}

run("source-verification-prebuild", [sys.executable, here / "verify_source.py", out / "source-verify"])
engine_dir = out / "engine"; shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = pin(engine_dir, "MCEntryInterpreter")
assert engine["bytes"] <= 393216

# Build a derived coordinator pin without mutating durable staged source.
coord_dir = out / "coordinator"; shutil.copytree(stage / "coordinator", coord_dir)
coord_source = coord_dir / "MCEntryCoordinator.sol"
text = coord_source.read_text()
match = re.search(r"(bytes32 private constant ENGINE_CODEHASH = hex\")[0-9a-f]{64}(\";)", text)
assert match
text = text[:match.start(1)] + match.group(1) + engine["runtimeKeccak256"] + match.group(2) + text[match.end(2):]
coord_source.write_text(text)
run("coordinator-build", ["node", coord_dir / "build.js"])
coordinator = pin(coord_dir, "MCEntryCoordinator")
assert coordinator["bytes"] == 5394

# The raw-ABI driver only packs raw generated class bytes for EVM calls.
driver_source = stage / "tools/Go.txt"
text = driver_source.read_text()
def replace_const(name, value):
    global text
    pattern = r'(const ' + name + r' = ")[^"]+("\n)'
    text, n = re.subn(pattern, r'\g<1>' + value + r'\g<2>', text)
    assert n == 1, name
replace_const("immutableEngineSHA256", engine["runtimeSHA256"])
replace_const("immutableEngineKeccak", "0x" + engine["runtimeKeccak256"])
replace_const("immutableCoordinatorKeccak", "0x" + coordinator["runtimeKeccak256"])
for name, value in (("engineRun", engine["bytes"]), ("coordRun", coordinator["bytes"]), ("run", engine["bytes"])):
    pattern = r'(len\(' + name + r'\) != )\d+'
    text, n = re.subn(pattern, r'\g<1>' + str(value), text)
    assert n == 1, name
main = out / "main.go"; main.write_text(text)
run("gofmt", ["gofmt", "-w", main]); run("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]); run("go-vet", ["go", "vet", main])

root_record = json.loads((stage / "root-commitment.json").read_text())
pins = {
    "phase": "built", "basis": "parent-8ac912dd6", "parentEvidence": "parent-8ac912dd6/artifacts/engine/MCEntryInterpreter.sol",
    "domain": "MC-SUBSTRING-INT-00001", "bootstrapCount": 94,
    "bootstrapRoot": root_record["bootstrapRoot"], "bootstrapSHA256": {"String": root_record["changedLeaves"]["String"]["sha256"]},
    "globalNativeBindings": 14, "stringLocalBinding": 11, "exceptionKinds": 14,
    "maxFrames": 128, "rawLimits": [50, 324338], "diagnosticClassBound": 144,
    "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000,
    "runtimeCap": 393216, "address": "0x4d432d535542535452494e472d494e542d303031",
    "owner": "0x4d432d535542535452494e472d494e542d303032", "engine": engine, "coordinator": coordinator,
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coordinator}, indent=2))
