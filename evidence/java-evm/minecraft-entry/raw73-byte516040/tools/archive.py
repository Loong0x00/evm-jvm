#!/usr/bin/env python3
"""Archive generated-only raw73 evidence and independently recheck public receipts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parents[3]
if len(sys.argv) != 5:
    raise SystemExit("usage: archive.py BUILD_DIR FIXTURE_DIR GATE_DIR RESULTS_DIR")
BUILD, FIXTURES, GATE, OUT = (Path(x).resolve() for x in sys.argv[1:])
assert all(p.parent == ROOT / "build" for p in (BUILD, FIXTURES, GATE))
assert BUILD.name.startswith("java-diff-mc-raw73-byte516040-build-")
assert FIXTURES.name.startswith("java-diff-mc-raw73-byte516040-fixtures-")
assert GATE.name.startswith("java-diff-mc-raw73-byte516040-gate-")
assert OUT.parent == STAGE / "results" and not OUT.exists()

pins = json.loads((BUILD / "pins.json").read_text())
fixtures = json.loads((FIXTURES / "fixtures.json").read_text())
summary = json.loads((GATE / "summary.json").read_text())
assert pins["rawLimits"] == [73, 516040] and pins["bootstrapCount"] == 97
assert pins["bootstrapRoot"] == "60d5d3b5d4ecaf68427aa6bba3dcb3084e04b64f09b5d155d2f651746aeb875e"
assert pins["engine"]["bytes"] <= 393216
assert fixtures["hostGuestExecution"] is False
assert summary["status"] == "generated-local-gates-passed"
assert summary["wholeGateWallSeconds"] <= 1200 and summary["ordinaryGas"] == 1_000_000_000

OUT.mkdir(parents=True)
(OUT / "worlds").mkdir()
(OUT / "probes").mkdir()
shutil.copyfile(BUILD / "pins.json", OUT / "build-pins.json")
shutil.copyfile(BUILD / "source-audit.json", OUT / "source-audit.json")
shutil.copyfile(FIXTURES / "fixtures.json", OUT / "fixture-manifest.json")
source_paths = [
    STAGE / "engine/MCEntryInterpreter.sol", STAGE / "engine/build.js",
    STAGE / "coordinator/MCEntryCoordinator.sol", STAGE / "coordinator/build.js",
    STAGE / "driver.go", STAGE / "tools/build.py", STAGE / "tools/generate_fixtures.py",
    STAGE / "tools/gate.py", STAGE / "tools/checkpoint_diagnostic.py",
    STAGE / "tools/verify_receipts.js", STAGE / "tools/archive.py",
    *sorted((STAGE / "fixtures/java/generated").glob("*.java")),
]
source_manifest = {
    path.relative_to(STAGE).as_posix(): {
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    for path in source_paths
}
(OUT / "source-manifest.json").write_text(json.dumps({
    "basis": "Git-tracked scoped raw73-byte516040 candidate sources",
    "files": source_manifest,
}, indent=2) + "\n")
summary["buildPins"] = "build-pins.json"
summary["fixturePins"] = "fixture-manifest.json"
(OUT / "gate-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
shutil.copyfile(GATE / "receipt-verification.json", OUT / "receipt-verification.json")

# Preserve successful public receipts, durable heads, and their tiny MR01 blobs;
# no LevelDB world, source class bundle, original-JAR input, or host state is copied.
labels = []
for group in summary["worlds"].values():
    labels.extend(row["label"] for row in group)
labels.extend(("quantum-loop-q4096", "quantum-loop-q65536"))
for label in labels:
    source_world = GATE / "worlds" / label
    dest_world = OUT / "worlds" / label
    (dest_world / "checkpoints").mkdir(parents=True)
    shutil.copyfile(source_world / "durable-head.json", dest_world / "durable-head.json")
    src_reports = GATE / "worlds/reports" / label
    dst_reports = OUT / "worlds/reports" / label
    dst_reports.mkdir(parents=True)
    report_files = sorted(src_reports.glob("slice-*.json"))
    assert report_files
    for report in report_files:
        data = json.loads(report.read_text())
        cp_name = data["checkpointSHA256"] + ".bin"
        cp_src = source_world / "checkpoints" / cp_name
        cp_dst = dest_world / "checkpoints" / cp_name
        blob = cp_src.read_bytes()
        assert hashlib.sha256(blob).hexdigest() == data["checkpointSHA256"]
        shutil.copyfile(cp_src, cp_dst)
        shutil.copyfile(report, dst_reports / report.name)

# Retain direct-engine and typed failure/constructor boundary receipts.
probe_files = {
    "engine-direct-raw73.json": GATE / "engine-direct-raw73/engine-direct-raw73.json",
    "engine-byte-516040.json": GATE / "engine-byte-516040/engine-byte-516040.json",
    "coordinator-raw74.json": GATE / "worlds/reports/coordinator-raw74/coordinator-raw74.json",
    "coordinator-byte-516040.json": GATE / "worlds/coordinator-byte-516040/coordinator-byte-516040.json",
    "coordinator-byte-516041.json": GATE / "worlds/reports/coordinator-byte-516041/coordinator-byte-516041.json",
    "engine-raw74.json": GATE / "engine-raw74/engine-probe.json",
    "engine-bytes516041.json": GATE / "engine-bytes516041/engine-probe.json",
    "engine-jvm65537.json": GATE / "engine-jvm65537/engine-probe.json",
    "engine-jvm0.json": GATE / "engine-jvm0/engine-probe.json",
    "engine-internal0.json": GATE / "engine-internal0/engine-probe.json",
    "engine-internal4097.json": GATE / "engine-internal4097/engine-probe.json",
    "driver-raw74-guard.json": GATE / "logs/driver-raw74-guard.json",
    "driver-raw74-guard.log": GATE / "logs/driver-raw74-guard.log",
}
for name, source in probe_files.items():
    assert source.is_file(), source
    shutil.copyfile(source, OUT / "probes" / name)

# Re-run the independent ABI/event/read-range verifier against archived receipts.
(OUT / "build").mkdir()
shutil.copyfile(OUT / "build-pins.json", OUT / "build/pins.json")
verify_labels = labels
verify_env = {
    **os.environ,
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "npm_config_offline": "true",
}
verified = subprocess.run(
    ["node", str(STAGE / "tools/verify_receipts.js"), str(OUT / "build"),
     str(OUT / "worlds"), "1", *verify_labels],
    cwd=ROOT, env=verify_env, text=True, capture_output=True,
    timeout=120, check=True)
(OUT / "archived-receipt-verification.json").write_text(verified.stdout)
assert json.loads(verified.stdout) == json.loads((OUT / "receipt-verification.json").read_text())

files = {}
for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
    rel = path.relative_to(OUT).as_posix()
    data = path.read_bytes()
    files[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
(OUT / "archive-manifest.json").write_text(json.dumps({
    "schema": 1,
    "scope": "generated-only P25 raw73/516040 profile gate; no original Minecraft classes or inputs",
    "sourceBuild": BUILD.name,
    "sourceFixtures": FIXTURES.name,
    "sourceGate": GATE.name,
    "publicReceiptLabels": labels,
    "allArchivedPublicReceiptsReverified": True,
    "files": files,
}, indent=2) + "\n")

lines = []
for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  {path.relative_to(OUT).as_posix()}")
(OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(json.dumps({"archive": str(OUT), "publicReceiptChains": len(labels),
                  "reverifiedReceipts": json.loads(verified.stdout)["verifiedReceipts"],
                  "files": len(lines), "bytes": sum(x["bytes"] for x in files.values())}, indent=2))
