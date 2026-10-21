#!/usr/bin/env python3
"""Build and run generated-only P33 checkpoint-2m engine/coordinator EVM gates."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

STAGE = Path(__file__).resolve().parent.parent
BASE = STAGE.parent / "checkpoint-2m-base-p33"
ROOT = STAGE.parents[3]
INITIAL_GAS = 1_000_000_000
INITIAL_WALL_SECONDS = 1200
MAX_ATTEMPTS = 5


class GateFailure(RuntimeError):
    pass


class GasBudgetShortage(GateFailure):
    pass


class WallBudgetShortage(GateFailure):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_checked(command: list[str], *, cwd: Path, env: dict[str, str], log: Path,
                timeout: int) -> dict[str, object]:
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open("w") as stream:
        try:
            proc = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout)
            code, timed_out = proc.returncode, False
        except subprocess.TimeoutExpired:
            code, timed_out = -999, True
    return {"command": command, "exit": code, "timedOut": timed_out,
            "timeoutSeconds": timeout, "wallSeconds": round(time.monotonic() - started, 3),
            "log": str(log)}


def copy_if_present(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def preserve_attempt(archive: Path, attempt_dir: Path, row: dict[str, object],
                     reason: str, gas: int, wall: int) -> None:
    dest = archive / "attempts" / f"attempt-{row['attempt']}"
    dest.mkdir(parents=True, exist_ok=False)
    write_json(dest / "attempt.json", {"attempt": row["attempt"], "status": reason,
                                       "gasBudget": gas, "wallBudgetSeconds": wall,
                                       "error": row.get("error"), "commands": row.get("commands", [])})
    logs = attempt_dir / "logs"
    if logs.is_dir():
        shutil.copytree(logs, dest / "logs")
    for report_name in ("direct", "coordinator"):
        source = attempt_dir / report_name
        if not source.is_dir():
            continue
        for name in ("gate-failure.json", "gate-summary.json", "reopen-summary.json",
                     "coordinator-summary.json"):
            copy_if_present(source / name, dest / report_name / name)
        requests = source / "reopen-requests"
        if requests.is_dir():
            shutil.copytree(requests, dest / report_name / "reopen-requests")
        checkpoints = source / "checkpoints"
        if checkpoints.is_dir():
            for name in ("q1-identity-hash-map-matrix.checkpoint.bin", "q1-raw150.checkpoint.bin",
                         "q1-math-double-min-max-edges.checkpoint.bin", "q1-checkpoint-2m-array-pair.checkpoint.bin"):
                copy_if_present(checkpoints / name, dest / report_name / "checkpoints" / name)


def build_sources(run_id: str, env: dict[str, str], build_log_dir: Path):
    build_dir = ROOT / "build" / f"java-diff-mc-checkpoint-2m-build-{run_id}"
    fixture_dir = ROOT / "build" / f"java-diff-mc-checkpoint-2m-fixtures-{run_id}"
    coordinator_dir = build_dir / "coordinator"
    driver_bin = build_dir / "tools" / "evm_driver"
    if build_dir.exists() or fixture_dir.exists():
        raise GateFailure(f"refusing to overwrite fresh build path for {run_id}")

    build_row = run_checked([sys.executable, str(STAGE / "tools/build_candidate.py"), str(build_dir)],
                            cwd=ROOT, env=env, log=build_log_dir / "engine-build.log", timeout=900)
    if build_row["exit"] != 0 or build_row["timedOut"]:
        raise GateFailure(f"fresh engine build/source proof failed: {build_row}")
    engine_path = build_dir / "engine/MCEntryInterpreter.json"
    engine = json.loads(engine_path.read_text())
    engine_code = bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))
    pins = json.loads((STAGE / "pins.json").read_text())
    if pins["runtimeCapBytes"] != 1048576 or pins["checkpointCapBytes"] != 2097152:
        raise GateFailure("stage pins conflate or changed the runtime/checkpoint limits")
    if len(engine_code) != pins["engineRuntimeBytes"] or len(engine_code) > pins["runtimeCapBytes"]:
        raise GateFailure(f"fresh engine runtime size outside unchanged 1 MiB runtime artifact cap: {len(engine_code)}")
    if sha(engine_code) != pins["engineRuntimeSHA256"] or engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x") != pins["engineRuntimeKeccak256"]:
        raise GateFailure("fresh engine artifact runtime differs from stage pins")

    # build_candidate.py already copied and freshly compiled the paired coordinator.
    # Reuse that exact artifact rather than creating a second source directory.
    coordinator_source = (coordinator_dir / "MCEntryCoordinator.sol").read_text()
    match = re.search(r'ENGINE_CODEHASH\s*=\s*hex"([0-9a-fA-F]{64})"', coordinator_source)
    if not match or match.group(1).lower() != engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x").lower():
        raise GateFailure("coordinator does not bind the fresh engine codehash")
    coordinator = json.loads((coordinator_dir / "MCEntryCoordinator.json").read_text())
    coord_code = bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))
    if len(coord_code) != pins["coordinatorRuntimeBytes"] or len(coord_code) > 24576:
        raise GateFailure(f"coordinator runtime size mismatch: {len(coord_code)}")
    if (sha(coord_code) != coordinator["codeHashes"]["runtimeSHA256"] or
            coordinator["codeHashes"]["runtimeSHA256"] != pins["coordinatorRuntimeSHA256"] or
            coordinator["codeHashes"]["runtimeKeccak256"] != pins["coordinatorRuntimeKeccak256"] or
            sha((coordinator_dir / "MCEntryCoordinator.sol").read_bytes()) != pins["coordinatorSourceSHA256"]):
        raise GateFailure("coordinator artifact runtime/source differs from frozen stage pins")
    pair_pins = {
        "profile": "P33-checkpoint-2m-runtime1m-raw150-byte1063930",
        "engine": {"runtimeBytes": len(engine_code), **engine["codeHashes"]},
        "coordinator": {"runtimeBytes": len(coord_code), **coordinator["codeHashes"],
                        "sourceSHA256": sha((coordinator_dir / "MCEntryCoordinator.sol").read_bytes())},
        "constructorRawClassLimit": 150,
        "constructorRawByteLimit": 1063930,
        "maximumMR01DiagnosticClasses": 250,
        "bootstrapCount": 100,
        "runtimeCapBytes": 1048576,
        "checkpointCapBytes": 2097152,
        "engineExecution": "LOCAL preinstalled-code runtime.Call, not CREATE",
        "coordinatorExecution": "ordinary EVM CREATE with constructor-pinned AS0/ZI0/DI0 dependencies",
        "acceptedEngineCapChanged": False,
        "ordinaryOpcodeGasChanged": False,
    }
    write_json(build_dir / "paired-pins.json", pair_pins)

    fixture_row = run_checked([sys.executable, str(STAGE / "tools/generate_fixtures.py"), str(fixture_dir)],
                              cwd=ROOT, env=env, log=build_log_dir / "fixtures.log", timeout=300)
    if fixture_row["exit"] != 0 or fixture_row["timedOut"]:
        raise GateFailure(f"fresh generated fixture/oracle build failed: {fixture_row}")
    manifest = json.loads((fixture_dir / "fixture-manifest.json").read_text())
    required_cases = {"Checkpoint2MArrayPair", "Checkpoint2MArrayBoundary", "checkpoint2m-exact150",
                      "raw150-envelope", "raw151-refusal", "raw-bytes-exact", "raw-bytes-over"}
    if not required_cases.issubset(manifest["cases"]):
        raise GateFailure(f"generated-only fixture manifest omitted required case(s): {required_cases - set(manifest['cases'])}")
    if len(manifest["cases"]) != 41 or len(manifest["hostOracles"]) != 21:
        raise GateFailure(f"generated-only fixture manifest count mismatch: {len(manifest['cases'])}/{len(manifest['hostOracles'])}")
    math_oracle = manifest.get("mathDoubleMinMaxOracle", {}).get("cases", {})
    if math_oracle.get("MathDoubleMinMaxEdges", {}).get("pairCount") != 24 or \
            math_oracle.get("MathDoubleMinMaxRandom", {}).get("pairCount") != 256:
        raise GateFailure("generated full-IEEE edge/random oracle matrix size mismatch")
    limits = manifest["limits"]
    if (limits["rawClasses"] != 150 or limits["rawBytes"] != 1063930 or
            limits["diagnosticClasses"] != 250 or limits["runtimeCapBytes"] != 1048576 or
            limits["checkpointCapBytes"] != 2097152):
        raise GateFailure("generated fixture raw/diagnostic/runtime/checkpoint boundary differs from frozen profile")
    exact = manifest["cases"]["raw-bytes-exact"]
    if exact["rawCount"] != 150 or exact["rawBytes"] != 1063930 or max(x["bytes"] for x in exact["rawClasses"]) > 262144:
        raise GateFailure("exact-byte positive bundle or DI0 resource boundary mismatch")
    if manifest["identityHashMapCapacityOracle"]["rows"]["21845"]["tableLength"] != 65536:
        raise GateFailure("independent Java 8 reflection oracle omitted the legal table upper bound")

    driver_row = run_checked(["go", "build", "-trimpath", "-o", str(driver_bin),
                              "./" + (STAGE / "tools").relative_to(ROOT).as_posix()],
                             cwd=ROOT, env=env, log=build_log_dir / "driver-build.log", timeout=300)
    if driver_row["exit"] != 0 or driver_row["timedOut"]:
        raise GateFailure(f"fresh generated EVM driver build failed: {driver_row}")
    legacy_base = STAGE.parent / "checkpoint-2m-base-p33"
    legacy_pins = json.loads((legacy_base / "p33-pins.json").read_text())
    if (legacy_pins["address"] != pins["engineAddress"] or legacy_pins["owner"] != pins["ownerAddress"] or
            legacy_pins["bootstrapCount"] != 100 or legacy_pins["globalNativeBindings"] != 21 or
            legacy_pins["rawLimits"] != [150, 1063930] or legacy_pins["runtimeCap"] != 1048576 or
            legacy_pins["checkpointCap"] != 1048576):
        raise GateFailure("checkpoint-2m profile no longer binds the frozen P33 address/owner and legacy limits")
    legacy_engine_path = legacy_base / "engine/MCEntryInterpreter.json"
    legacy_coord_path = legacy_base / "coordinator/MCEntryCoordinator.json"
    legacy_engine = json.loads(legacy_engine_path.read_text())
    legacy_coord = json.loads(legacy_coord_path.read_text())
    legacy_engine_code = bytes.fromhex(legacy_engine["deployedBytecode"].removeprefix("0x"))
    legacy_coord_code = bytes.fromhex(legacy_coord["deployedBytecode"].removeprefix("0x"))
    if (len(legacy_engine_code) != 398336 or sha(legacy_engine_code) != legacy_pins["engine"]["runtimeSHA256"] or
            legacy_engine["codeHashes"]["runtimeKeccak256"] != legacy_pins["engine"]["runtimeKeccak256"] or
            len(legacy_coord_code) != 5411 or sha(legacy_coord_code) != legacy_pins["coordinator"]["runtimeSHA256"] or
            legacy_coord["codeHashes"]["runtimeKeccak256"] != legacy_pins["coordinator"]["runtimeKeccak256"]):
        raise GateFailure("frozen P33 1 MiB baseline artifacts no longer match their pinned runtime hashes")
    return (build_dir, fixture_dir, driver_bin, engine_path, coordinator_dir / "MCEntryCoordinator.json",
            manifest, pair_pins, [build_row, fixture_row, driver_row],
            legacy_engine_path, legacy_coord_path)


def run_attempt(number: int, gas: int, wall: int, *, build_dir: Path, fixture_dir: Path,
                driver_bin: Path, engine_path: Path, coordinator_path: Path,
                legacy_engine_path: Path, legacy_coord_path: Path,
                attempt_dir: Path, env: dict[str, str]) -> dict[str, object]:
    attempt_dir.mkdir(parents=True, exist_ok=False)
    logs = attempt_dir / "logs"
    logs.mkdir()
    direct_dir = attempt_dir / "direct"
    direct_dir.mkdir()
    coordinator_report_dir = attempt_dir / "coordinator"
    coordinator_report_dir.mkdir()
    deadline = time.monotonic() + wall
    commands: list[dict[str, object]] = []
    shared = [str(engine_path), str(coordinator_path), str(fixture_dir / "fixture-manifest.json"),
              str(fixture_dir)]

    def execute(label: str, args: list[str], report_dir: Path) -> None:
        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            raise WallBudgetShortage(f"attempt {number} exhausted {wall}s test-only wall budget before {label}")
        command = [str(driver_bin), *args, *shared, str(report_dir), str(gas),
                   str(legacy_engine_path), str(legacy_coord_path)]
        row = run_checked(command, cwd=ROOT, env=env, log=logs / f"{label}.log", timeout=remaining)
        row["label"] = label
        commands.append(row)
        write_json(attempt_dir / "commands.json", commands)
        if row["timedOut"]:
            raise WallBudgetShortage(f"attempt {number} timed out during {label} at {wall}s")
        if row["exit"] == 42:
            failure_path = report_dir / "gate-failure.json"
            detail = json.loads(failure_path.read_text()) if failure_path.exists() else {}
            failure = detail.get("failure", {})
            if failure.get("classification") == "test-only-gas-budget":
                raise GasBudgetShortage(failure.get("error", f"{label} exhausted the per-call gas budget"))
            raise GateFailure(f"{label} returned42 without explicit test-only gas classification")
        if row["exit"] != 0:
            failure_path = report_dir / "gate-failure.json"
            explanation = failure_path.read_text() if failure_path.exists() else "no structured driver failure"
            raise GateFailure(f"{label} failed ({row['exit']}): {explanation[:2000]}")

    execute("direct-generated-engine-gate", ["gate"], direct_dir)
    execute("fresh-process-q1-reopen", ["reopen"], direct_dir)
    execute("generated-coordinator-engine-route", ["coordinator"], coordinator_report_dir)
    direct = json.loads((direct_dir / "gate-summary.json").read_text())
    reopen = json.loads((direct_dir / "reopen-summary.json").read_text())
    coordinated = json.loads((coordinator_report_dir / "coordinator-summary.json").read_text())
    raw150 = next(row for row in direct["schedules"] if row["name"] == "q1-raw150")
    if raw150["rawCount"] != 150 or raw150["diagnosticClassCount"] != 250 or raw150["final"]["lifecycle"] != 2:
        raise GateFailure("direct exact150 q1 terminal evidence mismatch")
    identity_map = next(row for row in direct["schedules"] if row["name"] == "q1-identity-hash-map-matrix")
    if identity_map["rawCount"] != 1 or identity_map["diagnosticClassCount"] != 101 or identity_map["final"]["lifecycle"] != 2:
        raise GateFailure("IdentityHashMap matrix direct terminal evidence mismatch")
    pair = next(row for row in direct["schedules"] if row["name"] == "q1-checkpoint-2m-array-pair")
    if (pair["rawCount"] != 1 or pair["checkpointBytes"] <= 1048576 or pair["checkpointBytes"] > 2097152 or
            pair["readOnlyCheckpointHeapAudit"]["checkpoint2mObjectArrayElements"] != 131072 or
            pair["readOnlyCheckpointHeapAudit"]["checkpoint2mObjectArrayCellsAllZero"] is not True or
            pair["final"]["lifecycle"] != 2):
        raise GateFailure("q1 eager Object[65536] pair did not produce an authenticated >1MiB checkpoint")
    if (not reopen.get("distinctProcess") or reopen.get("reopenCount") != 4 or
            reopen.get("rawCount") != 150 or reopen.get("diagnosticClassCount") != 250 or
            reopen.get("identityHashMapRawCount") != 1 or reopen.get("identityHashMapDiagnosticClassCount") != 101 or
            reopen.get("mathEdgeRawCount") != 1 or reopen.get("mathEdgeDiagnosticClassCount") != 101 or
            reopen.get("checkpoint2mArrayPairRawCount") != 1):
        raise GateFailure("fresh-process q1 raw150/IdentityHashMap/Math/>1MiB MR01 reopen mismatch")
    controls = {row["name"]: row for row in direct.get("controls", [])}
    for name in ("legacy-1m-checkpoint-atomic-refusal", "checkpoint-2m-output-cap-refusal"):
        row = controls.get(name)
        if (row is None or row.get("errorName") != "LC0StateError" or row.get("errorArgs") != ["1", "0"] or
                row.get("rootBefore") != row.get("rootAfter") or row.get("atomic") is not True):
            raise GateFailure(f"{name} did not preserve the state/head on typed checkpoint-cap refusal")
    plus_one = controls.get("checkpoint-2m-plus-one-validator-refusal")
    if (plus_one is None or plus_one.get("checkpointBytes") != 2097153 or
            plus_one.get("errorName") != "LC0StateError" or plus_one.get("errorArgs") != ["1", "0"] or
            plus_one.get("rootBefore") != plus_one.get("rootAfter")):
        raise GateFailure("exact 2MiB+1 read-only validator refusal evidence mismatch")
    if (coordinated["rawCount"] != 150 or coordinated["rawBytes"] != 1063930 or
            coordinated["diagnosticClassCount"] != 250 or coordinated["checkpointBytes"] <= 1048576 or
            coordinated["checkpointBytes"] > 2097152 or coordinated["runtimeCodeHash"] != direct["engineRuntimeKeccak256"] or
            coordinated["executedJvmSteps"] != coordinated["jvmSteps"] or
            coordinated["executedInternalSteps"] != coordinated["internalSteps"]):
        raise GateFailure("ordinary-CREATE coordinator exact150/>1MiB terminal evidence mismatch")
    return {"attempt": number, "status": "passed", "gasBudget": gas,
            "wallBudgetSeconds": wall, "elapsedWallSeconds": round(wall - max(0, int(deadline - time.monotonic())), 3),
            "direct": direct, "reopen": reopen, "coordinator": coordinated, "commands": commands}


def main() -> int:
    if len(sys.argv) > 2:
        raise SystemExit("usage: run_gate.py [RUN_ID]")
    run_id = sys.argv[1] if len(sys.argv) == 2 else time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{os.getpid()}"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise SystemExit("RUN_ID must be a simple filesystem token")
    archive = STAGE / "runs" / run_id
    build_dir = ROOT / "build" / f"java-diff-mc-checkpoint-2m-build-{run_id}"
    fixture_dir = ROOT / "build" / f"java-diff-mc-checkpoint-2m-fixtures-{run_id}"
    transient = ROOT / "build" / f"java-diff-mc-checkpoint-2m-gate-{run_id}"
    if archive.exists() or build_dir.exists() or fixture_dir.exists() or transient.exists():
        raise SystemExit(f"run/build path already exists; refusing to overwrite: {run_id}")
    archive.mkdir(parents=True)
    transient.mkdir(parents=True)
    build_logs = transient / "build-logs"
    build_logs.mkdir()
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1", NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"),
               TMPDIR=str(transient / "tmp"))
    (transient / "tmp").mkdir()
    try:
        built = build_sources(run_id, env, build_logs)
    except GateFailure as exc:
        if build_logs.is_dir():
            shutil.copytree(build_logs, archive / "logs" / "build")
        write_json(archive / "failed-build.json", {"status": "build-failed", "error": str(exc)})
        raise
    (build_dir, fixture_dir, driver_bin, engine_path, coordinator_path, manifest, pair_pins,
     build_commands, legacy_engine_path, legacy_coord_path) = built
    # Preserve generated inputs/codehashes before any behavior gate can fail.
    shutil.copy2(fixture_dir / "fixture-manifest.json", archive / "fixture-manifest.json")
    shutil.copy2(build_dir / "paired-pins.json", archive / "paired-pins.json")
    gas, wall = INITIAL_GAS, INITIAL_WALL_SECONDS
    history: list[dict[str, object]] = []
    success: dict[str, object] | None = None
    for number in range(1, MAX_ATTEMPTS + 1):
        attempt_dir = transient / "attempts" / f"attempt-{number}"
        try:
            success = run_attempt(number, gas, wall, build_dir=build_dir, fixture_dir=fixture_dir,
                                  driver_bin=driver_bin, engine_path=engine_path,
                                  coordinator_path=coordinator_path, legacy_engine_path=legacy_engine_path,
                                  legacy_coord_path=legacy_coord_path, attempt_dir=attempt_dir, env=env)
            history.append({"attempt": number, "status": "passed", "gasBudget": gas,
                            "wallBudgetSeconds": wall, "commands": success["commands"]})
            break
        except GasBudgetShortage as exc:
            row = {"attempt": number, "status": "budget-insufficient", "classification": "test-only-gas-budget",
                   "gasBudget": gas, "wallBudgetSeconds": wall, "error": str(exc),
                   "commands": json.loads((attempt_dir / "commands.json").read_text()) if (attempt_dir / "commands.json").exists() else []}
            history.append(row)
            preserve_attempt(archive, attempt_dir, row, "test-only-gas-budget", gas, wall)
            gas *= 2
        except WallBudgetShortage as exc:
            row = {"attempt": number, "status": "budget-insufficient", "classification": "test-only-wall-clock-budget",
                   "gasBudget": gas, "wallBudgetSeconds": wall, "error": str(exc),
                   "commands": json.loads((attempt_dir / "commands.json").read_text()) if (attempt_dir / "commands.json").exists() else []}
            history.append(row)
            preserve_attempt(archive, attempt_dir, row, "test-only-wall-clock-budget", gas, wall)
            wall *= 2
        except GateFailure as exc:
            row = {"attempt": number, "status": "failed", "gasBudget": gas,
                   "wallBudgetSeconds": wall, "error": str(exc),
                   "commands": json.loads((attempt_dir / "commands.json").read_text()) if (attempt_dir / "commands.json").exists() else []}
            history.append(row)
            preserve_attempt(archive, attempt_dir, row, "semantic-or-harness-failure", gas, wall)
            write_json(archive / "failed-run.json", {"status": "failed", "attempts": history,
                                                        "pairPins": pair_pins})
            raise
    if success is None:
        write_json(archive / "failed-run.json", {"status": "failed-after-budget-expansions",
                                                  "attempts": history, "pairPins": pair_pins})
        raise GateFailure(f"generated gates did not pass after {MAX_ATTEMPTS} test-budget attempts")

    attempt_dir = transient / "attempts" / f"attempt-{success['attempt']}"
    direct_dir = attempt_dir / "direct"
    coordinator_report_dir = attempt_dir / "coordinator"
    shutil.copy2(fixture_dir / "fixture-manifest.json", archive / "fixture-manifest.json")
    shutil.copy2(direct_dir / "gate-summary.json", archive / "gate-summary.json")
    shutil.copy2(direct_dir / "reopen-summary.json", archive / "reopen-summary.json")
    shutil.copy2(coordinator_report_dir / "coordinator-summary.json", archive / "coordinator-summary.json")
    shutil.copy2(build_dir / "paired-pins.json", archive / "paired-pins.json")
    for source, name in (
        (direct_dir / "checkpoints/q1-identity-hash-map-matrix.checkpoint.bin", "q1-identity-hash-map-matrix.checkpoint.bin"),
        (direct_dir / "checkpoints/q1-raw150.checkpoint.bin", "q1-raw150.checkpoint.bin"),
        (direct_dir / "checkpoints/q1-math-double-min-max-edges.checkpoint.bin", "q1-math-double-min-max-edges.checkpoint.bin"),
        (direct_dir / "checkpoints/q1-checkpoint-2m-array-pair.checkpoint.bin", "q1-checkpoint-2m-array-pair.checkpoint.bin"),
        (direct_dir / "checkpoints/raw-bytes-exact.checkpoint.bin", "raw-bytes-exact.checkpoint.bin"),
        (coordinator_report_dir / "checkpoints/coordinator-checkpoint2m-exact150.checkpoint.bin", "coordinator-checkpoint2m-exact150.checkpoint.bin"),
    ):
        copy_if_present(source, archive / name)
    source_files = [STAGE / "README.md", STAGE / "pins.json", STAGE / "engine/MCEntryInterpreter.sol",
                    STAGE / "engine/build.js", STAGE / "coordinator/MCEntryCoordinator.sol",
                    STAGE / "coordinator/build.js", STAGE / "tools/build_candidate.py",
                    STAGE / "tools/generate_fixtures.py", STAGE / "tools/verify_source.py",
                    STAGE / "tools/evm_driver.go", STAGE / "tools/coordinator_route.go",
                    STAGE / "tools/run_gate.py", STAGE / "transport/checkpoint.go",
                    STAGE / "transport/checkpoint_test.go",
                    BASE / "SOURCE_MANIFEST.json", BASE / "p33-pins.json",
                    BASE / "engine/MCEntryInterpreter.sol", BASE / "engine/MCEntryInterpreter.json",
                    BASE / "coordinator/MCEntryCoordinator.sol", BASE / "coordinator/MCEntryCoordinator.json"]
    source_files.extend(sorted(p for p in (STAGE / "reference-transport").rglob("*") if p.is_file()))
    source_hashes = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in source_files}
    for directory in (STAGE / "bootstrap", STAGE / "fixtures/src"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and (path.suffix == ".java" or path.name.endswith(".template")):
                source_hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    # Preserve the exact build and execution logs inside the durable evidence tree;
    # never leave the only useful reproduction data under ignored build/ paths.
    archived_build_commands = []
    for i, command in enumerate(build_commands):
        archived = dict(command)
        source_log = Path(str(command["log"]))
        log_name = f"build-{i + 1}-{source_log.name}"
        copy_if_present(source_log, archive / "logs" / log_name)
        archived["log"] = f"logs/{log_name}"
        archived_build_commands.append(archived)
    for command in success["commands"]:
        source_log = Path(str(command["log"]))
        log_name = f"{command['label']}.log"
        copy_if_present(source_log, archive / "logs" / log_name)
        command["log"] = f"logs/{log_name}"
    tool_versions = {}
    for name, cmd in (("go", ["go", "version"]), ("node", ["node", "--version"]),
                      ("python", [sys.executable, "--version"]), ("javac", ["javac", "-version"])):
        try:
            tool_versions[name] = subprocess.check_output(cmd, cwd=ROOT, env=env, text=True,
                                                           stderr=subprocess.STDOUT).strip()
        except Exception as exc:
            tool_versions[name] = f"unavailable: {exc}"
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_report = {
        "status": "generated-only P33 checkpoint-only 2 MiB profile gates passed; 1 MiB legacy control, eager arrays, q1/q7/q4096/q65536/direct, reopen, exact 2 MiB+1 validator refusal, raw150 engine/coordinator; original replay not run",
        "runId": run_id, "gitHead": git_head, "sourceHashes": source_hashes,
        "attemptHistory": history,
        "budgetClassification": "ordinary1B/1200s" if gas == 1_000_000_000 and wall == 1200 else "expanded-test-only-budget-not-ordinary1B",
        "testOnlyGasBudget": gas,
        "testOnlyWallBudgetSeconds": wall, "elapsedWallSeconds": success["elapsedWallSeconds"],
        "toolVersions": tool_versions, "checkpointCapBytes": 2097152,
        "runtimeCapBytes": 1048576, "acceptedEngineCapChanged": False,
        "legacyCheckpointCapBytes": 1048576,
        "buildCommands": archived_build_commands, "pairedPins": pair_pins,
        "generatedClassCount": len(manifest["cases"]), "hostOracleCount": len(manifest["hostOracles"]),
        "directElapsedMS": success["direct"]["elapsedMs"],
        "coordinatorTotalGas": success["coordinator"]["totalGas"],
        "coordinatorMaxCallGas": success["coordinator"]["maxCallGas"],
        "directTerminalRaw150Schedules": ["q1-raw150", "q7-raw150", "q65536-raw150", "q4096-raw150"],
        "checkpoint2mArrayPairSchedules": ["q1", "q7", "q4096", "q65536", "direct"],
        "checkpoint2mBoundaryControls": ["legacy 1 MiB positive refusal", "2 MiB array overflow refusal", "exact 2 MiB+1 read-only validator refusal"],
        "identityHashMapSchedules": ["q1-identity-hash-map-matrix", "q7-identity-hash-map-matrix",
                                      "q65536-identity-hash-map-matrix", "q4096-identity-hash-map-matrix"],
        "mathDoubleMinMaxSchedules": ["q1/q7/q65536/q4096 edge witness", "q65536/q4096 deterministic random matrix",
                                       "fresh-process q1 edge checkpoint reopen"],
        "actualCountsVerified": {"raw150": 150, "rawByteLimit": 1063930, "rawDiagnosticClasses": 250,
                                  "bootstrapClasses": 100, "raw151Refused": True, "rawBytePlusOneRefused": True,
                                  "identityHashMapRawCount": 1, "identityHashMapDiagnosticClasses": 101,
                                  "identityHashMapReflectionMatrix": 9, "mathEdgePairs": 24,
                                  "mathRandomPairs": 256, "mathRawResultsComparedToReadOnlyJdk8": 560,
                                  "checkpoint2mArrayElements": 131072, "legacyOneMiBRefusal": True,
                                  "exactCheckpoint2mPlusOneRefusal": True, "newNativeBindings": 0},
    }
    write_json(archive / "run-report.json", run_report)
    print(json.dumps({"status": run_report["status"], "archive": str(archive),
                      "testOnlyGasBudget": gas, "testOnlyWallBudgetSeconds": wall,
                      "directElapsedMS": run_report["directElapsedMS"],
                      "coordinatorTotalGas": run_report["coordinatorTotalGas"],
                      "coordinatorMaxCallGas": run_report["coordinatorMaxCallGas"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateFailure as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
