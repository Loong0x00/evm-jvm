#!/usr/bin/env python3
"""Archive generated-only raw74 evidence and independently recheck public receipts."""
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
assert BUILD.name.startswith("java-diff-mc-raw74-byte518516-build-")
assert FIXTURES.name.startswith("java-diff-mc-raw74-byte518516-fixtures-")
assert GATE.name.startswith("java-diff-mc-raw74-byte518516-gate-")
assert OUT.parent == STAGE / "results" and not OUT.exists()

pins = json.loads((BUILD / "pins.json").read_text())
fixtures = json.loads((FIXTURES / "fixtures.json").read_text())
summary = json.loads((GATE / "summary.json").read_text())
assert pins["profile"] == "MC-RANDOM-CLASS-P26-RAW74-BYTE518516"
assert pins["rawLimits"] == [74, 518516] and pins["bootstrapCount"] == 97
assert pins["bootstrapRoot"] == "9badb7b2e5fd2990b0285dcad078f36955841cc091e7f2eeb07f8401fbfb694d"
assert pins["engine"]["bytes"] <= 393216
assert fixtures["hostGuestExecution"] is False
assert summary["status"] == "generated-local-gates-passed"
assert summary["wholeGateWallSeconds"] <= 1200 and summary["ordinaryGas"] == 1_000_000_000
assert summary["driverRaw75Guard"]["worldAbsent"] is True
assert summary["coordinatorRaw75"]["rootUnchanged"] is True
assert summary["engineRefusals"]["raw75"]["error"] == "LinkError"

OUT.mkdir(parents=True)
(OUT / "worlds").mkdir()
(OUT / "probes").mkdir()
(OUT / "sources").mkdir()
shutil.copyfile(BUILD / "pins.json", OUT / "build-pins.json")
shutil.copyfile(BUILD / "source-audit.json", OUT / "source-audit.json")
shutil.copyfile(FIXTURES / "fixtures.json", OUT / "fixture-manifest.json")
shutil.copyfile(BUILD / "driver.go", OUT / "sources/generated-driver.go")
summary["buildPins"] = "build-pins.json"
summary["fixturePins"] = "fixture-manifest.json"
(OUT / "gate-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
shutil.copyfile(GATE / "receipt-verification.json", OUT / "receipt-verification.json")

# Record candidate and accepted-parent source hashes without copying original
# resources, class bundles, durable LevelDB worlds, or any original checkpoints.
base = ROOT / "evidence/java-evm/minecraft-entry/parent-raw73-byte516040"
source_paths = [
    STAGE / "engine/MCEntryInterpreter.sol", STAGE / "engine/build.js",
    STAGE / "coordinator/MCEntryCoordinator.sol", STAGE / "coordinator/build.js",
    STAGE / "tools/build.py", STAGE / "tools/generate_fixtures.py",
    STAGE / "tools/gate.py", STAGE / "tools/checkpoint_diagnostic.py",
    STAGE / "tools/verify_receipts.js", STAGE / "tools/archive.py",
    *sorted((STAGE / "fixtures/java/generated").glob("*.java")),
    base / "artifacts/engine/MCEntryInterpreter.sol",
    base / "artifacts/engine/build.js",
    base / "artifacts/coordinator/MCEntryCoordinator.sol",
    base / "artifacts/coordinator/build.js",
    base / "generated-probe-driver.go.txt",
]
files = {}
for path in source_paths:
    rel = path.relative_to(ROOT).as_posix()
    data = path.read_bytes()
    files[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
(OUT / "source-manifest.json").write_text(json.dumps({
    "basis": "exact accepted P26 raw73 source plus explicit raw74 envelope amendments",
    "candidateAndReadOnlyBaselineFiles": files,
    "generatedDriver": {
        "path": "sources/generated-driver.go",
        "bytes": (OUT / "sources/generated-driver.go").stat().st_size,
        "sha256": hashlib.sha256((OUT / "sources/generated-driver.go").read_bytes()).hexdigest(),
    },
}, indent=2) + "\n")

# Archive successful public receipts and opaque MR01 checkpoint blobs only for
# generated Java-8 fixtures. Each copied blob is checked against both its report
# SHA-256 and the durable head; no host-side Java/class evaluation occurs.
labels = []
for group in summary["worlds"].values():
    labels.extend(row["label"] for row in group)
labels.extend(("quantum-loop-q4096", "quantum-loop-q65536"))
for label in labels:
    src = GATE / "worlds" / label
    dst = OUT / "worlds" / label
    (dst / "checkpoints").mkdir(parents=True)
    shutil.copyfile(src / "durable-head.json", dst / "durable-head.json")
    src_reports = GATE / "worlds/reports" / label
    dst_reports = OUT / "worlds/reports" / label
    dst_reports.mkdir(parents=True)
    reports = sorted(src_reports.glob("slice-*.json"))
    assert reports, label
    for report in reports:
        row = json.loads(report.read_text())
        cp_src = src / "checkpoints" / (row["checkpointSHA256"] + ".bin")
        blob = cp_src.read_bytes()
        assert hashlib.sha256(blob).hexdigest() == row["checkpointSHA256"]
        shutil.copyfile(cp_src, dst / "checkpoints" / cp_src.name)
        shutil.copyfile(report, dst_reports / report.name)

# Preserve atomic refusal/success boundary evidence and the driver-side refusal.
probe_files = {
    "engine-direct-raw74.json": GATE / "engine-direct-raw74/engine-direct-raw74.json",
    "engine-byte-518516.json": GATE / "engine-byte-518516/engine-byte-518516.json",
    "coordinator-raw75.json": GATE / "worlds/reports/coordinator-raw75/coordinator-raw75.json",
    "coordinator-byte-518516.json": GATE / "worlds/coordinator-byte-518516/coordinator-byte-518516.json",
    "coordinator-byte-518517.json": GATE / "worlds/reports/coordinator-byte-518517/coordinator-byte-518517.json",
    "engine-raw75.json": GATE / "engine-raw75/engine-probe.json",
    "engine-bytes518517.json": GATE / "engine-bytes518517/engine-probe.json",
    "engine-jvm65537.json": GATE / "engine-jvm65537/engine-probe.json",
    "engine-jvm0.json": GATE / "engine-jvm0/engine-probe.json",
    "engine-internal0.json": GATE / "engine-internal0/engine-probe.json",
    "engine-internal4097.json": GATE / "engine-internal4097/engine-probe.json",
    "driver-raw75-guard.json": GATE / "logs/driver-raw75-guard.json",
    "driver-raw75-guard.log": GATE / "logs/driver-raw75-guard.log",
}
for name, source in probe_files.items():
    assert source.is_file(), source
    shutil.copyfile(source, OUT / "probes" / name)

# Re-run the independent ABI/event/read-range verifier over archived receipts.
(OUT / "build").mkdir()
shutil.copyfile(OUT / "build-pins.json", OUT / "build/pins.json")
verify_env = {
    **os.environ,
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "npm_config_offline": "true",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}
verified = subprocess.run(
    ["node", str(STAGE / "tools/verify_receipts.js"), str(OUT / "build"),
     str(OUT / "worlds"), "1", *labels],
    cwd=ROOT, env=verify_env, text=True, capture_output=True,
    timeout=120, check=True)
(OUT / "archived-receipt-verification.json").write_text(verified.stdout)
assert json.loads(verified.stdout) == json.loads((OUT / "receipt-verification.json").read_text())

manifest_files = {}
for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
    rel = path.relative_to(OUT).as_posix()
    data = path.read_bytes()
    manifest_files[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
(OUT / "archive-manifest.json").write_text(json.dumps({
    "schema": 1,
    "scope": "generated-only P26 raw74/518516 envelope gate; no original Java/Minecraft execution",
    "sourceBuild": BUILD.name,
    "sourceFixtures": FIXTURES.name,
    "sourceGate": GATE.name,
    "publicReceiptLabels": labels,
    "verifiedPublicReceipts": json.loads(verified.stdout)["verifiedReceipts"],
    "allArchivedPublicReceiptsReverified": True,
    "files": manifest_files,
}, indent=2) + "\n")
lines = []
for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
    lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(OUT).as_posix()}")
(OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(json.dumps({"archive": str(OUT), "publicReceiptChains": len(labels),
                  "reverifiedReceipts": json.loads(verified.stdout)["verifiedReceipts"],
                  "files": len(lines), "bytes": sum(x["bytes"] for x in manifest_files.values())}, indent=2))
