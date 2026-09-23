#!/usr/bin/env python3
"""Offline candidate build with fixed P5 coordinator and MR0 driver pins."""
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-float-packed-build-") and not out.exists()
base = json.loads((stage / "baseline-pins.json").read_text())
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "offline pinned node_modules required"
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node), "PYTHONDONTWRITEBYTECODE": "1"}


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)

run("source-invariants", [sys.executable, here / "verify_source.py"])
source_report = json.loads((stage / "results/source-invariants.json").read_text())
engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_run = bytes.fromhex(engine_artifact["deployedBytecode"])
engine = {"bytes": len(engine_run), **engine_artifact["codeHashes"]}
assert engine["bytes"] <= base["runtimeCap"] == 393216

coord_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coord_dir)
coord_source = coord_dir / "MCEntryCoordinator.sol"
text = coord_source.read_text()
old_hash = base["engine"]["runtimeKeccak256"]
assert text.count(old_hash) == 1
text = text.replace(old_hash, engine["runtimeKeccak256"])
coord_source.write_text(text)
run("coordinator-build", ["node", coord_dir / "build.js"])
coord_artifact = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord = {"bytes": len(bytes.fromhex(coord_artifact["deployedBytecode"])),
         **coord_artifact["codeHashes"]}
assert coord["bytes"] == base["coordinator"]["bytes"]

main = (here / "Go.txt").read_text()
for old, new in (
    (base["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
    ("0x" + base["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
    ("0x" + base["coordinator"]["runtimeKeccak256"], "0x" + coord["runtimeKeccak256"]),
):
    assert main.count(old) == 1, (old, main.count(old))
    main = main.replace(old, new)
for variable in ("engineRun", "run"):
    pattern = r"len\(" + variable + r"\) != " + str(base["engine"]["bytes"])
    main, n = re.subn(pattern, "len(%s) != %d" % (variable, engine["bytes"]), main)
    assert n == 1, (variable, n)
main_path = out / "main.go"
main_path.write_text(main)
for label, command in (("gofmt", ["gofmt", "-w", main_path]),
                       ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main_path]),
                       ("go-vet", ["go", "vet", main_path])):
    run(label, command)

pins = dict(base)
pins.update({
    "phase": "built-float-packed-checkpoint-candidate",
    "basis": "56f2377a5", "worker": "parent", "domain": "MC-RANDOM-CLASS-P5",
    "bootstrapRoot": source_report["actualP5BootstrapRoot"],
    "engine": engine, "coordinator": coord,
    "sourceInvariants": source_report,
    "packedFloatWire": {
        "flag": "0x40000000", "sparseFlag": "0x80000000",
        "minimumLength": 1024, "cellWidthBytes": 4,
        "strictSelection": "4*length < 4+12*nonzero",
        "guestRepresentation": "eager dense uint64[]",
    },
})
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coord,
                  "bootstrapRoot": pins["bootstrapRoot"],
                  "runtimeCap": pins["runtimeCap"],
                  "externalLocalGas": pins["externalLocalGas"]}, indent=2))
