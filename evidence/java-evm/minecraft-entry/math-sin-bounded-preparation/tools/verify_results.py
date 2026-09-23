#!/usr/bin/env python3
"""Verify durable bounded-sine candidate artifacts and generated EVM receipts."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
archive = stage / "results/generated-gate-v2"
read = lambda name: json.loads((archive / name).read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()

pins = read("build-pins.json")
summary = read("gate-summary.json")
proof = read("proof.json")
source = read("source-invariants.json")
commitment = read("root-commitment.json")
baseline_pins = read("baseline-pins.json")
manifest = read("manifest.json")
fixtures = read("fixtures/summary.json")

assert summary["profile"] == proof["profile"] == manifest["profile"] == "MC-RANDOM-CLASS-P2-MATH-SIN-BOUNDED-Q120"
assert summary["generatedOnly"] is True and pins["bootstrapCount"] == proof["bootstrapCount"] == 97
assert pins["globalNativeBindings"] == proof["globalNativeBindings"] == 19
assert pins["stringLocalBinding"] == proof["stringLocalBinding"] == 12
assert pins["rawLimits"] == proof["rawLimits"] == [71, 471911]
assert pins["diagnosticClassBound"] == proof["diagnosticClassBound"] == 168
assert pins["runtimeCap"] == proof["runtimeCapBytes"] == 393216
assert pins["engine"]["bytes"] == summary["engineBytes"] == proof["engineBytes"] <= 393216
assert summary["wholeGateSeconds"] == manifest["gateSeconds"] <= manifest["limitSeconds"] == 1200
assert summary["canonicalReceipts"]["verifiedReceipts"] == proof["canonicalReceipts"]
assert proof["canonicalReceipts"] == 3769
assert pins["bootstrapRoot"] == summary["bootstrapRoot"] == proof["bootstrapRoot"] == commitment["bootstrapRoot"] == source["orderedRoot"]
assert source["changedBootstrapIndices"] == [] and source["bootstrapImagesByteIdentical"] is True
assert source["orderedRoot"] == "e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac"
assert commitment["priorHistoricalP1PinRoot"] == baseline_pins["bootstrapRoot"]
assert commitment["historicalP1PinMatchesSourceDerivedRoot"] is False
assert commitment["priorSourceDerivedRoot"] == commitment["bootstrapRoot"]
assert source["globalNativeBindings"] == 19 and source["stringLocalBinding"] == 12
assert source["rawLimits"] == [71, 471911]

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
node = 'const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(x.map(v=>keccak256(Buffer.from(v,"hex")))))'
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
keccaks = json.loads(subprocess.run(["node", "-e", node], input=json.dumps([
    engine_runtime.hex(), coord_runtime.hex()
]), cwd=root, env=env, text=True, capture_output=True, check=True).stdout)
assert keccaks == [pins["engine"]["runtimeKeccak256"], pins["coordinator"]["runtimeKeccak256"]]

# Every generated ZIP is exact and contains only its enumerated class payloads.
assert fixtures["generatedOnly"] is True
for label, fixture in fixtures["fixtures"].items():
    bundle = archive / ("fixtures/" + label + ".zip")
    assert sha(bundle.read_bytes()) == fixture["zipSHA256"], label
    with zipfile.ZipFile(bundle) as zipped:
        assert set(zipped.namelist()) == set(fixture["entries"]), label
        for name, digest in fixture["classSHA256"].items():
            data = zipped.read(name)
            assert sha(data) == digest and len(data) == fixture["classBytes"][name], (label, name)
for label in ("math-sin-bounded-edges", "math-sin-bounded-grid"):
    fixture = read("fixtures/" + label + ".json")
    assert fixture["java8HostOracle"] and len(fixture["sinVectors"]) > 0

# Independently inspect q1/q7/direct archived checkpoints and compare every
# committed raw double/float result against its generated Java 8 witness.
spec_path = here / "checkpoint_diagnostic.py"
spec = __import__("importlib.util").util.spec_from_file_location("verifyBoundedSinCheckpoint", spec_path)
diagnostic = __import__("importlib.util").util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
MASK64 = (1 << 64) - 1

def ordered(bits):
    return (~bits & MASK64) if bits >> 63 else bits | (1 << 63)

def check_sin_world(label, quantum):
    world_name = "world-" + label + "-q" + str(quantum)
    head = read("heads/" + world_name + ".json")
    cp_path = archive / "checkpoints/" / (world_name + ".bin")
    cp = cp_path.read_bytes()
    assert sha(cp) == head["checkpointSHA256"]
    decoded = diagnostic.inspect(cp)
    vectors = read("fixtures/" + label + ".json")["sinVectors"]
    rows = decoded["initialization"][0]["staticValues"]
    values = {row["fieldIndex"]: int(row["packedValue"], 16) for row in rows}
    count = len(vectors)
    assert decoded["lifecycle"] == head["lifecycle"] == 2
    assert len(values) == 2 * count + 1
    for i, vector in enumerate(vectors):
        got = values[i] & MASK64
        want = int(vector["javaDoubleRaw"], 16)
        distance = abs(ordered(got) - ordered(want))
        assert distance <= 1, (world_name, vector["name"], hex(got), hex(want), distance)
        assert (values[count + i] & 0xffffffff) == int(vector["javaFloatRaw"], 16)
        if vector["name"] in ("positive-zero", "negative-zero"):
            assert got == want
        if vector["name"] == "measured-positive":
            assert int(vector["inputRaw"], 16) == 0x3f1921fb54442d18
            assert got == 0x3f1921fb539ecf31 and (values[count + i] & 0xffffffff) == 0x38c90fdb
    assert (values[2 * count] & 0xffffffff) == 7

for label in ("math-sin-bounded-edges", "math-sin-bounded-grid"):
    rows = proof["boundedEdgesQ1Q7Direct"] if label.endswith("edges") else proof["sampledGridQ1Q7Direct"]
    assert set(rows) == {"q1", "q7", "direct"}
    first = rows["q1"]
    for quantum, key in ((1, "q1"), (7, "q7"), (4096, "direct")):
        row = rows[key]
        for field in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
            assert row[field] == first[field], (label, quantum, field)
        world = row["world"]
        assert world == "world-" + label + "-q" + str(quantum)
        archived_head = read("heads/" + world + ".json")
        assert archived_head["machineRoot"] == row["machineRoot"]
        check_sin_world(label, quantum)
        receipt_paths = sorted((archive / "receipts" / world).glob("slice-*.json"))
        assert len(receipt_paths) == archived_head["epoch"]
        for receipt_path in receipt_paths:
            receipt = json.loads(receipt_path.read_text())
            assert receipt["gasUsed"] > 0 and receipt["elapsedMS"] <= 30000
            cp_candidates = list((archive / "checkpoints" / world).glob(receipt_path.stem + "-*.bin"))
            assert len(cp_candidates) == 1
            checkpoint = cp_candidates[0].read_bytes()
            assert sha(checkpoint) == receipt["checkpointSHA256"]
            assert len(checkpoint) == receipt["checkpointBytes"]

# The full test-only Q120 model is not runtime code; confirm its pinned oracle
# and generated-only counts without overclaiming universal correctly-rounded sin.
model = read("q120-test-only-model.json")
assert model["purpose"].startswith("test-only")
assert model["oracleSHA256"] == "6001a5c714608ca9649b08b25eba27a3aa011f7c870a32ddae15ca330fefc058"
assert model["gridInputs"] == 65536 and model["maxBinary64ULPDistanceFromJava8"] == 1
assert model["binary64BitMismatchCount"] == 2008 and model["floatCastBitMismatchCount"] == 0

# Atomic out-of-range/nonfinite refusals preserve exact Heads and have no child
# checkpoint publication; the q1/q7/direct selector is the specific Math error.
refusal_labels = ("math-sin-above-bound-refusal", "math-sin-below-negative-bound-refusal",
                  "math-sin-nan-refusal", "math-sin-positive-infinity-refusal",
                  "math-sin-negative-infinity-refusal")
for label in refusal_labels:
    for quantum in (1, 7, 4096):
        key = "q1" if quantum == 1 else "q7" if quantum == 7 else "direct"
        row = proof["unsupportedInputs"][label][key]
        refusal = read("refusals/" + label + "-q" + str(quantum) + ".json")
        head_bytes = (archive / "heads/" / (label + "-q" + str(quantum) + ".json")).read_bytes()
        assert sha(head_bytes) == refusal["durableHeadSHA256Before"] == refusal["durableHeadSHA256After"]
        assert refusal["durableHeadUnchanged"] and refusal["rootUnchanged"] and refusal["checkpointBytes"] == 0
        assert refusal["selector"] == row["selector"] == "0x3a439c67"
        assert refusal["uint256Words"][0] == "1" and int(refusal["uint256Words"][1]) > 0

# Retain exact sparse-array q1 parent/child checkpoints and malformed refusals.
sparse = proof["sparseQ1Q7Direct"]["q1"]
assert sparse["heapCounts"]["arrayElements"] == 197638
q1 = proof["sparseQ1ParentChild"]
parent_cp = (archive / "checkpoints/sparse-array-q1-parent.bin").read_bytes()
assert sha(parent_cp) == q1["parentCheckpointSHA256"]
assert q1["largePrimitiveArrays"] == 1 and q1["childEpoch"] == q1["parentEpoch"] + 1
for label in ("sparse-zero-value-refusal", "sparse-duplicate-index-refusal", "sparse-out-of-range-refusal",
              "sparse-excessive-count-refusal", "sparse-undersized-array-refusal",
              "sparse-truncated-pairs-refusal", "sparse-noncanonical-dense-refusal"):
    refusal = read("refusals/" + label + ".json")
    assert refusal["selector"] == "0x71540d20" and refusal["error"] == "LC0StateError"
    assert refusal["rootUnchanged"] and refusal["headUnchanged"] and refusal["logsUnchanged"]

# Verify the nested and top-level manifests/checksum sets; neither checksum file
# self-hashes. Every archived raw EVM receipt and checkpoint is covered.
for relative, digest in manifest["files"].items():
    assert sha((archive / relative).read_bytes()) == digest, relative
for line in (archive / "SHA256SUMS").read_text().splitlines():
    digest, relative = line.split("  ", 1)
    assert sha((archive / relative).read_bytes()) == digest, relative
for line in (stage / "results/SHA256SUMS").read_text().splitlines():
    digest, relative = line.split("  ", 1)
    assert sha((stage / "results" / relative).read_bytes()) == digest, relative
print(json.dumps({
    "verified": "bounded Q120 Math.sin EVM receipts + signed zero + refusal + preserved sparse checkpoint gate",
    "bootstrapRoot": pins["bootstrapRoot"], "engineBytes": pins["engine"]["bytes"],
    "wholeGateSeconds": summary["wholeGateSeconds"], "canonicalReceipts": proof["canonicalReceipts"],
    "sinQ1Q7DirectSlices": sum(len(list((archive / "receipts" / ("world-math-sin-bounded-" + kind + "-q" + str(q))).glob("slice-*.json"))) for kind in ("edges", "grid") for q in (1, 7, 4096)),
    "scope": "generated-only finite |x|<=0x401921fb54442d18; sampled Java8 comparison, no original replay/Minecraft Done claim",
}, indent=2))
