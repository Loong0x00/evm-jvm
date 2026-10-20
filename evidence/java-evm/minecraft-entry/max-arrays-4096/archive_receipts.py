#!/usr/bin/env python3
"""Archive hashes/counters for generated candidate receipts without checkpoint blobs."""
from pathlib import Path
import gzip
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ARTIFACTS = HERE / "artifacts"
capacity_dir = Path(sys.argv[1]).resolve()
retained_dir = Path(sys.argv[2]).resolve()
output_path = Path(sys.argv[3]).resolve()
assert len(sys.argv) == 4
assert capacity_dir.parent == retained_dir.parent == ROOT / "build"
assert output_path.parent == ARTIFACTS and output_path.name.startswith("ordered-receipt-hashes-")
assert output_path.name.endswith(".json.gz")
assert not output_path.exists(), "never overwrite a prior evidence run"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect(path: Path) -> dict:
    summary_path = path / "summary.json"
    summary_bytes = summary_path.read_bytes()
    summary = json.loads(summary_bytes)
    worlds = summary["canonicalReceipts"]["summary"]
    all_worlds = []
    count = 0
    for world_name, expected in sorted(worlds.items()):
        world = path / world_name
        report_dir = path / "reports" / world_name
        head = json.loads((world / "durable-head.json").read_text())
        rows = []
        for receipt_path in sorted(report_dir.glob("slice-*.json")):
            raw = receipt_path.read_bytes()
            row = json.loads(raw)
            assert row["epoch"] == len(rows) + 1
            assert row["checkpointSHA256"]
            rows.append({
                "epoch": row["epoch"],
                "receiptSHA256": sha(raw),
                "checkpointSHA256": row["checkpointSHA256"],
                "machineStateRoot": row["slice"]["machineStateRoot"],
                "lifecycle": row["slice"]["lifecycle"],
                "javaKind": row["slice"]["javaKind"],
                "jvmSteps": row["slice"]["totalJvmSteps"],
                "internalSteps": row["slice"]["totalInternalSteps"],
                "suppliedGas": row["suppliedGas"],
                "executionBudget": row.get("executionBudget"),
                "gasUsed": row["gasUsed"],
                "elapsedMS": row["elapsedMS"],
            })
        assert len(rows) == expected["receipts"] == head["epoch"]
        assert rows[-1]["checkpointSHA256"] == head["checkpointSHA256"]
        assert rows[-1]["lifecycle"] == head["lifecycle"]
        count += len(rows)
        all_worlds.append({
            "world": world_name,
            "receipts": rows,
            "final": {
                "epoch": head["epoch"],
                "jvmSteps": head["jvmSteps"],
                "internalSteps": head["internalSteps"],
                "lifecycle": head["lifecycle"],
                "javaKind": head["javaKind"],
                "machineRoot": head["machineRoot"],
                "checkpointSHA256": head["checkpointSHA256"],
            },
        })
    assert count == summary["canonicalReceipts"]["verifiedReceipts"]
    return {"summarySHA256": sha(summary_bytes), "verifiedReceipts": count,
            "canonicalWorlds": len(all_worlds), "worlds": all_worlds}


capacity = collect(capacity_dir)
retained = collect(retained_dir)
report = {
    "schema": 1,
    "scope": "generated candidate successful public receipt hashes and counters; no checkpoint or world bytes",
    "capacityPreflight": capacity,
    "retainedGate": retained,
}
ARTIFACTS.mkdir(exist_ok=True)
with output_path.open("wb") as stream:
    with gzip.GzipFile(filename="", fileobj=stream, mode="wb", compresslevel=9, mtime=0) as compressed:
        compressed.write((json.dumps(report, indent=2) + "\n").encode("utf-8"))
print(json.dumps({"path": str(output_path), "capacityReceipts": capacity["verifiedReceipts"],
                  "retainedReceipts": retained["verifiedReceipts"],
                  "capacityWorlds": capacity["canonicalWorlds"],
                  "retainedWorlds": retained["canonicalWorlds"],
                  "sha256": sha(output_path.read_bytes())}, indent=2))
