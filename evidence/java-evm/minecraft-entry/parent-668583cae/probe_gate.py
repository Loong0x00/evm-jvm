#!/usr/bin/env python3
"""Directly exercise the private scan through a disposable test-only wrapper."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if len(sys.argv) != 3:
    raise SystemExit("usage: probe_gate.py BUILD OUTPUT")
BUILD = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
assert BUILD.parent == ROOT / "build"
assert BUILD.name.startswith("java-diff-mc-packed-float-grouped-scan-build-")
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-packed-float-grouped-scan-probe-")
assert not OUT.exists(), "probe output is append-only"
NODE_MODULES = ROOT / "jvmevm/runtime/node_modules"
assert NODE_MODULES.is_dir()
ENV = {
    **os.environ,
    "TMPDIR": str(BUILD / "tmp"),
    "NODE_PATH": str(NODE_MODULES),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}
OUT.mkdir(parents=True)
started = time.monotonic()


def run(label, command):
    log = OUT / (label + ".log")
    with log.open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=ROOT, env=ENV,
                       stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=1200)


probe_dir = OUT / "test-only-engine"
probe_dir.mkdir(parents=True)
source = (BUILD / "candidate/engine/MCEntryInterpreter.sol").read_text()
assert source.rstrip().endswith("}")
wrapper = (HERE / "grouped_scan_probe.sol.txt").read_text()
source = source.rstrip()[:-1] + "\n" + wrapper + "}\n"
(probe_dir / "MCEntryInterpreter.sol").write_text(source)
build_js = (BUILD / "candidate/engine/build.js").read_text()
assert build_js.count("runtime.length/2>384*1024") == 1
(probe_dir / "build.js").write_text(build_js.replace("runtime.length/2>384*1024", "runtime.length/2>400*1024", 1))
run("probe-engine-build", ["node", probe_dir / "build.js"])
artifact = json.loads((probe_dir / "MCEntryInterpreter.json").read_text())
assert len(artifact["deployedBytecode"]) // 2 <= 400 * 1024
assert any(entry.get("name") == "groupedScanProbe" for entry in artifact["abi"])

source_path = HERE / "probe_driver.go"
binary = OUT / "grouped-scan-probe-driver"
run("probe-driver-build", ["go", "build", "-trimpath", "-o", binary, source_path])
run("probe-driver-vet", ["go", "vet", source_path])
summary_path = OUT / "summary.json"
run("probe-cases", [binary, probe_dir / "MCEntryInterpreter.runtime.hex", summary_path])
summary = json.loads(summary_path.read_text())
assert summary["result"] == "PASS" and summary["generatedOnly"]
assert summary["ordinaryExternalGas"] == 1_000_000_000
assert summary["successfulCases"] == 14 and summary["typedRefusalCases"] == 16
assert len(summary["cases"]) == 30
assert all(row["suppliedGas"] == 1_000_000_000 for row in summary["cases"])
report = {
    "result": "PASS",
    "generatedOnly": True,
    "testOnlyWrapper": "groupedScanProbe(uint64[]) inserted into a disposable engine source copy",
    "probeRuntimeBytes": len(artifact["deployedBytecode"]) // 2,
    "ordinaryExternalGas": 1_000_000_000,
    "elapsedSeconds": time.monotonic() - started,
    "successCases": summary["successfulCases"],
    "typedRefusalCases": summary["typedRefusalCases"],
    "caseSummary": [
        {key: row[key] for key in ("name", "length", "expectedCount", "actualCount", "expectedPacked", "packed", "expectedSparse", "sparse", "error", "errorCode", "errorRef") if key in row}
        for row in summary["cases"]
    ],
}
(OUT / "gate.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({
    "result": report["result"],
    "probeRuntimeBytes": report["probeRuntimeBytes"],
    "successCases": report["successCases"],
    "typedRefusalCases": report["typedRefusalCases"],
    "elapsedSeconds": report["elapsedSeconds"],
    "output": str(OUT.relative_to(ROOT)),
}, indent=2))
