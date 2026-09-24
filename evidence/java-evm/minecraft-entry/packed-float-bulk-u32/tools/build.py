#!/usr/bin/env python3
"""Build P17 reference and packed-u32 candidate using only tracked generated fixtures."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
if len(sys.argv) != 2:
    raise SystemExit("usage: build.py BUILD-ID")
build_id = sys.argv[1]
assert build_id.startswith("01-")
build = root / "build" / ("java-diff-mc-packed-float-bulk-u32-build-" + build_id)
fixtures = root / "build" / ("java-diff-mc-packed-float-bulk-u32-fixtures-" + build_id)
assert not build.exists() and not fixtures.exists(), "build outputs are append-only"

p17 = root / "evidence/java-evm/minecraft-entry/parent-485ccd8d4"
pins_path = p17 / "artifacts/parent-build-pins.json"
pins = json.loads(pins_path.read_text())
base_engine_source = p17 / "artifacts/engine/MCEntryInterpreter.sol"
base_engine_build = p17 / "artifacts/engine/build.js"
base_coordinator_source = p17 / "artifacts/coordinator/MCEntryCoordinator.sol"
base_coordinator_build = p17 / "artifacts/coordinator/build.js"
base_driver_source = p17 / "canonical-driver.go.txt"
assert pins["bootstrapCount"] == 97 and pins["rawLimits"] == [71, 471911]
assert pins["engine"]["bytes"] == 392176 and pins["runtimeCap"] == 393216
assert pins["bootstrapRoot"] == "aae001d9449928180fe6daf66cc3a7bffa4686a7823f69bb994cd882fa89ec0d"

node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "only the local npm cache may supply compiler dependencies"
tmp = build / "tmp"
build.mkdir(parents=True)
tmp.mkdir()
env = {
    **os.environ,
    "TMPDIR": str(tmp),
    "NODE_PATH": str(node_modules),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}


def run(label, command, timeout=1200):
    with (build / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True,
                       timeout=timeout)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


run("source-verification", [sys.executable, here / "verify_source.py", build_id])


def engine_build(name, source):
    directory = build / name / "engine"
    directory.mkdir(parents=True)
    shutil.copy2(source, directory / "MCEntryInterpreter.sol")
    shutil.copy2(base_engine_build, directory / "build.js")
    run(name + "-engine-build", ["node", directory / "build.js"])
    artifact = json.loads((directory / "MCEntryInterpreter.json").read_text())
    runtime = bytes.fromhex(artifact["deployedBytecode"])
    result = {"bytes": len(runtime), **artifact["codeHashes"]}
    assert result["bytes"] <= 393216, result
    return directory, artifact, result


def coordinator_build(name, engine_hash):
    directory = build / name / "coordinator"
    directory.mkdir(parents=True)
    source = base_coordinator_source.read_text()
    p17_hash = pins["engine"]["runtimeKeccak256"]
    needle = 'hex"' + p17_hash + '"'
    assert source.count(needle) == 1
    source = source.replace(needle, 'hex"' + engine_hash + '"', 1)
    (directory / "MCEntryCoordinator.sol").write_text(source)
    shutil.copy2(base_coordinator_build, directory / "build.js")
    run(name + "-coordinator-build", ["node", directory / "build.js"])
    artifact = json.loads((directory / "MCEntryCoordinator.json").read_text())
    runtime = bytes.fromhex(artifact["deployedBytecode"])
    result = {"bytes": len(runtime), **artifact["codeHashes"]}
    return directory, artifact, result


def driver_build(name, engine, coordinator):
    text = base_driver_source.read_text()
    replacements = (
        (pins["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
        ("0x" + pins["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
        ("0x" + pins["coordinator"]["runtimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
        ("len(engineRun) != %d" % pins["engine"]["bytes"],
         "len(engineRun) != %d" % engine["bytes"]),
        ("len(run) != %d" % pins["engine"]["bytes"],
         "len(run) != %d" % engine["bytes"]),
        ("len(coordRun) != %d" % pins["coordinator"]["bytes"],
         "len(coordRun) != %d" % coordinator["bytes"]),
    )
    for old, new in replacements:
        assert text.count(old) == 1, (name, old, text.count(old))
        text = text.replace(old, new, 1)
    driver = build / (name + "-driver.go")
    driver.write_text(text)
    binary = build / (name + "-driver")
    run(name + "-driver-gofmt", ["gofmt", "-w", driver])
    run(name + "-driver-build", ["go", "build", "-trimpath", "-o", binary, driver])
    run(name + "-driver-vet", ["go", "vet", driver])
    return binary, sha256(driver.read_bytes())


# Rebuild the exact P17 reference and the candidate independently with pinned solc.
base_engine_dir, base_engine_artifact, base_engine = engine_build("p17", base_engine_source)
assert base_engine == pins["engine"], (base_engine, pins["engine"])
base_coord_dir, base_coord_artifact, base_coord = coordinator_build(
    "p17", base_engine["runtimeKeccak256"])
assert base_coord == pins["coordinator"], (base_coord, pins["coordinator"])
base_driver, base_driver_sha = driver_build("p17", base_engine, base_coord)

candidate_engine_dir, candidate_engine_artifact, candidate_engine = engine_build(
    "candidate", stage / "engine/MCEntryInterpreter.sol")
assert candidate_engine_artifact["abi"] == base_engine_artifact["abi"]
assert candidate_engine_artifact["storageLayout"] == base_engine_artifact["storageLayout"]
candidate_coord_dir, candidate_coord_artifact, candidate_coord = coordinator_build(
    "candidate", candidate_engine["runtimeKeccak256"])
expected_candidate_coordinator = base_coordinator_source.read_text().replace(
    'hex"' + pins["engine"]["runtimeKeccak256"] + '"',
    'hex"' + candidate_engine["runtimeKeccak256"] + '"', 1)
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_candidate_coordinator
assert candidate_coord_artifact["abi"] == base_coord_artifact["abi"]
assert (stage / "coordinator/build.js").read_bytes() == base_coordinator_build.read_bytes()
candidate_driver, candidate_driver_sha = driver_build(
    "candidate", candidate_engine, candidate_coord)
# Compatibility names used by the generated-only capacity-boundary probes.
shutil.copy2(candidate_driver, build / "driver")
shutil.copy2(build / "candidate-driver.go", build / "main.go")
shutil.copytree(candidate_engine_dir, build / "engine")
shutil.copytree(candidate_coord_dir, build / "coordinator")

# These are synthetic Java-8 fixture classes, never extracted from an external JAR.
fixture_source = root / "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures"
assert (fixture_source / "packed-array-oracle.zip").is_file()
shutil.copytree(fixture_source, fixtures)

# Patch only the two generated sipush(1024) operands (allocation and length check)
# to exercise exact 0/1/7-cell tails; all array contents otherwise remain the same.
base_meta = json.loads((fixtures / "packed-array-oracle.json").read_text())
raw_oracle_source = stage / "tools/RawFloatOracle.java"
assert raw_oracle_source.is_file(), "checked-in generated-fixture oracle is required"
oracle_classes = build / "float-oracle-classes"
oracle_classes.mkdir()
run("float-oracle-javac", ["javac", "--release", "8", "-d", oracle_classes, raw_oracle_source])

for length in (1024, 1025, 1031):
    label = "float-tail-%d" % length
    zip_path = fixtures / (label + ".zip")
    classes_dir = build / (label + "-classes")
    classes_dir.mkdir()
    source_zip = fixtures / "packed-array-oracle.zip"
    with zipfile.ZipFile(source_zip) as src, zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_STORED
    ) as dst:
        assert set(src.namelist()) == set(base_meta["entries"])
        for name in src.namelist():
            data = src.read(name)
            needle = b"\x11\x04\x00"  # JVM sipush 1024
            if length != 1024:
                assert data.count(needle) == 1, (name, data.count(needle))
                data = data.replace(needle, b"\x11" + length.to_bytes(2, "big"), 1)
            dst.writestr(name, data)
            (classes_dir / name).write_bytes(data)

    java_cp = str(classes_dir) + os.pathsep + str(oracle_classes)
    proc = subprocess.run(["java", "-cp", java_cp, "RawFloatOracle"], cwd=root,
                          env=env, text=True, capture_output=True, check=True,
                          timeout=60)
    values = [line.strip().lower() for line in proc.stdout.splitlines() if line.strip()]
    assert len(values) == length and all(len(value) == 8 for value in values), (length, len(values))
    assert values[:1024] == base_meta["hostOutput"], "tail rewrite changed generated Java8 values"
    assert all(value == "00000000" for value in values[1024:])
    with zipfile.ZipFile(zip_path) as z:
        entries = {name: z.read(name) for name in z.namelist()}
    class_bytes = {name: len(data) for name, data in entries.items()}
    metadata = {
        "entries": base_meta["entries"],
        "bindingCount": base_meta["bindingCount"],
        "bootstrapCount": base_meta["bootstrapCount"],
        "totalClassBytes": sum(class_bytes.values()),
        "classBytes": class_bytes,
        "classSHA256": {name: sha256(data) for name, data in entries.items()},
        "zipSHA256": sha256(zip_path.read_bytes()),
        "java8HostOracle": True,
        "tailLength": length,
        "hostOutput": values,
    }
    (fixtures / (label + ".json")).write_text(json.dumps(metadata, indent=2) + "\n")

source_audit_path = stage / "results" / ("source-audit-" + build_id + ".json")
source_audit = json.loads(source_audit_path.read_text())
root_audit = source_audit
assert root_audit["candidateRoot"] == pins["bootstrapRoot"]
assert root_audit["candidateRoot"] == root_audit["p17Root"]

math_keccak = pins["math"]["keccak256"]
build_pins = {
    "profile": "MC-RANDOM-CLASS-P17-PACKED-FLOAT-BULK-U32",
    "basis": "parent-485ccd8d4 P17 source; only packed float MR01 cell loops changed",
    "bootstrapCount": 97,
    "bootstrapRoot": pins["bootstrapRoot"],
    "expectedBootstrapRoot": pins["sourceInvariants"]["actualP16BootstrapRoot"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "globalNativeBindings": pins["globalNativeBindings"],
    "stringLocalBinding": pins["stringLocalBinding"],
    "rawLimits": pins["rawLimits"],
    "checkpointCap": pins["checkpointCap"],
    "reserve": pins["reserve"],
    "externalLocalGas": pins["externalLocalGas"],
    "runtimeCap": pins["runtimeCap"],
    "maxFrames": pins["maxFrames"],
    "exceptionKinds": pins["exceptionKinds"],
    "address": pins["address"],
    "owner": pins["owner"],
    "engine": candidate_engine,
    "coordinator": candidate_coord,
    "baselineEngine": base_engine,
    "baselineCoordinator": base_coord,
    "baselineDriverSHA256": base_driver_sha,
    "driverSHA256": candidate_driver_sha,
    "sourceInvariants": {
        "actualP16BootstrapRoot": pins["sourceInvariants"]["actualP16BootstrapRoot"],
        "actualIndependentParentP17Root": root_audit["candidateRoot"],
        "orderedLeaves": 97,
    },
    "integer": pins["integer"],
    "object": pins["object"],
    "math": {"keccak256": math_keccak},
    "expectedMathKeccak256": math_keccak,
    "string": pins["string"],
    "system": pins["system"],
    "locale": pins["locale"],
    "random": pins["random"],
    "sparseWire": pins["sparseWire"],
    "packedFloatWire": pins["packedFloatWire"],
    "buildID": build_id,
    "generatedFixtureSource": str(fixture_source.relative_to(root)),
}
(build / "pins.json").write_text(json.dumps(build_pins, indent=2) + "\n")
(build / "build-result.json").write_text(json.dumps({
    "result": "PASS",
    "generatedOnly": True,
    "candidateEngine": candidate_engine,
    "baselineEngine": base_engine,
    "candidateCoordinator": candidate_coord,
    "baselineCoordinator": base_coord,
    "bootstrapRoot": root_audit["candidateRoot"],
    "orderedBootstrapLeaves": 97,
    "engineABIUnchanged": True,
    "engineStorageLayoutUnchanged": True,
    "coordinatorABIUnchanged": True,
    "candidateDriverSHA256": candidate_driver_sha,
    "baselineDriverSHA256": base_driver_sha,
    "fixtures": str(fixtures.relative_to(root)),
    "floatTailLengths": [1024, 1025, 1031],
}, indent=2) + "\n")
print(json.dumps({
    "build": str(build), "fixtures": str(fixtures),
    "candidateEngine": candidate_engine, "baselineEngine": base_engine,
    "candidateCoordinator": candidate_coord, "baselineCoordinator": base_coord,
    "bootstrapRoot": root_audit["candidateRoot"], "runtimeCap": pins["runtimeCap"],
}, indent=2))
