#!/usr/bin/env python3
"""Build a disposable, fresh P9 artifact from the frozen candidate source."""
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-math-asin-p9-build-") and not out.exists()
baseline = json.loads((stage / "baseline-pins.json").read_text())
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir()
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node), "PYTHONDONTWRITEBYTECODE": "1"}


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


run("rebase-source", [sys.executable, here / "rebase_source.py"])
run("source-invariants", [sys.executable, here / "verify_source.py"])
source_report = json.loads((stage / "results/source-invariants.json").read_text())
assert source_report["normalizedByteExactToP6"] and source_report["actualSolidityP9BootstrapRoot"]
q120 = subprocess.run([sys.executable, here / "verify_q120.py"], cwd=root, text=True,
                      capture_output=True, check=True, timeout=120)
q120_report = json.loads(q120.stdout)
assert q120_report["supportedRows"] == 17066
assert q120_report["maxBinary64ULPDistanceFromJava8"] == 1
assert q120_report["floatCastBitMismatchCount"] == 0

engine_dir = out / "engine"
shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_code = bytes.fromhex(engine_artifact["deployedBytecode"])
engine = {"bytes": len(engine_code), **engine_artifact["codeHashes"]}
assert engine["bytes"] <= 393216, engine

coord_dir = out / "coordinator"
shutil.copytree(stage / "coordinator", coord_dir)
coord_source = coord_dir / "MCEntryCoordinator.sol"
coord_text = coord_source.read_text()
p6_engine_hash = baseline["engine"]["runtimeKeccak256"]
assert coord_text.count(p6_engine_hash) == 1
coord_source.write_text(coord_text.replace(p6_engine_hash, engine["runtimeKeccak256"]))
run("coordinator-build", ["node", coord_dir / "build.js"])
coord_artifact = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord = {"bytes": len(bytes.fromhex(coord_artifact["deployedBytecode"])),
         **coord_artifact["codeHashes"]}
assert coord["bytes"] == baseline["coordinator"]["bytes"]

main = (stage / "tools/Go.txt").read_text()
old_constants = (
    (baseline["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
    ("0x" + baseline["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
    ("0x" + baseline["coordinator"]["runtimeKeccak256"], "0x" + coord["runtimeKeccak256"]),
)
for old, new in old_constants:
    assert main.count(old) == 1, (old, main.count(old))
    main = main.replace(old, new, 1)
for pattern in (r"len\(engineRun\) != 388691", r"len\(run\) != 388691"):
    main, count = re.subn(pattern, lambda m: m.group(0).replace("388691", str(engine["bytes"])), main)
    assert count == 1, (pattern, count)
main_path = out / "main.go"
main_path.write_text(main)
for label, cmd in (("gofmt", ["gofmt", "-w", main_path]),
                   ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main_path]),
                   ("go-vet", ["go", "vet", main_path])):
    run(label, cmd)

pins = dict(baseline)
pins.update({
    "address": "0x4d432d52414e444f4d2d434c4153532d5039000e",
    "owner": "0x4d432d52414e444f4d2d434c4153532d5039000f",
    "phase": "generated-only P9 Math.asin + accepted P6 packed-float candidate",
    "domain": "MC-RANDOM-CLASS-P9",
    "freshDomain": True,
    "baselineCommit": "parent-670d5a8ce (accepted P6 packed-float source)",
    "baselineEngineSourceSHA256": source_report["baselineEngineSourceSHA256"],
    "candidateEngineSourceSHA256": source_report["candidateEngineSourceSHA256"],
    "bootstrapRoot": source_report["actualSolidityP9BootstrapRoot"],
    "globalNativeBindings": 20,
    "packedFloatWire": {"flag": "0x40000000", "sparseFlag": "0x80000000",
                        "minimumLength": 1024, "cellWidthBytes": 4,
                        "strictSelection": "4*length < 4+12*nonzero",
                        "guestRepresentation": "eager dense uint64[]"},
    "bootstrapSHA256": dict(baseline["bootstrapSHA256"]),
    "engine": engine,
    "coordinator": coord,
    "math": {"slot": 89, "bytes": source_report["mathImageBytes"],
             "sha256": source_report["mathImageSHA256"],
             "keccak256": source_report["mathImageKeccak256"],
             "surface": "P6 Math API plus exact bounded Q120 integer asin(D)D binding20"},
    "sourceInvariants": source_report,
    "q120TestOnlyModel": q120_report,
    "runtimeCap": 393216,
})
pins["bootstrapSHA256"]["Math"] = source_report["mathImageSHA256"]
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "domain": pins["domain"], "engine": engine,
                  "coordinator": coord, "bootstrapRoot": pins["bootstrapRoot"],
                  "math": pins["math"], "globalNativeBindings": 20,
                  "runtimeCap": 393216, "oracle": {"supportedRows": q120_report["supportedRows"],
                  "maxULP": q120_report["maxBinary64ULPDistanceFromJava8"]}}, indent=2))
