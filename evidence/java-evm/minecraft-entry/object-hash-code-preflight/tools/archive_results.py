#!/usr/bin/env python3
"""Archive hashes/results for one passed generated-only P12 Object gate.

The inputs are disposable generated fixture/world outputs under build/. The
tracked result index retains hashes and receipt metadata, never class/resource,
checkpoint, or world payload bytes.
"""
from pathlib import Path
import gzip
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 4, "archive_results.py BUILD_DIR FIXTURES_DIR GATE_DIR"
build, fixtures, gate = (Path(arg).resolve() for arg in sys.argv[1:])
for path, prefix in (
    (build, "java-diff-mc-object-hash-code-build-"),
    (fixtures, "java-diff-mc-object-hash-code-fixtures-"),
    (gate, "java-diff-mc-object-hash-code-gate-"),
):
    assert path.parent == root / "build" and path.name.startswith(prefix)


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()

pins = read(build / "pins.json")
fixture_manifest = read(fixtures / "summary.json")
summary = read(gate / "summary.json")
assert summary["profile"] == "MC-RANDOM-CLASS-P12-OBJECT-HASH-CODE"
assert summary["generatedOnly"] is True and summary["wholeGateSeconds"] < 1200
assert summary["bootstrapRoot"] == pins["bootstrapRoot"]
assert summary["engineBytes"] == pins["engine"]["bytes"] <= 393216
assert summary["changedBootstrapIndices"] == [0]
assert summary["unchangedOtherBootstrapImages"] == 96
assert fixture_manifest["generatedOnly"] is True and fixture_manifest["bootstrapCount"] == 97
assert fixture_manifest["rawLimits"] == [71, 471911]
assert summary["canonicalReceipts"]["verifiedReceipts"] > 0

receipt_index = {
    "schema": 1,
    "profile": summary["profile"],
    "generatedOnly": True,
    "bootstrapRoot": pins["bootstrapRoot"],
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "coordinatorRuntimeKeccak256": pins["coordinator"]["runtimeKeccak256"],
    "ordinaryGas": pins["ordinaryGas"],
    "worlds": [],
}
actual_total = 0
for name, expected in summary["canonicalReceipts"]["summary"].items():
    world = gate / name
    head = read(world / "durable-head.json")
    report_dir = gate / "reports" / name
    receipt_paths = sorted(report_dir.glob("slice-*.json"))
    assert len(receipt_paths) == expected["receipts"] == head["epoch"], (name, len(receipt_paths), expected, head)
    rows = []
    total_jvm = total_internal = 0
    for epoch, receipt_path in enumerate(receipt_paths, 1):
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        cp_sha = receipt["checkpointSHA256"]
        cp_path = world / "checkpoints" / (cp_sha + ".bin")
        cp_bytes = cp_path.read_bytes()
        assert sha(cp_bytes) == cp_sha and len(cp_bytes) == receipt["checkpointBytes"]
        body = receipt["slice"]
        assert receipt["epoch"] == body["epoch"] == epoch
        assert body["schema"] == 1 and body["result"] == 0
        total_jvm = body["totalJvmSteps"]
        total_internal = body["totalInternalSteps"]
        rows.append({
            "epoch": epoch,
            "receiptSHA256": sha(receipt_bytes),
            "checkpointSHA256": cp_sha,
            "checkpointBytes": len(cp_bytes),
            "checkpointRoot": body["checkpointRoot"],
            "machineStateRoot": body["machineStateRoot"],
            "lifecycle": body["lifecycle"],
            "outcome": body["outcome"],
            "javaKind": body["javaKind"],
            "totalJvmSteps": body["totalJvmSteps"],
            "totalInternalSteps": body["totalInternalSteps"],
            "executedJvmSteps": body["executedJvmSteps"],
            "executedInternalSteps": body["executedInternalSteps"],
            "gasUsed": receipt["gasUsed"],
            "elapsedMS": receipt["elapsedMS"],
        })
    assert total_jvm == head["jvmSteps"] == expected["java"]
    assert total_internal == head["internalSteps"] == expected["internal"]
    assert rows[-1]["checkpointSHA256"] == head["checkpointSHA256"]
    assert rows[-1]["machineStateRoot"] == head["machineRoot"]
    fixture_label = name.removeprefix("world-").rsplit("-q", 1)[0]
    fixture = read(fixtures / (fixture_label + ".json"))
    actual_total += len(rows)
    receipt_index["worlds"].append({
        "world": name,
        "quantum": int(name.rsplit("-q", 1)[1]),
        "fixture": fixture_label,
        "fixtureZipSHA256": fixture["zipSHA256"],
        "rawClassCount": fixture["bindingCount"],
        "totalClassBytes": fixture["totalClassBytes"],
        "receipts": rows,
    })
assert actual_total == summary["canonicalReceipts"]["verifiedReceipts"]

results = stage / "results"
results.mkdir(exist_ok=True)
# Keep complete machine-readable summaries, gzip-compressed with fixed mtime.
full_summary = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
full_summary_gz = gzip.compress(full_summary, compresslevel=9, mtime=0)
(results / "gate-summary.json.gz").write_bytes(full_summary_gz)
receipt_bytes = json.dumps(receipt_index, sort_keys=True, separators=(",", ":")).encode()
receipt_gz = gzip.compress(receipt_bytes, compresslevel=9, mtime=0)
(results / "verified-receipt-index.json.gz").write_bytes(receipt_gz)
(results / "canonical-receipts.json").write_text(json.dumps(
    summary["canonicalReceipts"], indent=2, sort_keys=True) + "\n")
(results / "fixture-manifest.json").write_text(json.dumps(
    fixture_manifest, indent=2, sort_keys=True) + "\n")
(results / "q120-test-only-model.json").write_text(json.dumps(
    read(gate / "q120-test-only-model.json"), indent=2, sort_keys=True) + "\n")

archive_index = {
    "result": "PASS",
    "profile": summary["profile"],
    "gateSeconds": summary["wholeGateSeconds"],
    "runtimeBytes": summary["engineBytes"],
    "runtimeCapBytes": summary["engineCapBytes"],
    "bootstrapRoot": summary["bootstrapRoot"],
    "objectImageSHA256": pins["object"]["sha256"],
    "objectImageKeccak256": pins["object"]["keccak256"],
    "globalNativeBindings": summary["globalNativeBindings"],
    "stringLocalBinding": summary["stringLocalBinding"],
    "rawLimits": summary["rawLimits"],
    "canonicalReceipts": actual_total,
    "receiptWorlds": len(receipt_index["worlds"]),
    "fullGateSummaryGzipSHA256": sha(full_summary_gz),
    "fullGateSummaryGzipBytes": len(full_summary_gz),
    "verifiedReceiptIndexGzipSHA256": sha(receipt_gz),
    "verifiedReceiptIndexGzipBytes": len(receipt_gz),
    "canonicalReceiptSummarySHA256": sha((results / "canonical-receipts.json").read_bytes()),
    "fixtureManifestSHA256": sha((results / "fixture-manifest.json").read_bytes()),
    "q120TestOnlyModelSHA256": sha((results / "q120-test-only-model.json").read_bytes()),
    "generatedOnly": True,
    "originalProgramInputs": False,
}
(results / "archive-index.json").write_text(json.dumps(archive_index, indent=2, sort_keys=True) + "\n")
print(json.dumps(archive_index, indent=2, sort_keys=True))
