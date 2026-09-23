#!/usr/bin/env python3
"""Verify archived candidate source, generated fixtures, receipts and checkpoints."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
import tarfile
import zipfile

here = Path(__file__).resolve().parent
stage = next(path for path in here.parents
             if (path / "engine/MCEntryInterpreter.sol").is_file()
             and (path / "coordinator/MCEntryCoordinator.sol").is_file())
root = next(path for path in stage.parents if (path / "jvmevm/runtime/node_modules").is_dir())
archive = here.parent if (here.parent / "proof.json").is_file() else stage / "results/generated-gate-v5"
read = lambda name: json.loads((archive / name).read_text())
sha_bytes = lambda data: hashlib.sha256(data).hexdigest()

def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

# Verify archive-local and top-level durable checksum manifests.
def check_sums(path):
    expected = {}
    for line in path.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        assert relative not in expected
        expected[relative] = digest
    base = path.parent
    actual = {p.relative_to(base).as_posix(): sha_file(p) for p in base.rglob("*")
              if p.is_file() and p != path}
    assert actual == expected, (path, len(actual), len(expected))

check_sums(archive / "SHA256SUMS")
check_sums(stage / "results/SHA256SUMS")
manifest = read("manifest.json")
proof = read("proof.json")
pins = read("build/pins.json")
summary = read("gate-summary.json")
source = read("source/source-invariants.json")
fixtures = read("fixtures/summary.json")
assert manifest["profile"] == proof["profile"] == summary["profile"] == "MC-RANDOM-CLASS-P5-FLOAT-PACKED-CHECKPOINT"
assert proof["generatedOnly"] and summary["generatedOnly"]
assert summary["wholeGateSeconds"] == manifest["gateSeconds"] == proof["wholeGateSeconds"] <= 1200
assert manifest["canonicalReceipts"] == proof["canonicalReceipts"] == summary["canonicalReceipts"]["verifiedReceipts"]
assert manifest["bootstrapRoot"] == proof["bootstrapRoot"] == pins["bootstrapRoot"] == summary["bootstrapRoot"]
assert pins["bootstrapCount"] == proof["bootstrapCount"] == 97
assert pins["rawLimits"] == proof["rawLimits"] == [71, 471911]
assert pins["globalNativeBindings"] == proof["globalNativeBindings"] == 19
assert pins["stringLocalBinding"] == proof["stringLocalBinding"] == 12
assert pins["runtimeCap"] == proof["runtimeCapBytes"] == 393216
assert pins["engine"]["bytes"] == proof["runtimeBytes"] == summary["engineBytes"] <= 393216
assert pins["engine"]["runtimeSHA256"] == proof["runtimeSHA256"] == manifest["runtimeSHA256"]
assert pins["engine"]["runtimeKeccak256"] == proof["runtimeKeccak256"] == manifest["runtimeKeccak256"]
assert source["candidateSourceSHA256"] == proof["sourceSHA256"] == manifest["candidateSourceSHA256"]
assert source["result"] == "PASS" and source["bootstrapImagesAndRootFunctionByteIdentical"]
assert source["transportDriverByteIdenticalToBaseline"] and source["coordinatorByteIdenticalToBaseline"]
assert source["rawLimits"] == [71, 471911]
assert pins["packedFloatWire"] == {
    "flag": "0x40000000", "sparseFlag": "0x80000000", "minimumLength": 1024,
    "cellWidthBytes": 4,
    "strictSelection": "4*length < 4+12*nonzero",
    "guestRepresentation": "eager dense uint64[]",
}

engine_source = (archive / "source/MCEntryInterpreter.sol").read_bytes()
coordinator_source = (archive / "source/MCEntryCoordinator.sol").read_bytes()
driver_source = (archive / "source/canonical-driver.go.txt").read_bytes()
assert sha_bytes(engine_source) == source["candidateSourceSHA256"]
assert sha_bytes(coordinator_source) == source["coordinatorSHA256"]
assert sha_bytes(driver_source) == source["transportDriverSHA256"]
assert driver_source == (archive / "baseline/canonical-driver.go.txt").read_bytes()
assert coordinator_source == (archive / "baseline/MCEntryCoordinator.sol").read_bytes()
assert sha_bytes((archive / "baseline/MCEntryInterpreter.sol").read_bytes()) == source["baselineSourceSHA256"]

engine_runtime = bytes.fromhex((archive / "artifacts/MCEntryInterpreter.runtime.hex").read_text().strip())
coordinator_runtime = bytes.fromhex((archive / "artifacts/MCEntryCoordinator.runtime.hex").read_text().strip())
assert len(engine_runtime) == pins["engine"]["bytes"]
assert sha_bytes(engine_runtime) == pins["engine"]["runtimeSHA256"]
assert len(coordinator_runtime) == pins["coordinator"]["bytes"]
assert sha_bytes(coordinator_runtime) == pins["coordinator"]["runtimeSHA256"]
node = 'const fs=require("fs"),{keccak256}=require("js-sha3");const a=JSON.parse(fs.readFileSync(0,"utf8"));console.log(JSON.stringify(a.map(x=>keccak256(Buffer.from(x,"hex")))));'
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
keccaks = json.loads(subprocess.run(
    ["node", "-e", node], input=json.dumps([engine_runtime.hex(), coordinator_runtime.hex()]),
    cwd=root, env=env, text=True, capture_output=True, check=True).stdout)
assert keccaks == [pins["engine"]["runtimeKeccak256"], pins["coordinator"]["runtimeKeccak256"]]

# Every preserved ZIP is generated Java 8 input, exact at both archive and class level.
assert len(fixtures["fixtures"]) > 30
for label, fixture in fixtures["fixtures"].items():
    bundle = archive / "fixtures" / (label + ".zip")
    meta = read("fixtures/" + label + ".json")
    assert sha_file(bundle) == fixture["zipSHA256"] == meta["zipSHA256"]
    assert meta["entries"] == fixture["entries"]
    with zipfile.ZipFile(bundle) as zipped:
        assert set(zipped.namelist()) == set(fixture["entries"])
        for name, digest in fixture["classSHA256"].items():
            data = zipped.read(name)
            assert len(data) == fixture["classBytes"][name]
            assert sha_bytes(data) == digest
packed_oracle = fixtures["fixtures"]["packed-array-oracle"]
assert packed_oracle["java8HostOracle"] and len(packed_oracle["hostOutput"]) == 1024
assert packed_oracle["bindingCount"] == 2

# Decode q1/q7/direct checkpoints independently and compare every restored
# guest uint64 cell with the Java-8 raw-float oracle. This proves eager dense state.
spec = importlib.util.spec_from_file_location("packedCheckpointDiagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
expected = [int(value, 16) for value in packed_oracle["hostOutput"]]
packed_proof = proof["packedFixture"]
assert packed_proof["nonzeroCells"] == sum(value != 0 for value in expected) == 348
assert packed_proof["packedPayloadBytes"] == 4096
assert packed_proof["sparsePayloadBytes"] == 4 + 12 * 348 == 4180
assert packed_proof["strictWireSavingBytes"] == 84
assert packed_proof["specialRawCells"] == {
    "customQuietNaN": "0x7fc12345", "negativeZero": "0x80000000",
    "positiveInfinity": "0x7f800000", "negativeInfinity": "0xff800000",
    "positiveMinimumSubnormal": "0x00000001", "negativeMinimumSubnormal": "0x80000001",
    "maximumFinite": "0x7f7fffff",
}
for quantum, name in ((1, "q1"), (7, "q7"), (4096, "direct")):
    saved_name = "q4096" if quantum == 4096 else name
    head = read("heads/packed-array-oracle-" + saved_name + ".json")
    checkpoint = (archive / ("checkpoints/packed-array-oracle-" + saved_name + ".bin")).read_bytes()
    assert sha_bytes(checkpoint) == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["lifecycle"] == head["lifecycle"] == 2
    packed = [array for array in decoded["heap"]
              if array["rank"] == 1 and array["metadata"].endswith("46")
              and array["count"] == 1024 and array["packedFloat"]]
    assert len(packed) == 1, name
    actual = [int(cell, 16) for cell in packed[0]["cells"]]
    assert actual == expected, name
    assert [actual[i] for i in (0, 500, 501, 502, 503, 504, 505)] == [
        0x7fc12345, 0x80000000, 0x7f800000, 0xff800000,
        0x00000001, 0x80000001, 0x7f7fffff,
    ], name
    row = summary["results"]["packed-array-oracle"]["direct" if quantum == 4096 else name]
    assert row["machineRoot"] == summary["results"]["packed-array-oracle"]["q1"]["machineRoot"]
    assert row["opaquePayloadSHA256"] == summary["results"]["packed-array-oracle"]["q1"]["opaquePayloadSHA256"]

# The original sparse float-array profile stays canonical and byte-for-byte resumable.
for quantum, name in ((1, "q1"), (7, "q7"), (4096, "direct")):
    saved_name = "q4096" if quantum == 4096 else name
    head = read("heads/sparse-array-stress-" + saved_name + ".json")
    checkpoint = (archive / ("checkpoints/sparse-array-stress-" + saved_name + ".bin")).read_bytes()
    assert sha_bytes(checkpoint) == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    arrays = [array for array in decoded["heap"] if array["rank"] == 1 and array["metadata"].endswith("46")]
    large = [array for array in arrays if array["count"] == 65536]
    assert len(large) == 1 and large[0]["sparse"] and not large[0]["packedFloat"]
    assert all(not array["packedFloat"] for array in arrays)

resume = proof["packedQ1Resume"]
assert resume == summary["results"]["q1-packed-resume-from-successful-array-head"]
for role, digest in (("parent", resume["parentCheckpointSHA256"]),
                     ("child", resume["childCheckpointSHA256"])):
    cp = archive / ("checkpoints/packed-array-q1-resume-" + role + ".bin")
    receipt = read("receipts/packed-array-q1-resume-" + role + ".json")
    assert sha_file(cp) == digest == receipt["checkpointSHA256"]
assert resume["childEpoch"] == resume["parentEpoch"] + 1

# Malformed-wire tests prove atomic refusals (no root, Head, or log change).
packed_refusal_labels = set(proof["malformedPackedRefusals"])
assert packed_refusal_labels == {
    "packed-both-flags-refusal", "packed-wrong-rank-refusal",
    "packed-wrong-type-refusal", "packed-bad-count-refusal",
    "packed-noncanonical-density-refusal", "packed-truncated-payload-refusal",
    "float-dense-high-bits-refusal",
}
for label in packed_refusal_labels:
    row = read("refusals/" + label + ".json")
    assert row == proof["malformedPackedRefusals"][label]
    assert row["headUnchanged"] and row["rootUnchanged"] and row["logsUnchanged"]
    assert row["code"] == row["expectedCode"]

# Ensure the compressed report archive contains the full canonical slice set,
# packed/sparse refusal reports, and cross-process resume receipts.
report_archive = archive / "canonical-reports.tar.gz"
with tarfile.open(report_archive, "r:gz") as reports:
    names = set(reports.getnames())
    slices = [name for name in names if name.startswith("reports/") and "/slice-" in name and name.endswith(".json")]
    assert len(slices) >= proof["canonicalReceipts"]
    for quantum in (1, 7, 4096):
        world = "world-packed-array-oracle-q" + str(quantum)
        assert "reports/" + world + "/slice-%020d.json" % (read("heads/packed-array-oracle-" + ("q4096" if quantum == 4096 else "q" + str(quantum)) + ".json")["epoch"]) in names
    for label in packed_refusal_labels:
        member = "reports/world-packed-array-oracle-q1/" + label + ".json"
        item = json.load(reports.extractfile(member))
        assert item["headUnchanged"] and item["rootUnchanged"] and item["logsUnchanged"]

print(json.dumps({
    "result": "PASS",
    "profile": proof["profile"],
    "archivedFiles": len(manifest["files"]),
    "canonicalReceipts": proof["canonicalReceipts"],
    "packedOracleCells": len(expected),
    "q1Q7DirectEquivalent": True,
    "malformedPackedRefusals": len(packed_refusal_labels),
    "reportsTarSHA256": sha_file(report_archive),
}, indent=2))
