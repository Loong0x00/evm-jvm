#!/usr/bin/env python3
"""Single reproducible LOCAL384 cap30 source build; generated fixtures only."""
from pathlib import Path
import json, os, shutil, subprocess, sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-classcount30-")
assert not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
if not node_modules.is_dir():
    raise RuntimeError("pinned local solc is unavailable; install it offline in this worktree")
out.mkdir()
(out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")

parent_engine_keccak = "193fb2fa9fad5417924977b956f06a11c52952c797892c1e2a074c3aa3850c00"
parent_engine_sha = "8bdc4b6d2159009fcab50faa861d56bff01eafe25cf9551383f6046ff5d14ae0"
parent_coordinator_keccak = "d036eb145986d342d0cc30130ddbffc2e83cf4474aae05fde1ccfa513d8be5e8"
expected_engine_bytes = 393205
expected_coordinator_bytes = 4146

def run(label, command):
    with (out / (label + ".log")).open("w") as log:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

def artifact(directory, name):
    return json.loads((directory / (name + ".json")).read_text())

# The parent engine has no mutable code hash input: one engine compilation is enough
# to derive the only changed coordinator/driver pins.
engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine = artifact(engine_dir, "MCEntryInterpreter")
engine_pin = {"bytes": len(engine["deployedBytecode"]) // 2, **engine["codeHashes"]}
assert engine_pin["bytes"] == expected_engine_bytes

coordinator_source = stage / "coordinator/MCEntryCoordinator.sol"
text = coordinator_source.read_text()
if parent_engine_keccak in text:
    assert text.count(parent_engine_keccak) == 1
    text = text.replace(parent_engine_keccak, engine_pin["runtimeKeccak256"])
    coordinator_source.write_text(text)
else:
    assert text.count(engine_pin["runtimeKeccak256"]) == 1

coordinator_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coordinator_dir)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator = artifact(coordinator_dir, "MCEntryCoordinator")
coordinator_pin = {"bytes": len(coordinator["deployedBytecode"]) // 2, **coordinator["codeHashes"]}
assert coordinator_pin["bytes"] == expected_coordinator_bytes

driver_source = stage / "tools/Go.txt"
text = driver_source.read_text()
replacements = (
    (parent_engine_sha, engine_pin["runtimeSHA256"]),
    ("0x" + parent_engine_keccak, "0x" + engine_pin["runtimeKeccak256"]),
    ("0x" + parent_coordinator_keccak, "0x" + coordinator_pin["runtimeKeccak256"]),
)
for old, new in replacements:
    if old in text:
        assert text.count(old) == 1
        text = text.replace(old, new)
    else:
        assert text.count(new) == 1

driver_source.write_text(text)

pins = {
    "basis": "3ed302a92",
    "parentEvidence": "parent-3ed302a92",
    "phase": "built",
    "domain": "MC-CLASSCOUNT30-C30",
    "runtimeCap": 393216,
    "bootstrapCount": 83,
    "bootstrapSHA256": {"EnumSet": "ab36a2f498e571717f53554bb485b5d84a38616fc376f1af7a0f5a66846ff230"},
    "bootstrapKeccak256": "00e07d84942a8e3eaec0abf3226c2c4f1ac68e70fed62aafc4393cd2fa5414e9",
    "globalNativeBindings": 12,
    "stringLocalBinding": 10,
    "exceptionKinds": 14,
    "maxFrames": 128,
    "externalLocalGas": 1000000000,
    "reserve": 25000000,
    "rawLimits": [30, 262144],
    "checkpointCap": 1048576,
    "headCap": 32768,
    "engine": engine_pin,
    "coordinator": coordinator_pin,
    "parentAmendment": "reject initializationState==3 as guest NoClassDefFoundError; cap30 diagnostic bound113",
    "diagnosticClassBound": 113,
    "address": "0x4d432d434c415353434f554e5433302d43333001",
    "owner": "0x4d432d434c415353434f554e5433302d4f333002",
}
(stage / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")

main = out / "main.go"
shutil.copy2(driver_source, main)
for label, command in (("gofmt", ["gofmt", "-w", main]), ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]), ("go-vet", ["go", "vet", main])):
    run(label, command)
print(json.dumps({"build": str(out), "engine": engine_pin, "coordinator": coordinator_pin}, indent=2))
