#!/usr/bin/env python3
"""Archive hashes/results for one passed generated-only P15 Integer.rotateLeft gate.

The inputs are disposable generated fixture/world outputs under build/. The
tracked result index retains hashes and receipt metadata, never class/resource,
checkpoint, or world payload bytes.
"""
from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 4, "archive_results.py BUILD_DIR FIXTURES_DIR GATE_DIR"
build, fixtures, gate = (Path(arg).resolve() for arg in sys.argv[1:])
for path, prefix in (
    (build, "java-diff-mc-integer-rotate-left-build-"),
    (fixtures, "java-diff-mc-integer-rotate-left-fixtures-"),
    (gate, "java-diff-mc-integer-rotate-left-gate-"),
):
    assert path.parent == root / "build" and path.name.startswith(prefix)


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()

pins = read(build / "pins.json")
fixture_manifest = read(fixtures / "summary.json")
summary_path = gate / "summary.json"
summary_source_sha256 = sha(summary_path.read_bytes())
summary = read(summary_path)
assert summary["profile"] == "MC-RANDOM-CLASS-P15-INTEGER-ROTATE-LEFT"
assert summary["generatedOnly"] is True and summary["wholeGateSeconds"] < 1200
assert summary["bootstrapRoot"] == pins["bootstrapRoot"]
assert summary["engineBytes"] == pins["engine"]["bytes"] <= 393216
assert summary["changedBootstrapIndices"] == [70]
assert summary["unchangedOtherBootstrapImages"] == 96
assert fixture_manifest["generatedOnly"] is True and fixture_manifest["bootstrapCount"] == 97
assert fixture_manifest["rawLimits"] == [71, 471911]
rotate_fixture = read(fixtures / "integer-rotate-left.json")
rotate_count = len(rotate_fixture["rotateLeftVectors"])
assert summary["results"]["integer-rotate-left"]["oracleVectors"] == rotate_count
assert summary["canonicalReceipts"]["verifiedReceipts"] > 0
original_limitations = summary["limitations"]
summary["limitations"], replacements = re.subn(r"\d+(?= signed-int raw outputs)", str(rotate_count), original_limitations)
assert replacements in (0, 1)
summary_amendment = None
if summary["limitations"] != original_limitations:
    summary_amendment = {
        "schema": 1, "kind": "documentation-only generated summary correction",
        "sourceSummarySHA256": summary_source_sha256,
        "field": "limitations", "original": original_limitations,
        "corrected": summary["limitations"], "oracleVectorCount": rotate_count,
        "basis": "the same gate result records results.integer-rotate-left.oracleVectors and fixture integer-rotate-left.json; no execution, receipt, root, or timing data changed",
    }

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

run_label = gate.name.removeprefix("java-diff-mc-integer-rotate-left-gate-")
assert run_label and run_label != gate.name
results = stage / "results" / run_label
assert not results.exists(), "refusing to overwrite an archived gate run"
results.mkdir(parents=True)
# Keep complete machine-readable summaries, gzip-compressed with fixed mtime.
# Preserve the emitted summary separately when correcting its descriptive vector
# count from the independently recorded fixture count.
original_summary_gz = gzip.compress(summary_path.read_bytes(), compresslevel=9, mtime=0)
(results / "gate-summary-generated.json.gz").write_bytes(original_summary_gz)
full_summary = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
full_summary_gz = gzip.compress(full_summary, compresslevel=9, mtime=0)
(results / "gate-summary.json.gz").write_bytes(full_summary_gz)
if summary_amendment:
    (results / "summary-metadata-amendment.json").write_text(json.dumps(summary_amendment, indent=2) + "\n")
receipt_bytes = json.dumps(receipt_index, sort_keys=True, separators=(",", ":")).encode()
receipt_gz = gzip.compress(receipt_bytes, compresslevel=9, mtime=0)
(results / "verified-receipt-index.json.gz").write_bytes(receipt_gz)
(results / "canonical-receipts.json").write_text(json.dumps(
    summary["canonicalReceipts"], indent=2, sort_keys=True) + "\n")
(results / "fixture-manifest.json").write_text(json.dumps(
    fixture_manifest, indent=2, sort_keys=True) + "\n")
(results / "q120-test-only-model.json").write_text(json.dumps(
    read(gate / "q120-test-only-model.json"), indent=2, sort_keys=True) + "\n")
for name in ("build-pins.json", "root-commitment.json", "prechange-image-verification.json"):
    shutil.copy2(stage / name, results / name)
source_verification = read(build / "source-verification.log")
(results / "source-verification.json").write_text(json.dumps(source_verification, indent=2, sort_keys=True) + "\n")
rotation = summary["results"]["integer-rotate-left"]
rotation_receipts = summary["canonicalReceipts"]["summary"]
equivalence = {
    "schema": 1, "fixture": "integer-rotate-left", "fixtureZipSHA256": rotate_fixture["zipSHA256"],
    "vectors": rotate_count, "oracleSourceSHA256": rotate_fixture["oracleSourceSHA256"],
    "oracleOutputSHA256": rotate_fixture["oracleOutputSHA256"],
    "q1": {key: rotation["q1"][key] for key in ("world", "epoch", "jvmSteps", "internalSteps", "machineRoot", "opaquePayloadSHA256", "lifecycle")},
    "q7": {key: rotation["q7"][key] for key in ("world", "epoch", "jvmSteps", "internalSteps", "machineRoot", "opaquePayloadSHA256", "lifecycle")},
    "direct": {key: rotation["direct"][key] for key in ("world", "epoch", "jvmSteps", "internalSteps", "machineRoot", "opaquePayloadSHA256", "lifecycle")},
    "canonicalSuccessfulReceipts": {name: rotation_receipts[name]["receipts"] for name in ("world-integer-rotate-left-q1", "world-integer-rotate-left-q7", "world-integer-rotate-left-q4096")},
    "allOutputsMatchGeneratedJava8Oracle": True, "allChainsIncludeDurableReopen": True,
}
assert equivalence["q1"]["machineRoot"] == equivalence["q7"]["machineRoot"] == equivalence["direct"]["machineRoot"]
assert equivalence["q1"]["opaquePayloadSHA256"] == equivalence["q7"]["opaquePayloadSHA256"] == equivalence["direct"]["opaquePayloadSHA256"]
(results / "integer-rotate-left-equivalence.json").write_text(json.dumps(equivalence, indent=2, sort_keys=True) + "\n")
def compact_terminal_map(name):
    rows = summary["results"][name]
    keep = ("world", "epoch", "jvmSteps", "internalSteps", "machineRoot",
            "opaquePayloadSHA256", "lifecycle", "javaKind")
    return {quantum: {key: value[key] for key in keep if key in value}
            for quantum, value in rows.items() if isinstance(value, dict) and
            quantum in ("q1", "q7", "direct")}

retained_names = (
    "retained-string", "retained-map", "retained-integer", "retained-system-out-err",
    "retained-properties", "identity-hash", "object-hashcode-identity",
    "object-hashcode-null-caught", "object-hashcode-null-uncaught", "object-hashcode-smoke",
    "math-sqrt-binary64", "math-sin-bounded-edges", "math-sin-bounded-grid",
    "math-asin-bounded-edges", "math-cos-bounded-domain", "sparse-array-stress",
    "packed-array-oracle", "count-71",
)
retained = {
    "schema": 1, "profile": summary["profile"], "generatedOnly": True,
    "q1q7DirectReopenControls": {name: compact_terminal_map(name) for name in retained_names},
    "packed1024Q1Resume": summary["results"]["q1-packed-resume-from-successful-array-head"],
    "sparseOldWireAndMalformedRefusals": summary["results"]["sparse-malformed-refusals"],
    "packedMalformedRefusals": summary["results"]["packed-malformed-refusals"],
    "aggregate471911": {"classification": summary["results"]["byte-471911"]["classification"],
                         "allClassBytesRead": summary["results"]["byte-471911"]["allClassBytesRead"]},
    "aggregate471912": summary["results"]["byte-471912"],
}
(results / "retained-controls.json").write_text(json.dumps(retained, indent=2, sort_keys=True) + "\n")
build_receipt = {
    "schema": 1, "pins": pins["engine"], "coordinator": pins["coordinator"],
    "engineBuildLogSHA256": sha((build / "engine-build.log").read_bytes()),
    "coordinatorBuildLogSHA256": sha((build / "coordinator-build.log").read_bytes()),
    "sourceVerificationLogSHA256": sha((build / "source-verification.log").read_bytes()),
    "driverSourceSHA256": sha((build / "main.go").read_bytes()),
    "driverExecutableSHA256": sha((build / "driver").read_bytes()),
    "goBuildLogSHA256": sha((build / "go-build.log").read_bytes()),
    "goVetLogSHA256": sha((build / "go-vet.log").read_bytes()),
}
(results / "build-receipt.json").write_text(json.dumps(build_receipt, indent=2, sort_keys=True) + "\n")

archive_index = {
    "result": "PASS",
    "profile": summary["profile"],
    "gateSeconds": summary["wholeGateSeconds"],
    "runtimeBytes": summary["engineBytes"],
    "runtimeCapBytes": summary["engineCapBytes"],
    "bootstrapRoot": summary["bootstrapRoot"],
    "prechangeP14ImageByteMatch": True,
    "oracleVectors": rotate_count,
    "oracleSourceSHA256": rotate_fixture["oracleSourceSHA256"],
    "integerImageSHA256": pins["integer"]["sha256"],
    "integerImageKeccak256": pins["integer"]["keccak256"],
    "globalNativeBindings": summary["globalNativeBindings"],
    "stringLocalBinding": summary["stringLocalBinding"],
    "rawLimits": summary["rawLimits"],
    "canonicalReceipts": actual_total,
    "receiptWorlds": len(receipt_index["worlds"]),
    "emittedGateSummarySHA256": summary_source_sha256,
    "generatedGateSummaryGzipSHA256": sha(original_summary_gz),
    "fullGateSummaryGzipSHA256": sha(full_summary_gz),
    "fullGateSummaryGzipBytes": len(full_summary_gz),
    "summaryMetadataAmended": summary_amendment is not None,
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
