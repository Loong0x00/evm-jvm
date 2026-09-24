#!/usr/bin/env python3
"""Record measured generated checkpoint gas against freshly compiled P16."""
from pathlib import Path
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build, candidate_gate, baseline_replay = map(Path, sys.argv[1:4])
build = build.resolve(); candidate_gate = candidate_gate.resolve(); baseline_replay = baseline_replay.resolve()
run_id = candidate_gate.name.rsplit("-", 1)[-1]
report_path = stage / ("results/generated-gas-comparison-gate-" + run_id + ".json")
assert not report_path.exists(), "gas evidence is append-only"

rows = []
for label in ("packed-array-oracle", "array-savings-boundary", "sparse-array-stress"):
    for quantum in (1, 7, 4096):
        tag = "q" + str(quantum)
        reports = []
        for base in (baseline_replay, candidate_gate):
            report_dir = base / "reports" / ("world-" + label + "-" + tag)
            files = sorted(report_dir.glob("slice-*.json"))
            assert files
            samples = [json.loads(path.read_text()) for path in files]
            head = json.loads((base / ("world-" + label + "-" + tag) / "durable-head.json").read_text())
            assert len(samples) == head["epoch"]
            assert samples[-1]["checkpointSHA256"] == head["checkpointSHA256"]
            reports.append((samples, head))
        baseline, candidate = reports
        base_samples, base_head = baseline
        candidate_samples, candidate_head = candidate
        assert len(base_samples) == len(candidate_samples)
        for a, b in zip(base_samples, candidate_samples):
            assert a["epoch"] == b["epoch"]
            assert a["checkpointBytes"] == b["checkpointBytes"]
            assert a["slice"]["totalJvmSteps"] == b["slice"]["totalJvmSteps"]
            assert a["slice"]["totalInternalSteps"] == b["slice"]["totalInternalSteps"]
        for key in ("lifecycle", "outcome", "result", "jvmSteps", "internalSteps", "vfsRoot"):
            assert base_head[key] == candidate_head[key]
        base_last = base_samples[-1]
        candidate_last = candidate_samples[-1]
        saved = base_last["gasUsed"] - candidate_last["gasUsed"]
        rows.append({
            "fixture": label,
            "quantum": quantum,
            "successfulReceipts": len(base_samples),
            "terminalJvmSteps": candidate_head["jvmSteps"],
            "terminalInternalSteps": candidate_head["internalSteps"],
            "sameMR01LengthBytes": base_last["checkpointBytes"] - 280,
            "baselineTerminalGas": base_last["gasUsed"],
            "candidateTerminalGas": candidate_last["gasUsed"],
            "gasSaved": saved,
            "gasSavedBasisPoints": saved * 10000 // base_last["gasUsed"],
            "sameMR01SHA256": hashlib.sha256(
                (stage / ("results/opaque-equivalence-gate-" + run_id) / "baseline" /
                 (label + "-" + ("direct" if quantum == 4096 else "q" + str(quantum)) + ".mr01.bin")).read_bytes()
            ).hexdigest(),
            "checkpointSizeUnchanged": base_last["checkpointBytes"] == candidate_last["checkpointBytes"],
        })

report = {
    "result": "PASS",
    "generatedOnly": True,
    "baseline": "fresh accepted P16 engine/coordinator compile",
    "candidateRuntimeSHA256": json.loads((build / "pins.json").read_text())["engine"]["runtimeSHA256"],
    "note": "Each row compares the terminal successful EVM slice for identical generated input and quantum. MR01 checkpoint bytes and execution counters agree; gas change is the reserved-size single-scan path. These are bounded generated controls, not an original workload estimate.",
    "measurements": rows,
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"result": "PASS", "measurements": len(rows),
                  "largestSavedGas": max(row["gasSaved"] for row in rows),
                  "report": str(report_path.relative_to(root))}, indent=2))
