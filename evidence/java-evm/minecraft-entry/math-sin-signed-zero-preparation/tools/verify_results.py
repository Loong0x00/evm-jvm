#!/usr/bin/env python3
"""Verify archived generated-only Math.sin and sparse checkpoint evidence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
archive = stage / "results/generated-gate-v1"
read = lambda path: json.loads((archive / path).read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()

pins = read("build-pins.json")
summary = read("gate-summary.json")
proof = read("proof.json")
source = read("source-invariants.json")
commitment = read("root-commitment.json")
baseline_pins = read("baseline-pins.json")
manifest = read("manifest.json")

assert summary["profile"] == proof["profile"] == manifest["profile"] == "MC-RANDOM-CLASS-P2-MATH-SIN-SIGNED-ZERO"
assert summary["generatedOnly"] is True and pins["bootstrapCount"] == proof["bootstrapCount"] == 97
assert pins["globalNativeBindings"] == proof["globalNativeBindings"] == 19
assert pins["stringLocalBinding"] == proof["stringLocalBinding"] == 12
assert pins["rawLimits"] == proof["rawLimits"] == [71, 471911]
assert pins["diagnosticClassBound"] == proof["diagnosticClassBound"] == 168
assert pins["runtimeCap"] == proof["runtimeCapBytes"] == 393216
assert pins["engine"]["bytes"] == summary["engineBytes"] == proof["engineBytes"] <= 393216
assert summary["wholeGateSeconds"] == manifest["gateSeconds"] <= manifest["limitSeconds"] == 1200
assert summary["canonicalReceipts"]["verifiedReceipts"] == proof["canonicalReceipts"] == 3091
assert pins["bootstrapRoot"] == summary["bootstrapRoot"] == proof["bootstrapRoot"] == commitment["bootstrapRoot"] == source["orderedRoot"]
assert commitment["changedIndex"] == source["changedBootstrapIndex"] == 89
assert source["allOtherBootstrapImagesByteIdentical"] is True
assert source["baselinePinMatchesSourceDerivedRoot"] is False
assert commitment["priorRoot"] == source["baselineSourceDerivedRoot"]
assert commitment["priorDeclaredPinRoot"] == baseline_pins["bootstrapRoot"]
assert commitment["priorPinMatchesSourceDerivedRoot"] is False

math_bytes = bytes.fromhex((archive / "bootstrap/Math.class.hex").read_text().strip())
assert len(math_bytes) == pins["math"]["bytes"] == 289
assert sha(math_bytes) == pins["math"]["sha256"] == source["mathImageSHA256"]
assert pins["math"]["keccak256"] == source["mathImageKeccak256"]
assert (archive / "bootstrap/Math.sha256").read_text().strip() == sha(math_bytes)
assert source["candidateEngineSourceSHA256"] == manifest["candidateEngineSourceSHA256"]
assert source["baselineEngineSourceSHA256"] == manifest["baselineEngineSourceSHA256"]
assert manifest["engineRuntimeSHA256"] == pins["engine"]["runtimeSHA256"]
assert manifest["engineRuntimeKeccak256"] == pins["engine"]["runtimeKeccak256"]

engine_runtime = bytes.fromhex((archive / "artifacts/engine-runtime.hex").read_text().strip())
coord_runtime = bytes.fromhex((archive / "artifacts/coordinator-runtime.hex").read_text().strip())
assert len(engine_runtime) == pins["engine"]["bytes"]
assert sha(engine_runtime) == pins["engine"]["runtimeSHA256"]
assert len(coord_runtime) == pins["coordinator"]["bytes"] == 5394
assert sha(coord_runtime) == pins["coordinator"]["runtimeSHA256"]
node = 'const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(x.map(v=>keccak256(Buffer.from(v,"hex")))));'
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
keccaks = json.loads(subprocess.run(["node", "-e", node], input=json.dumps([
    engine_runtime.hex(), coord_runtime.hex(),
]), cwd=root, env=env, text=True, capture_output=True, check=True).stdout)
assert keccaks == [pins["engine"]["runtimeKeccak256"], pins["coordinator"]["runtimeKeccak256"]]

# Every ZIP fixture is generated locally, content-addressed, and byte-checked.
fixture_summary = read("fixtures/summary.json")
assert fixture_summary["generatedOnly"] is True
for label, fixture in fixture_summary["fixtures"].items():
    bundle = archive / ("fixtures/" + label + ".zip")
    assert sha(bundle.read_bytes()) == fixture["zipSHA256"], label
    with zipfile.ZipFile(bundle) as zipped:
        assert set(zipped.namelist()) == set(fixture["entries"]), label
        for name, digest in fixture["classSHA256"].items():
            data = zipped.read(name)
            assert sha(data) == digest and len(data) == fixture["classBytes"][name], (label, name)
assert fixture_summary["fixtures"]["math-sin-signed-zero"]["java8HostOracle"] is True


def compare_quantum_rows(rows, *, lifecycle=2):
    assert set(rows) == {"q1", "q7", "direct"}
    first = rows["q1"]
    for key, row in rows.items():
        for field in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
            assert row[field] == first[field], (key, field)
        assert row["lifecycle"] == lifecycle and row["javaKind"] == 0
        assert row["jvmSteps"] > 0
        world = row["world"]
        head = json.loads((archive / ("heads/" + world + ".json")).read_text())
        checkpoint = (archive / ("checkpoints/" + world + ".bin")).read_bytes()
        assert sha(checkpoint) == head["checkpointSHA256"]
        assert head["machineRoot"] == row["machineRoot"] and head["lifecycle"] == row["lifecycle"]


compare_quantum_rows(proof["signedZeroQ1Q7Direct"])
compare_quantum_rows(proof["retainedSqrtQ1Q7Direct"])
compare_quantum_rows(proof["sparseQ1Q7Direct"])

# Decode the exact guest packed long statics from the signed-zero checkpoint.
sin_q1 = proof["signedZeroQ1Q7Direct"]["q1"]
head = json.loads((archive / ("heads/" + sin_q1["world"] + ".json")).read_text())
checkpoint = archive / ("checkpoints/" + sin_q1["world"] + ".bin")
assert sha(checkpoint.read_bytes()) == head["checkpointSHA256"]
static_values = next(row for row in sin_q1["initialization"] if row["classIndex"] == 0)["staticValues"]
raw_values = {row["fieldIndex"]: int(row["packedValue"], 16) & 0xffffffffffffffff for row in static_values}
assert raw_values == {0: 0, 1: 0x8000000000000000, 2: 7}

# The complete existing sqrt regression and sparse q1 parent->child resume remain.
sparse = proof["sparseQ1Q7Direct"]["q1"]
assert sparse["heapCounts"]["arrayElements"] == 197638
q1 = proof["sparseQ1ParentChild"]
parent_cp = (archive / "checkpoints/sparse-array-q1-parent.bin").read_bytes()
assert sha(parent_cp) == q1["parentCheckpointSHA256"]
assert q1["largePrimitiveArrays"] == 1 and q1["childEpoch"] == q1["parentEpoch"] + 1
assert q1["childGasUsed"] <= pins["externalLocalGas"] and q1["childElapsedMS"] <= 30000
for label in ("sparse-zero-value-refusal", "sparse-duplicate-index-refusal", "sparse-out-of-range-refusal",
              "sparse-excessive-count-refusal", "sparse-undersized-array-refusal",
              "sparse-truncated-pairs-refusal", "sparse-noncanonical-dense-refusal"):
    refusal = read("refusals/" + label + ".json")
    assert refusal["selector"] == "0x71540d20" and refusal["error"] == "LC0StateError"
    assert refusal["rootUnchanged"] and refusal["headUnchanged"] and refusal["logsUnchanged"]

# Positive/negative finite values, NaN, and both infinities atomically refuse
# with MathSinProfileError(1,pc), preserving either the empty epoch-0 Head or
# the latest successful q1/q7 Head byte-for-byte and emitting no child epoch.
for label in ("math-sin-positive-refusal", "math-sin-negative-refusal", "math-sin-nan-refusal",
              "math-sin-positive-infinity-refusal", "math-sin-negative-infinity-refusal"):
    rows = proof["unsupportedInputs"][label]
    assert set(rows) == {"q1", "q7", "direct"}
    for quantum, key in ((1, "q1"), (7, "q7"), (4096, "direct")):
        refusal = read("refusals/" + label + "-q" + str(quantum) + ".json")
        head_bytes = (archive / ("heads/" + label + "-q" + str(quantum) + ".json")).read_bytes()
        assert sha(head_bytes) == refusal["durableHeadSHA256Before"] == refusal["durableHeadSHA256After"]
        saved_head = json.loads(head_bytes)
        assert refusal["durableHeadUnchanged"] and refusal["durableHeadEpochBefore"] == refusal["durableHeadEpochAfter"] == saved_head["epoch"]
        assert refusal["selector"] == rows[key]["selector"] == "0x3a439c67"
        assert refusal["uint256Words"] == rows[key]["uint256Words"]
        assert refusal["uint256Words"][0] == "1" and int(refusal["uint256Words"][1]) > 0
        assert refusal["rootUnchanged"] and refusal["checkpointBytes"] == 0
        assert refusal["candidateHead"] == refusal["candidateCheckpoint"] == refusal["candidateRoot"] == ""
        if saved_head["epoch"]:
            cp = archive / ("checkpoints/" + label + "-q" + str(quantum) + ".bin")
            assert sha(cp.read_bytes()) == saved_head["checkpointSHA256"]
        else:
            assert saved_head["lifecycle"] == 0

# Recheck both the archive's full manifest/checksum set and requested top-level
# results/SHA256SUMS. Each checksum file excludes only itself.
for relative, digest in manifest["files"].items():
    assert sha((archive / relative).read_bytes()) == digest, relative
for line in (archive / "SHA256SUMS").read_text().splitlines():
    digest, relative = line.split("  ", 1)
    assert sha((archive / relative).read_bytes()) == digest, relative
results_root = stage / "results"
for line in (results_root / "SHA256SUMS").read_text().splitlines():
    digest, relative = line.split("  ", 1)
    assert sha((results_root / relative).read_bytes()) == digest, relative
assert (results_root / "SHA256SUMS").is_file()
print(json.dumps({
    "verified": "generated Math.sin signed-zero binding + explicit refusal + preserved sparse checkpoint gate",
    "bootstrapRoot": pins["bootstrapRoot"], "mathSHA256": pins["math"]["sha256"],
    "engineBytes": pins["engine"]["bytes"], "wholeGateSeconds": summary["wholeGateSeconds"],
    "canonicalReceipts": proof["canonicalReceipts"],
    "scope": "generated-only; parent independent rebuild and original replay still required",
}, indent=2))
