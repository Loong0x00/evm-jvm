#!/usr/bin/env python3
"""Verify hashes and key generated-only witnesses in the P9 evidence archive."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
import zipfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
archive = stage / "results/generated-gate-p9"
read = lambda rel: json.loads((archive / rel).read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = read("manifest.json")
proof = read("proof.json")
pins = read("build-pins.json")
summary = read("gate-summary.json")
fixture_summary = read("fixtures/summary.json")
source = read("source-invariants.json")
assert proof["status"] == manifest["status"] == "WORKER_GENERATED_GATE_PASS_PENDING_INDEPENDENT_PARENT_REPLAY"
assert proof["notAcceptance"] is True and proof["independentReplay"] == "REQUIRED; not performed by this worker"
assert summary["generatedOnly"] is True and fixture_summary["generatedOnly"] is True
assert summary["wholeGateSeconds"] == manifest["gateSeconds"] == proof["wholeGateSeconds"] <= 1200
assert summary["canonicalReceipts"]["verifiedReceipts"] == proof["canonicalReceipts"] == manifest["canonicalReceipts"] == 6112
assert pins["bootstrapRoot"] == summary["bootstrapRoot"] == source["actualSolidityP9BootstrapRoot"] == proof["bootstrapRoot"]
assert source["normalizedByteExactToP6"] is True and source["changedBootstrapIndices"] == [89]
assert source["changedOther96Images"] == 0 and source["globalNativeBindings"] == 20
assert source["retainedP6Bindings"] == list(range(1, 20)) and source["rawLimits"] == [71, 471911]
assert pins["globalNativeBindings"] == 20 and pins["runtimeCap"] == 393216
assert pins["engine"]["bytes"] == summary["engineBytes"] == proof["engineBytes"] == 388632
assert pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["math"]["bytes"] == 304 and pins["math"]["sha256"] == source["mathImageSHA256"]
assert pins["math"]["keccak256"] == source["mathImageKeccak256"]

# Strict Math image and runtime artifacts.
math = bytes.fromhex((archive / "bootstrap/Math.class.hex").read_text().strip())
assert len(math) == pins["math"]["bytes"] and sha(math) == pins["math"]["sha256"]
assert (archive / "bootstrap/Math.sha256").read_text().strip() == sha(math)
engine = bytes.fromhex((archive / "artifacts/engine-runtime.hex").read_text().strip())
coordinator = bytes.fromhex((archive / "artifacts/coordinator-runtime.hex").read_text().strip())
assert len(engine) == pins["engine"]["bytes"] and sha(engine) == pins["engine"]["runtimeSHA256"]
assert len(coordinator) == pins["coordinator"]["bytes"] and sha(coordinator) == pins["coordinator"]["runtimeSHA256"]
node = 'const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(x.map(v=>keccak256(Buffer.from(v,"hex")))))'
import os
keccak_env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
keccaks = json.loads(subprocess.run(["node", "-e", node], input=json.dumps([engine.hex(), coordinator.hex()]),
                                    cwd=root, env=keccak_env, text=True, capture_output=True, check=True).stdout)
assert keccaks == [pins["engine"]["runtimeKeccak256"], pins["coordinator"]["runtimeKeccak256"]]

# Exact generated Java-8 fixture transport bytes and member hashes.
for label, row in fixture_summary["fixtures"].items():
    bundle = archive / ("fixtures/" + label + ".zip")
    assert sha(bundle.read_bytes()) == row["zipSHA256"]
    with zipfile.ZipFile(bundle) as z:
        assert set(z.namelist()) == set(row["entries"])
        for name, digest in row["classSHA256"].items():
            data = z.read(name)
            assert sha(data) == digest and len(data) == row["classBytes"][name]

# Decode archived engine checkpoints without executing/evaluating guest code.
diagnostic_path = root / "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/checkpoint_diagnostic.py"
spec = importlib.util.spec_from_file_location("p9_checkpoint_diagnostic", diagnostic_path)
diagnostic = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(diagnostic)
packed_fixture = read("fixtures/packed-array-oracle.json")
expected = packed_fixture["hostOutput"]
assert packed_fixture["java8HostOracle"] and len(expected) == 1024
assert sum(int(x, 16) != 0 for x in expected) == 348

def check_head(label):
    head = read("heads/" + label + ".json")
    blob = (archive / "checkpoints" / (label + ".bin")).read_bytes()
    assert sha(blob) == head["checkpointSHA256"]
    return head, diagnostic.inspect(blob)

asin_fixture = read("fixtures/math-asin-bounded-edges.json")
asin_vectors = asin_fixture["asinVectors"]
assert asin_fixture["java8HostOracle"] and len(asin_vectors) > 0
asin_rows = summary["results"]["math-asin-bounded-edges"]
base = asin_rows["q1"]
mask64 = (1 << 64) - 1
def ordered(bits): return (~bits & mask64) if bits >> 63 else bits | (1 << 63)
for key, q in (("q1", 1), ("q7", 7), ("direct", 4096)):
    row = asin_rows[key]
    for field in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
        assert row[field] == base[field]
    head, decoded = check_head("math-asin-bounded-edges-q" + str(q))
    assert decoded["lifecycle"] == head["lifecycle"] == 2
    static = decoded["initialization"][0]["staticValues"]
    values = {v["fieldIndex"]: int(v["packedValue"], 16) for v in static}
    n = len(asin_vectors)
    assert len(values) == 2 * n + 1
    for i, vector in enumerate(asin_vectors):
        got = values[i] & mask64
        want = int(vector["javaDoubleRaw"], 16)
        assert abs(ordered(got) - ordered(want)) <= 1, (vector["name"], hex(got), hex(want))
        assert values[n + i] & 0xffffffff == int(vector["javaFloatRaw"], 16), vector["name"]
        if "zero" in vector["name"]: assert got == want
        if vector["name"] == "one": assert got == 0x3ff921fb54442d18
        if vector["name"] == "negative-one": assert got == 0xbff921fb54442d18
    assert values[2 * n] & 0xffffffff == 7

packed_rows = summary["results"]["packed-array-oracle"]
packed_base = packed_rows["q1"]
for key, q in (("q1", 1), ("q7", 7), ("direct", 4096)):
    row = packed_rows[key]
    for field in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
        assert row[field] == packed_base[field]
    arrays = [h for h in row["heap"] if h["packedFloat"]]
    assert len(arrays) == 1 and arrays[0]["count"] == 1024 and not arrays[0]["sparse"]
    actual_summary = [x["value"][2:].zfill(8) for x in arrays[0]["packedCells"]]
    assert actual_summary == expected
    _, decoded = check_head("packed-array-oracle-q" + str(q))
    arrays = [h for h in decoded["heap"] if h["packedFloat"]]
    assert len(arrays) == 1 and arrays[0]["count"] == 1024
    assert [x["value"][2:].zfill(8) for x in arrays[0]["packedCells"]] == expected
assert summary["results"]["q1-packed-resume-from-successful-array-head"]["packedFloatArrays"] == 1
for label in ("math-asin-above-bound-refusal", "math-asin-below-negative-bound-refusal",
              "math-asin-nan-refusal", "math-asin-positive-infinity-refusal",
              "math-asin-negative-infinity-refusal"):
    for key in ("q1", "q7", "direct"):
        refusal = summary["results"][label][key]
        assert refusal["selector"] == "0xe309722e" and refusal["uint256Words"][0] == "1"
        assert refusal["rootUnchanged"] and refusal["checkpointBytes"] == 0
for label, row in summary["results"]["packed-malformed-refusals"].items():
    assert row["rootUnchanged"] and row["headUnchanged"] and row["logsUnchanged"]

sparse_rows = summary["results"]["sparse-array-stress"]
sparse_base = sparse_rows["q1"]
for key, q in (("q1", 1), ("q7", 7), ("direct", 4096)):
    row = sparse_rows[key]
    for field in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
        assert row[field] == sparse_base[field]
    sparse = [h for h in row["heap"] if h["sparse"]]
    assert [h["count"] for h in sparse] == [65536, 65536, 65536]
    _, decoded = check_head("sparse-array-stress-q" + str(q))
    assert len([h for h in decoded["heap"] if h["sparse"]]) == 3
assert summary["results"]["q1-sparse-resume-from-successful-large-array-head"]["largePrimitiveArrays"] == 1
for label, row in summary["results"]["sparse-malformed-refusals"].items():
    assert row["rootUnchanged"] and row["headUnchanged"]

# The report tar contains the complete receipt set and can be listed without
# extracting guest state or relying on a worker's temporary directory.
canonical = json.loads((archive / "canonical-receipts.log").read_text())
assert canonical["verifiedReceipts"] == proof["canonicalReceipts"]
with tarfile.open(archive / "reports.tar.gz", "r:gz") as tar:
    members = [m for m in tar.getmembers() if m.isfile()]
    slices = [m for m in members if Path(m.name).name.startswith("slice-") and m.name.endswith(".json")]
    receipt_counts = {world: count["receipts"] for world, count in canonical["summary"].items()}
    assert sum(receipt_counts.values()) == proof["canonicalReceipts"]
    for world, count in receipt_counts.items():
        found = [m for m in slices if m.name.startswith("reports/" + world + "/")]
        assert len(found) == count, (world, len(found), count)

# Verify the exact no-overwrite inventory and checksums.
expected_files = manifest["files"]
actual_files = {p.relative_to(archive).as_posix() for p in archive.rglob("*")
                if p.is_file() and p.name not in ("manifest.json", "SHA256SUMS")}
assert set(expected_files) == actual_files
for rel, digest in expected_files.items():
    assert sha((archive / rel).read_bytes()) == digest, rel
for line in (archive / "SHA256SUMS").read_text().splitlines():
    digest, rel = line.split("  ", 1)
    assert sha((archive / rel).read_bytes()) == digest, rel
results_root = stage / "results"
for line in (results_root / "SHA256SUMS").read_text().splitlines():
    digest, rel = line.split("  ", 1)
    assert sha((results_root / rel).read_bytes()) == digest, rel

print(json.dumps({"result": "PASS", "status": proof["status"], "engineBytes": len(engine),
                  "bootstrapRoot": proof["bootstrapRoot"], "asinQ1Q7Direct": True,
                  "packedFloatCellsComparedToJava8": 1024, "packedNonzeroCells": 348,
                  "packedMalformedCases": len(summary["results"]["packed-malformed-refusals"]),
                  "sparseMalformedCases": len(summary["results"]["sparse-malformed-refusals"]),
                  "canonicalReceipts": proof["canonicalReceipts"], "archivedSliceReceiptFiles": len(slices),
                  "wholeGateSeconds": proof["wholeGateSeconds"],
                  "archiveFiles": len(actual_files), "independentReplayStillRequired": True}, indent=2))
