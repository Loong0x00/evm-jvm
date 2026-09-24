#!/usr/bin/env python3
"""Verify the durable generated-only P16 single-scan evidence bundle."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import zipfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
results = stage / "results"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def check_sums(manifest):
    expected = {}
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        assert relative not in expected
        expected[relative] = digest
    base = manifest.parent
    actual = {path.relative_to(base).as_posix(): file_sha(path)
              for path in base.rglob("*") if path.is_file() and path != manifest}
    assert actual == expected, (len(actual), len(expected), manifest)


def read_json(path):
    return json.loads(path.read_text())


# Re-run the source-only comparison and bootstrap-root reconstruction.
subprocess.run(["python3", here / "verify_source.py"], cwd=root, check=True,
               stdout=subprocess.DEVNULL)
source_proof = read_json(stage / "source-invariants.json")
assert source_proof["result"] == "PASS"
assert source_proof["onlyChangedFunctions"] == ["_machineSize", "_encodeMachine"]
assert source_proof["bootstrapCount"] == 97
assert source_proof["actualP16BootstrapRoot"] == "8c5bc495513b12e7ee40f71f447c5f8f894d49ec9cf318d2744143f1d20ff310"

pins = read_json(results / "build-pins.json")
engine_json = read_json(stage / "engine/MCEntryInterpreter.json")
engine_runtime = bytes.fromhex((stage / "engine/MCEntryInterpreter.runtime.hex").read_text().strip())
assert len(engine_runtime) == pins["engine"]["bytes"] == 389818
assert len(engine_runtime) <= 393216
assert sha(engine_runtime) == pins["engine"]["runtimeSHA256"] == engine_json["codeHashes"]["runtimeSHA256"]
assert engine_json["sourceHashes"]["MCEntryInterpreter.sol"] == source_proof["candidateSourceSHA256"]
coord_dir = results / "artifacts/coordinator"
coord_json = read_json(coord_dir / "MCEntryCoordinator.json")
coord_runtime = bytes.fromhex((coord_dir / "MCEntryCoordinator.runtime.hex").read_text().strip())
assert len(coord_runtime) == pins["coordinator"]["bytes"] == 5394
assert sha(coord_runtime) == pins["coordinator"]["runtimeSHA256"] == coord_json["codeHashes"]["runtimeSHA256"]
assert coord_json["sourceHashes"]["MCEntryCoordinator.sol"] == file_sha(coord_dir / "MCEntryCoordinator.sol")
assert pins["baselineEngine"]["runtimeSHA256"] == "1c6390652b8eca5496cfca277fb1b6488eeacb8ef980e5770eea6ff79d98e050"
assert pins["baselineCoordinator"]["runtimeSHA256"] == "fc2fe2e205f1e186754d16b4eeb1dbe2d207b2864fe52eda37acbf807c53d27c"

# Check all full generated-gate output retained as a deterministic gzip archive.
with gzip.open(results / "generated-gate-summary.json.gz", "rt") as stream:
    gate = json.load(stream)
receipts = read_json(results / "canonical-receipts.json")
key = read_json(results / "key-results.json")
assert gate["generatedOnly"] and gate["profile"] == "MC-RANDOM-CLASS-P16-FLOAT-PACKED-CHECKPOINT"
assert gate["wholeGateSeconds"] <= 1200
assert gate["engineBytes"] == 389818 and gate["engineCapBytes"] == 393216
assert gate["bootstrapCount"] == 97 and gate["bootstrapRoot"] == source_proof["actualP16BootstrapRoot"]
assert gate["globalNativeBindings"] == 21 and gate["stringLocalBinding"] == 12
assert gate["rawLimits"] == [71, 471911] and gate["externalLocalGas"] == 1_000_000_000
assert receipts["verifiedReceipts"] == key["verifiedCanonicalReceipts"] == 11814
assert receipts["summary"]["world-count-71-q1"]["lifecycle"] == 2
assert "generated fixtures only" in key["limitations"].lower()

# Generated Java-8 fixture hashes and exact expected float cells.
fixture_dir = root / "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures"
for label in ("packed-array-oracle", "array-savings-boundary", "sparse-array-stress"):
    fixture = read_json(fixture_dir / (label + ".json"))
    assert file_sha(fixture_dir / (label + ".zip")) == fixture["zipSHA256"]

# Independently decode the MR01 machine portions saved for P16 equality proof.
spec = importlib.util.spec_from_file_location("singleScanCheckpointDiagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
comparison = read_json(results / "opaque-equivalence-gate-04/comparison.json")
assert comparison["result"] == "PASS" and comparison["generatedOnly"]
assert len(comparison["comparisons"]) == 9
node = r'''const fs=require('fs'),{keccak256}=require('js-sha3');
const xs=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(xs.map(x=>keccak256(Buffer.from(x,'hex')))));'''
code_keccaks = json.loads(subprocess.run(
    ["node", "-e", node], cwd=root,
    env={**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")},
    input=json.dumps([engine_runtime.hex(), coord_runtime.hex()]),
    text=True, capture_output=True, check=True,
).stdout)
assert code_keccaks == [pins["engine"]["runtimeKeccak256"], pins["coordinator"]["runtimeKeccak256"]]
blobs = []
expected_float = [int(value, 16) for value in read_json(fixture_dir / "packed-array-oracle.json")["hostOutput"]]
for row in comparison["comparisons"]:
    label = row["fixture"]
    tag = "direct" if row["quantum"] == 4096 else "q" + str(row["quantum"])
    relative = f"{label}-{tag}.mr01.bin"
    baseline = (results / "opaque-equivalence-gate-04/baseline" / relative).read_bytes()
    candidate = (results / "opaque-equivalence-gate-04/candidate" / relative).read_bytes()
    assert baseline == candidate
    assert len(candidate) == row["MR01Bytes"]
    assert sha(candidate) == row["MR01SHA256"]
    assert row["MR01ByteIdenticalToAcceptedP16"]
    blobs.append(candidate.hex())
keccaks = json.loads(subprocess.run(
    ["node", "-e", node], cwd=root,
    env={**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")},
    input=json.dumps(blobs), text=True, capture_output=True, check=True,
).stdout)
for row, keccak in zip(comparison["comparisons"], keccaks):
    assert keccak == row["MR01Keccak256"]

# Every quantum retains the historical machine bytes within a build; decoded
# packed/crossover/sparse arrays keep exact cells and canonical representations.
for label in ("packed-array-oracle", "array-savings-boundary", "sparse-array-stress"):
    rows = gate["results"][label]
    for metric in ("opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle"):
        assert len({rows[q][metric] for q in ("q1", "q7", "direct")}) == 1

def inspect_saved(label, quantum):
    p = results / "opaque-equivalence-gate-04/candidate" / (label + "-" + quantum + ".mr01.bin")
    return diagnostic.inspect(bytes(280) + p.read_bytes())

packed = inspect_saved("packed-array-oracle", "direct")
arrays = [row for row in packed["heap"] if row["rank"] == 1 and row["metadata"] == "0x46" and row["count"] == 1024]
assert len(arrays) == 1 and arrays[0]["packedFloat"] and [int(x, 16) for x in arrays[0]["cells"]] == expected_float
boundary = inspect_saved("array-savings-boundary", "direct")
float_arrays = [row for row in boundary["heap"] if row["rank"] == 1 and row["metadata"] == "0x46" and row["count"] == 1024]
ties = [row for row in float_arrays if row["sparse"]]
wins = [row for row in float_arrays if row["packedFloat"]]
assert len(ties) == len(wins) == 1 and ties[0]["sparseCount"] == 341
assert all(int(cell["value"], 16) == 0x3F800000 for cell in wins[0]["packedCells"][:342])
sparse = inspect_saved("sparse-array-stress", "direct")
large_float = [row for row in sparse["heap"] if row["rank"] == 1 and row["metadata"] == "0x46" and row["count"] == 65536]
assert large_float and all(row["sparse"] and not row["packedFloat"] for row in large_float)

resume = gate["results"]["q1-packed-resume-from-successful-array-head"]
assert resume["childEpoch"] == resume["parentEpoch"] + 1
for refusal_set, names in (("packed-malformed-refusals", {
        "packed-both-flags-refusal", "packed-wrong-rank-refusal", "packed-wrong-type-refusal",
        "packed-bad-count-refusal", "packed-noncanonical-density-refusal",
        "packed-truncated-payload-refusal", "float-dense-high-bits-refusal"}),
        ("sparse-malformed-refusals", {
        "sparse-zero-value-refusal", "sparse-duplicate-index-refusal", "sparse-out-of-range-refusal",
        "sparse-excessive-count-refusal", "sparse-undersized-array-refusal",
        "sparse-truncated-pairs-refusal", "sparse-noncanonical-dense-refusal"})):
    failures = gate["results"][refusal_set]
    assert set(failures) == names
    assert all(row["rootUnchanged"] and row["headUnchanged"] and row["logsUnchanged"]
               for row in failures.values())

direct = read_json(results / "opaque-equivalence-gate-04-direct/comparison.json")
assert direct["result"] == "PASS" and direct["comparisonMode"] == "direct-only"
assert len(direct["comparisons"]) == 3
assert all(row["MR01ByteIdenticalToAcceptedP16"] for row in direct["comparisons"])
run_metadata = read_json(results / "run-metadata.json")
assert run_metadata["candidateGatePlusRequiredDirectEqualityWallSeconds"] < 1200

gas = read_json(results / "generated-gas-comparison-gate-04.json")
assert gas["result"] == "PASS" and len(gas["measurements"]) == 9
assert max(row["gasSaved"] for row in gas["measurements"]) == 9_950_957

# Verify the append-only local evidence checksum manifest last.
check_sums(stage / "SHA256SUMS")
print(json.dumps({
    "result": "PASS",
    "bootstrapRoot": source_proof["actualP16BootstrapRoot"],
    "candidateRuntimeBytes": len(engine_runtime),
    "gateSeconds": gate["wholeGateSeconds"],
    "canonicalReceipts": receipts["verifiedReceipts"],
    "MR01P16Comparisons": len(comparison["comparisons"]),
    "gasMeasurements": len(gas["measurements"]),
}, indent=2))
