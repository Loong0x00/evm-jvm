#!/usr/bin/env python3
"""Offline reproducible P16 baseline/candidate build and generated-only driver build."""
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
out = Path(sys.argv[1]).resolve()
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-packed-float-single-scan-build-")
assert not out.exists(), "build outputs are append-only"
p16dir = root / "evidence/java-evm/minecraft-entry/parent-50541377b"
p16pins = json.loads((p16dir / "artifacts/parent-build-pins.json").read_text())
p16coord = p16dir / "artifacts/coordinator/MCEntryCoordinator.sol"
p16engine = p16dir / "artifacts/engine/MCEntryInterpreter.sol"
p5stage = root / "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation"
p5pins = json.loads((p5stage / "baseline-pins.json").read_text())
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "only the local cached solc/js-sha3 dependencies are permitted"
out.mkdir()
(out / "tmp").mkdir()
env = {
    **os.environ,
    "TMPDIR": str(out / "tmp"),
    "NODE_PATH": str(node_modules),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}


def run(label, command, cwd=root):
    with (out / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def build_engine(name, source):
    directory = out / name / "engine"
    directory.mkdir(parents=True)
    shutil.copy2(source, directory / "MCEntryInterpreter.sol")
    shutil.copy2(stage / "engine/build.js", directory / "build.js")
    run(name + "-engine-build", ["node", directory / "build.js"])
    artifact = json.loads((directory / "MCEntryInterpreter.json").read_text())
    runtime = bytes.fromhex(artifact["deployedBytecode"])
    result = {"bytes": len(runtime), **artifact["codeHashes"]}
    assert result["bytes"] <= 393216
    return directory, artifact, result


def build_coordinator(name, engine_hash):
    directory = out / name / "coordinator"
    directory.mkdir(parents=True)
    text = p16coord.read_text()
    old = "hex\"" + p16pins["engine"]["runtimeKeccak256"] + "\""
    assert text.count(old) == 1
    text = text.replace(old, "hex\"" + engine_hash + "\"", 1)
    (directory / "MCEntryCoordinator.sol").write_text(text)
    shutil.copy2(p16dir / "artifacts/coordinator/build.js", directory / "build.js")
    run(name + "-coordinator-build", ["node", directory / "build.js"])
    artifact = json.loads((directory / "MCEntryCoordinator.json").read_text())
    runtime = bytes.fromhex(artifact["deployedBytecode"])
    return directory, artifact, {"bytes": len(runtime), **artifact["codeHashes"]}


def build_driver(name, engine, coordinator):
    text = (p5stage / "tools/Go.txt").read_text()
    text = text.replace("MC-RANDOM-CLASS-P5", "MC-RANDOM-CLASS-P16")
    replacements = [
        (p5pins["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
        ("0x" + p5pins["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
        ("0x" + p5pins["coordinator"]["runtimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
        (p5pins["address"], p16pins["address"]),
        (p5pins["owner"], p16pins["owner"]),
        ("len(engineRun) != " + str(p5pins["engine"]["bytes"]),
         "len(engineRun) != " + str(engine["bytes"])),
        ("len(run) != " + str(p5pins["engine"]["bytes"]),
         "len(run) != " + str(engine["bytes"])),
        ("len(coordRun) != " + str(p5pins["coordinator"]["bytes"]),
         "len(coordRun) != " + str(coordinator["bytes"])),
    ]
    for old, new in replacements:
        assert old in text, (name, old)
        text = text.replace(old, new, 1)
    assert "MC-RANDOM-CLASS-P5" not in text
    driver = out / (name + "-driver.go")
    driver.write_text(text)
    binary = out / (name + "-driver")
    run(name + "-driver-gofmt", ["gofmt", "-w", driver])
    run(name + "-driver-build", ["go", "build", "-trimpath", "-o", binary, driver])
    run(name + "-driver-vet", ["go", "vet", driver])
    return binary, hashlib.sha256(driver.read_bytes()).hexdigest()


run("source-verification", [sys.executable, here / "verify_source.py"])
source_report = json.loads((stage / "source-invariants.json").read_text())
assert source_report["actualP16BootstrapRoot"] == p16pins["bootstrapRoot"]

base_engine_dir, base_engine_artifact, base_engine = build_engine("baseline", p16engine)
assert base_engine["bytes"] == p16pins["engine"]["bytes"]
assert base_engine["runtimeSHA256"] == p16pins["engine"]["runtimeSHA256"]
assert base_engine["runtimeKeccak256"] == p16pins["engine"]["runtimeKeccak256"]
base_coord_dir, base_coord_artifact, base_coord = build_coordinator(
    "baseline", base_engine["runtimeKeccak256"]
)
assert base_coord["bytes"] == p16pins["coordinator"]["bytes"]
assert base_coord["runtimeSHA256"] == p16pins["coordinator"]["runtimeSHA256"]
assert base_coord["runtimeKeccak256"] == p16pins["coordinator"]["runtimeKeccak256"]
base_driver, base_driver_sha = build_driver("baseline", base_engine, base_coord)

candidate_engine_dir, candidate_engine_artifact, candidate_engine = build_engine(
    "candidate", stage / "engine/MCEntryInterpreter.sol"
)
candidate_coord_dir, candidate_coord_artifact, candidate_coord = build_coordinator(
    "candidate", candidate_engine["runtimeKeccak256"]
)
candidate_driver, candidate_driver_sha = build_driver(
    "candidate", candidate_engine, candidate_coord
)
assert candidate_engine["bytes"] <= 393216
# Compatibility inputs used only by the generated raw-72 boundary probes.
shutil.copy2(out / "candidate-driver.go", out / "main.go")
shutil.copytree(candidate_coord_dir, out / "coordinator")

# Run fixtures are already archived, generated Java-8 inputs. Copy only those
# generated ZIPs and metadata needed by the gate; no official inputs are used.
fixture_archive = p5stage / "results/generated-gate-v5/fixtures"
fixture_dir = out.parent / ("java-diff-mc-packed-float-single-scan-fixtures-" + out.name.rsplit("-", 1)[-1])
assert not fixture_dir.exists()
shutil.copytree(fixture_archive, fixture_dir)

# P16 retained wrapper class leaf hashes: unchanged image metadata comes from
# the local generated-only P5 fixture pin; changed Integer is from accepted P16.
oldpins = p5pins
math_match = re.search(
    r"bytes32 private constant DBOOT_MATH = hex\"([0-9a-f]{64})\";",
    candidate_engine_dir.joinpath("MCEntryInterpreter.sol").read_text(),
)
assert math_match
math_keccak = math_match.group(1)
pins = {
    "profile": "MC-RANDOM-CLASS-P16-PACKED-FLOAT-SINGLE-SCAN",
    "basis": "accepted P16 parent-50541377b",
    "bootstrapCount": 97,
    "bootstrapRoot": p16pins["bootstrapRoot"],
    "expectedBootstrapRoot": p16pins["bootstrapRoot"],
    "diagnosticClassBound": p16pins["diagnosticClassBound"],
    "globalNativeBindings": p16pins["globalNativeBindings"],
    "stringLocalBinding": p16pins["stringLocalBinding"],
    "rawLimits": p16pins["rawLimits"],
    "checkpointCap": p16pins["checkpointCap"],
    "reserve": p16pins["reserve"],
    "externalLocalGas": p16pins["ordinaryGas"],
    "runtimeCap": p16pins["runtimeCap"],
    "maxFrames": p16pins["maxFrames"],
    "exceptionKinds": p16pins["exceptionKinds"],
    "address": p16pins["address"],
    "owner": p16pins["owner"],
    "engine": candidate_engine,
    "coordinator": candidate_coord,
    "baselineEngine": base_engine,
    "baselineCoordinator": base_coord,
    "baselineDriverSHA256": base_driver_sha,
    "driverSHA256": candidate_driver_sha,
    "sourceInvariants": source_report,
    "integer": p16pins["integer"],
    "object": p16pins["object"],
    "math": {"keccak256": math_keccak},
    "expectedMathKeccak256": math_keccak,
    "string": {"sha256": oldpins["string"]["sha256"]},
    "system": {"sha256": oldpins["system"]["sha256"]},
    "locale": {"sha256": oldpins["locale"]["sha256"]},
    "random": {"sha256": oldpins["random"]["sha256"]},
    "sparseWire": oldpins["sparseWire"],
    "packedFloatWire": {
        "flag": "0x40000000", "sparseFlag": "0x80000000",
        "minimumLength": 1024, "cellWidthBytes": 4,
        "strictSelection": "4*length < 4+12*nonzero",
        "guestRepresentation": "eager dense uint64[]",
    },
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(out / "build-result.json").write_text(json.dumps({
    "result": "PASS",
    "generatedOnlyFixtures": str(fixture_dir.relative_to(root)),
    "candidateEngine": candidate_engine,
    "candidateCoordinator": candidate_coord,
    "baselineEngine": base_engine,
    "baselineCoordinator": base_coord,
    "bootstrapRoot": p16pins["bootstrapRoot"],
    "driverSourceSHA256": candidate_driver_sha,
}, indent=2) + "\n")
print(json.dumps({
    "build": str(out),
    "fixtures": str(fixture_dir),
    "candidateEngine": candidate_engine,
    "candidateCoordinator": candidate_coord,
    "baselineEngine": base_engine,
    "baselineCoordinator": base_coord,
    "bootstrapRoot": p16pins["bootstrapRoot"],
    "runtimeCap": p16pins["runtimeCap"],
}, indent=2))
