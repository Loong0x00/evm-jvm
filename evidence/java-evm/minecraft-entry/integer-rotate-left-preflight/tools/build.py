#!/usr/bin/env python3
"""Build the isolated P15 source with cached dependencies only."""
from pathlib import Path
import json
import hashlib
import os
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-integer-rotate-left-build-") and not out.exists()
pins = json.loads((stage / "build-pins.json").read_text())
NPM_PINS = {"packageJSONSHA256": "1befdd3ffec8f47c79d52e344a976b20d2187a8f69cd5f747a9ca3408c208d43",
            "packageLockSHA256": "93e057f7e9ac9f1c6bf43cb1aae4d7e62309b24dd51dfe0e07973264a2cf78be"}
assert pins["domain"] == "MC-RANDOM-CLASS-P15" and pins["runtimeCap"] == 393216
out.mkdir(); (out / "tmp").mkdir()

# Rebuild the pinned runtime toolchain into this disposable output using the
# local npm cache only. No package registry/network access is attempted.
npm = out / "npm"
npm.mkdir()
for name, key in (("package.json", "packageJSONSHA256"),
                  ("package-lock.json", "packageLockSHA256")):
    shutil.copy2(root / "jvmevm/runtime" / name, npm / name)
    assert hashlib.sha256((npm / name).read_bytes()).hexdigest() == NPM_PINS[key]
env = {**os.environ, "TMPDIR": str(out / "tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
subprocess.run(["npm", "ci", "--offline", "--no-audit", "--no-fund", "--prefix", npm],
               cwd=root, env=env, check=True, stdout=(out / "npm-install.log").open("w"),
               stderr=subprocess.STDOUT)
env["NODE_PATH"] = str(npm / "node_modules")


def run(label, command):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)

run("source-verification", [sys.executable, here / "verify_source.py", "--check"])
for name, contract in (("engine", "MCEntryInterpreter"), ("coordinator", "MCEntryCoordinator")):
    target = out / name
    shutil.copytree(stage / name, target)
    run(name + "-build", ["node", target / "build.js"])
    artifact = json.loads((target / (contract + ".json")).read_text())
    actual = {"bytes": len(artifact["deployedBytecode"]) // 2, **artifact["codeHashes"]}
    assert actual == pins[name], (name, actual, pins[name])
    if name == "engine":
        assert actual["bytes"] <= pins["runtimeCap"]

main = out / "main.go"
shutil.copy2(stage / "tools/Go.txt", main)
for label, command in (("gofmt", ["gofmt", "-w", main]),
                       ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", main]),
                       ("go-vet", ["go", "vet", main])):
    run(label, command)
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
print(json.dumps({"build": str(out), "profile": pins["domain"], "engine": pins["engine"],
                  "coordinator": pins["coordinator"], "runtimeCap": pins["runtimeCap"]}, indent=2))
