#!/usr/bin/env python3
"""Archive generated-only P27 raw75 evidence and recheck public receipts."""
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
PARENT = ROOT / "evidence/java-evm/minecraft-entry/parent-raw74-byte518516"
if len(sys.argv) != 5:
    raise SystemExit("usage: archive.py BUILD_DIR FIXTURE_DIR GATE_DIR RESULTS_DIR")
BUILD, FIXTURES, GATE, OUT = (Path(x).resolve() for x in sys.argv[1:])
assert all(p.parent == ROOT / "build" for p in (BUILD, FIXTURES, GATE))
assert BUILD.name.startswith("java-diff-mc-raw75-byte531965-build-")
assert FIXTURES.name.startswith("java-diff-mc-raw75-byte531965-fixtures-")
assert GATE.name.startswith("java-diff-mc-raw75-byte531965-gate-")
assert OUT.parent == STAGE / "results" and not OUT.exists()

pins = json.loads((BUILD / "pins.json").read_text())
fixtures = json.loads((FIXTURES / "fixtures.json").read_text())
summary = json.loads((GATE / "summary.json").read_text())
assert pins["profile"] == "MC-RANDOM-CLASS-P27-RAW75-BYTE531965"
assert pins["rawLimits"] == [75, 531965] and pins["bootstrapCount"] == 97
assert pins["bootstrapRoot"] == "70b6401e629c75ad213efb8b6bf484cb3f364dc9a281031c4651069bd3776ec4"
assert pins["engine"]["bytes"] <= 393216 and fixtures["hostGuestExecution"] is False
assert summary["status"] == "generated-local-gates-passed"
assert summary["wholeGateWallSeconds"] <= 1200 and summary["ordinaryGas"] == 1000000000
assert summary["driverRaw76Guard"]["worldAbsent"] is True
assert summary["coordinatorRaw76"]["rootUnchanged"] is True
assert summary["engineRefusals"]["raw76"]["error"] == "LinkError"
assert summary["engineRefusals"]["bytes531966"]["detail"] == 531966
assert summary["worlds"]["raw75"][0]["rawCount"] == 75
assert summary["worlds"]["raw75"][1]["verifiedReopen"] is True
assert summary["directEngineRaw75"]["status"] == "positive-terminal"
assert summary["engineExact531965"]["status"] == "positive-terminal"
assert summary["coordinatorByteWitnesses"]["531965"]["status"] == "constructor-positive"
assert summary["coordinatorByteWitnesses"]["531966"]["rootUnchanged"] is True
for total in (531965, 531966):
    assert fixtures["byteWitnesses"][str(total)]["totalClassBytes"] == total

OUT.mkdir(parents=True)
(OUT / "worlds").mkdir()
(OUT / "probes").mkdir()
(OUT / "sources").mkdir()
(OUT / "artifacts/engine").mkdir(parents=True)
(OUT / "artifacts/coordinator").mkdir(parents=True)
shutil.copyfile(BUILD / "pins.json", OUT / "build-pins.json")
shutil.copyfile(BUILD / "source-audit.json", OUT / "source-audit.json")
shutil.copyfile(FIXTURES / "fixtures.json", OUT / "fixture-manifest.json")
summary["buildPins"] = "build-pins.json"
summary["fixturePins"] = "fixture-manifest.json"
(OUT / "gate-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
shutil.copyfile(GATE / "receipt-verification.json", OUT / "receipt-verification.json")

# Preserve reproducible source inputs plus compact compiler outputs and the full
# ABI/storage-layout records. No class ZIP or parent/original payload is copied.
base_source_paths = [
    STAGE / "engine/MCEntryInterpreter.sol", STAGE / "engine/build.js",
    STAGE / "coordinator/MCEntryCoordinator.sol", STAGE / "coordinator/build.js",
    STAGE / "tools/build.py", STAGE / "tools/generate_fixtures.py",
    STAGE / "tools/gate.py", STAGE / "tools/checkpoint_diagnostic.py",
    STAGE / "tools/verify_receipts.js", STAGE / "tools/archive.py",
    *sorted((STAGE / "fixtures/java/generated").glob("*.java")),
    PARENT / "artifacts/engine/MCEntryInterpreter.sol",
    PARENT / "artifacts/engine/build.js",
    PARENT / "artifacts/coordinator/MCEntryCoordinator.sol",
    PARENT / "artifacts/coordinator/build.js",
    PARENT / "artifacts/parent-build-pins.json",
    PARENT / "generated-probe-driver.go.txt",
]
source_files = {}
for path in base_source_paths:
    rel = path.relative_to(ROOT).as_posix()
    data = path.read_bytes()
    source_files[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

for name in ("engine", "coordinator"):
    source = STAGE / name
    target = OUT / "artifacts" / name
    for filename in (
        "MCEntryInterpreter.sol" if name == "engine" else "MCEntryCoordinator.sol",
        "build.js",
        "MCEntryInterpreter.json" if name == "engine" else "MCEntryCoordinator.json",
        "MCEntryInterpreter.abi.json" if name == "engine" else "MCEntryCoordinator.abi.json",
        "MCEntryInterpreter.init.hex" if name == "engine" else "MCEntryCoordinator.init.hex",
        "MCEntryInterpreter.runtime.hex" if name == "engine" else "MCEntryCoordinator.runtime.hex",
    ):
        src = source / filename if filename in ("build.js", "MCEntryInterpreter.sol", "MCEntryCoordinator.sol") else BUILD / name / filename
        if not src.is_file():
            continue
        dst = target / filename
        shutil.copyfile(src, dst)
        data = dst.read_bytes()
        source_files[dst.relative_to(OUT).as_posix()] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

shutil.copyfile(BUILD / "driver.go", OUT / "sources/generated-driver.go")
source_files["sources/generated-driver.go"] = {
    "bytes": (OUT / "sources/generated-driver.go").stat().st_size,
    "sha256": hashlib.sha256((OUT / "sources/generated-driver.go").read_bytes()).hexdigest(),
}
(OUT / "source-manifest.json").write_text(json.dumps({
    "basis": "exact accepted P27 raw74 source plus explicit raw75/531965 envelope amendments",
    "candidateAndReadOnlyBaselineFiles": source_files,
    "generatedDriverTemplate": {
        "path": "evidence/java-evm/minecraft-entry/parent-raw74-byte518516/generated-probe-driver.go.txt",
        "sha256": pins["driverTemplateSHA256"],
        "candidatePath": "sources/generated-driver.go",
        "candidateSHA256": pins["driverSHA256"],
    },
    "generatedInputPayloads": "Only hashes/manifests retained; regenerated from tracked Java fixture sources.",
}, indent=2) + "\n")

# Archive successful public receipt chains and their opaque generated-fixture
# MR01 checkpoints, checking the report hash before each copy.
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

probe_files = {
    "engine-direct-raw75.json": GATE / "engine-direct-raw75/engine-direct-raw75.json",
    "engine-byte-531965.json": GATE / "engine-byte-531965/engine-byte-531965.json",
    "coordinator-raw76.json": GATE / "worlds/reports/coordinator-raw76/coordinator-raw76.json",
    "coordinator-byte-531965.json": GATE / "worlds/coordinator-byte-531965/coordinator-byte-531965.json",
    "coordinator-byte-531966.json": GATE / "worlds/reports/coordinator-byte-531966/coordinator-byte-531966.json",
    "engine-raw76.json": GATE / "engine-raw76/engine-probe.json",
    "engine-bytes531966.json": GATE / "engine-bytes531966/engine-probe.json",
    "engine-jvm65537.json": GATE / "engine-jvm65537/engine-probe.json",
    "engine-jvm0.json": GATE / "engine-jvm0/engine-probe.json",
    "engine-internal0.json": GATE / "engine-internal0/engine-probe.json",
    "engine-internal4097.json": GATE / "engine-internal4097/engine-probe.json",
    "driver-raw76-guard.json": GATE / "logs/driver-raw76-guard.json",
    "driver-raw76-guard.log": GATE / "logs/driver-raw76-guard.log",
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
    "GOTOOLCHAIN": "local",
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
    "scope": "generated-only P27 raw75/531965 envelope gate; no original Java/Minecraft execution",
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
