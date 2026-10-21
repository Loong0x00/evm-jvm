#!/usr/bin/env python3
"""Independent generated-only replay of the checkpoint-2m stage gate."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

H = Path(__file__).resolve().parent
STAGE = H.parent
BASE = STAGE.parent / "checkpoint-2m-base-p33"
ROOT = STAGE.parents[3]
build, fixtures, out = map(lambda p: Path(p).resolve(), sys.argv[1:4])
assert build.parent == fixtures.parent == out.parent == ROOT / "build"
assert build.is_dir() and not out.exists() and not fixtures.exists()
pins = json.loads((build / "pins.json").read_text())
assert pins["rawClassLimit"] == 150 and pins["rawByteLimit"] == 1063930
assert pins["bootstrapCount"] == 100 and pins["runtimeCapBytes"] == 1048576
assert pins["checkpointCapBytes"] == 2097152
out.mkdir()
(out / "tmp").mkdir()
env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
           TMPDIR=str(out / "tmp"), PYTHONDONTWRITEBYTECODE="1",
           NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
with (out / "fixtures.log").open("w") as log:
    subprocess.run([sys.executable, STAGE / "tools/generate_fixtures.py", fixtures],
                   cwd=ROOT, env=env, check=True, stdout=log,
                   stderr=subprocess.STDOUT, timeout=300)
tools = out / "tools"
tools.mkdir()
driver_bin = out / "generated-driver"
with (out / "driver-build.log").open("w") as log:
    subprocess.run(["go", "build", "-trimpath", "-o", driver_bin,
                    "./" + (STAGE / "tools").relative_to(ROOT).as_posix()],
                   cwd=ROOT, env=env, check=True, stdout=log,
                   stderr=subprocess.STDOUT, timeout=300)
spec = importlib.util.spec_from_file_location("checkpoint2m_run_gate", STAGE / "tools/run_gate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
started = time.monotonic()
result = module.run_attempt(
    1, 1_000_000_000, 1200, build_dir=build, fixture_dir=fixtures,
    driver_bin=driver_bin, engine_path=build / "engine/MCEntryInterpreter.json",
    coordinator_path=build / "coordinator/MCEntryCoordinator.json",
    legacy_engine_path=BASE / "engine/MCEntryInterpreter.json",
    legacy_coord_path=BASE / "coordinator/MCEntryCoordinator.json",
    attempt_dir=out / "attempt-1", env=env)
assert result["status"] == "passed" and result["gasBudget"] == 1_000_000_000
result["profile"] = pins["profile"]
result["actualGateSeconds"] = time.monotonic() - started
result["legacyP33Artifacts"] = {
    "engineRuntimeSHA256": json.loads((BASE / "p33-pins.json").read_text())["engine"]["runtimeSHA256"],
    "coordinatorRuntimeKeccak256": json.loads((BASE / "p33-pins.json").read_text())["coordinator"]["runtimeKeccak256"],
}
result["generatedOnly"] = True
(out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"profile": pins["profile"], "seconds": result["actualGateSeconds"],
                  "checkpoint2mSchedules": len([r for r in result["direct"]["schedules"]
                                                 if "checkpoint-2m-array-pair" in r["name"]]),
                  "coordinatorCheckpointBytes": result["coordinator"]["checkpointBytes"],
                  "reopenCount": result["reopen"]["reopenCount"]}, indent=2))
