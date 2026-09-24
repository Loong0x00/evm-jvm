#!/usr/bin/env python3
"""Reproducibly compile the P10 Math.cos candidate and generated driver."""
from pathlib import Path
import json, os, re, shutil, subprocess, sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 3, "build.py BUILD_DIR FIXTURES_DIR"
out, fixtures = (Path(x).resolve() for x in sys.argv[1:])
assert out.parent == fixtures.parent == root / "build"
assert out.name.startswith("java-diff-mc-math-cos-build-") and not out.exists()
assert fixtures.name.startswith("java-diff-mc-math-cos-fixtures-") and fixtures.is_dir()
base = json.loads((stage / "baseline-pins.json").read_text())
source_report = json.loads((stage / "results/source-invariants.json").read_text())
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir()
out.mkdir(); (out / "tmp").mkdir()
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node),
       "PYTHONDONTWRITEBYTECODE": "1"}

def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)

run("source-invariants", [sys.executable, here / "verify_source.py"])
source_report = json.loads((stage / "results/source-invariants.json").read_text())
q120 = subprocess.run([sys.executable, here / "verify_q120.py", fixtures], cwd=root,
                      text=True, capture_output=True, check=True, timeout=180)
q120_report = json.loads(q120.stdout)
assert q120_report["supportedRows"] == 17066
assert q120_report["maxBinary64ULPDistanceFromJava8"] <= 1
assert q120_report["floatCastBitMismatchCount"] == 0 and q120_report["refusedControls"] == 11
cos = q120_report["cosQ120TestOnlyModel"]
assert cos["vectorCount"] >= 150 and cos["maxBinary64ULPDistanceFromJava8"] <= 1
assert cos["floatCastRawMismatchCount"] == 0

engine_dir = out / "engine"; shutil.copytree(stage / "engine", engine_dir)
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_code = bytes.fromhex(engine_artifact["deployedBytecode"])
engine = {"bytes": len(engine_code), **engine_artifact["codeHashes"]}
assert engine["bytes"] <= 393216
coord_dir = out / "coordinator"; shutil.copytree(stage / "coordinator", coord_dir)
coord_source = coord_dir / "MCEntryCoordinator.sol"
text = coord_source.read_text()
old_engine = base["engine"]["runtimeKeccak256"]
assert text.count(old_engine) == 1
coord_source.write_text(text.replace(old_engine, engine["runtimeKeccak256"]))
run("coordinator-build", ["node", coord_dir / "build.js"])
coord_artifact = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord = {"bytes": len(bytes.fromhex(coord_artifact["deployedBytecode"])),
         **coord_artifact["codeHashes"]}
assert coord["bytes"] == base["coordinator"]["bytes"]

main = (stage / "tools/Go.txt").read_text()
for old, new in ((base["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
                 ("0x" + base["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
                 ("0x" + base["coordinator"]["runtimeKeccak256"], "0x" + coord["runtimeKeccak256"])):
    assert main.count(old) == 1, (old, main.count(old))
    main = main.replace(old, new)
for pattern in (r"len\(engineRun\) != 388632", r"len\(run\) != 388632"):
    main, count = re.subn(pattern, lambda m: m.group(0).replace("388632", str(engine["bytes"])), main)
    assert count == 1, (pattern, count)
main_path = out / "main.go"; main_path.write_text(main)
for label, command in (("gofmt", ["gofmt", "-w", main_path]),
                       ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main_path]),
                       ("go-vet", ["go", "vet", main_path])):
    run(label, command)

pins = dict(base)
pins.update({
    "phase": "generated-only P10 Math.cos bounded Q120 profile",
    "bootstrapRoot": source_report["bootstrapRoot"],
    "globalNativeBindings": 21,
    "bootstrapSHA256": dict(base.get("bootstrapSHA256", {}), Math=source_report["mathImageSHA256"]),
    "engine": engine,
    "coordinator": coord,
    "math": {"slot": 89, "bytes": source_report["mathImageBytes"],
             "sha256": source_report["mathImageSHA256"],
             "keccak256": source_report["mathImageKeccak256"],
             "surface": "accepted Math P10 surface plus exact native cos(D)D binding21; sqrt18/sin19/asin20 retained",
             "java8": "javac -source 8 -target 8 -g:none"},
    "sourceInvariants": source_report,
    "q120TestOnlyModel": q120_report,
    "cosQ120TestOnlyModel": cos,
    "runtimeCap": 393216,
    "rawLimits": [71, 471911],
    "stringLocalBinding": 12,
    "diagnosticClassBound": 168,
    "sparseWire": {"flag": "0x80000000", "minimumLength": 1024,
                   "savingRule": "(4+12*nonzero)*4 <= (8*length)*3"},
})
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "engine": engine, "coordinator": coord,
                  "bootstrapRoot": pins["bootstrapRoot"], "math": pins["math"],
                  "globalNativeBindings": 21, "runtimeCap": 393216,
                  "cosVectors": cos["vectorCount"],
                  "cosMaxULP": cos["maxBinary64ULPDistanceFromJava8"]}, indent=2))
