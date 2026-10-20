#!/usr/bin/env python3
"""Build and run generated-only LOCAL1M ArrayList gates on the pinned geth EVM.

The engine is locally preinstalled bytecode (not CREATE); a second path reuses
P28's pinned canonical AS0/ZI0/DI0 -> coordinator -> MR0 transport with only the
candidate engine/coordinator hashes and selected local gas budget substituted.
"""
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
import zipfile

STAGE = Path(__file__).resolve().parent.parent
ROOT = STAGE.parents[3]
BASE_DRIVER = ROOT / "evidence/java-evm/minecraft-entry/parent-raw75-byte531965/canonical-driver.go.txt"
BASE_DRIVER_SHA256 = "d5f3ea7664d48879d2d96347acdb048f489ec0d2febbde576a5935ebca82a0f8"
BASE_ENGINE_SHA256 = "7e8be2b757b3130749433cfdba2654561562afeeb1cb96c755c7bf01670b9857"
BASE_ENGINE_KECCAK = "0xb1de9eaf84f61d4c8cac2cd35f3e003f3bd4714111fb2afd1667a049994ddca3"
BASE_COORD_KECCAK = "0xb30fe93c4e112d1e01a19e38f623353b734f4b528bb4aa81d41eecded28842b6"
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
                timeout: int = 900) -> dict[str, object]:
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open("w") as stream:
        try:
            p = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                               stderr=subprocess.STDOUT, timeout=timeout)
            code = p.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            code = -999
            timed_out = True
    row = {"command": command, "exit": code, "timedOut": timed_out,
           "timeoutSeconds": timeout, "wallSeconds": round(time.monotonic() - started, 3),
           "log": str(log)}
    return row


def make_canonical_source(engine: dict, coordinator: dict, gas: int, out: Path) -> None:
    base_bytes = BASE_DRIVER.read_bytes()
    if sha(base_bytes) != BASE_DRIVER_SHA256:
        raise GateFailure("pinned canonical generated-driver source SHA256 changed")
    source = base_bytes.decode()
    engine_sha = engine["codeHashes"]["runtimeSHA256"]
    engine_keccak = "0x" + engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x")
    coordinator_keccak = "0x" + coordinator["codeHashes"]["runtimeKeccak256"].removeprefix("0x")
    engine_bytes = len(bytes.fromhex(engine["deployedBytecode"].removeprefix("0x")))
    patches = [
        (f'const ordinaryGas = uint64(1_000_000_000)', f'const ordinaryGas = uint64({gas})', 1),
        (f'const immutableEngineSHA256 = "{BASE_ENGINE_SHA256}"', f'const immutableEngineSHA256 = "{engine_sha}"', 1),
        (f'const immutableEngineKeccak = "{BASE_ENGINE_KECCAK}"', f'const immutableEngineKeccak = "{engine_keccak}"', 1),
        (f'const immutableCoordinatorKeccak = "{BASE_COORD_KECCAK}"', f'const immutableCoordinatorKeccak = "{coordinator_keccak}"', 1),
        ("len(engineRun) != 392091", f"len(engineRun) != {engine_bytes}", 1),
        ("len(run) != 392091", f"len(run) != {engine_bytes}", 1),
    ]
    for old, new, count in patches:
        actual = source.count(old)
        if actual != count:
            raise GateFailure(f"canonical driver pin patch count mismatch for {old!r}: {actual}")
        source = source.replace(old, new)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(source)


def create_matrix_zip(fixtures: Path, out: Path) -> tuple[str, list[dict[str, object]]]:
    bundle_dir = fixtures / "bundles/ArrayListMatrix"
    bundle = json.loads((bundle_dir / "bundle.json").read_text())
    bindings: list[str] = []
    entries: list[dict[str, object]] = []
    with zipfile.ZipFile(out, "w") as archive:
        for row in bundle["rawClasses"]:
            resource = row["binaryName"].replace(".", "/") + ".class"
            data = (bundle_dir / row["file"]).read_bytes()
            if len(data) != row["bytes"] or sha(data) != row["sha256"]:
                raise GateFailure(f"generated class hash mismatch before zip: {resource}")
            info = zipfile.ZipInfo(resource, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
            bindings.append(resource)
            entries.append({"resource": resource, "bytes": len(data), "sha256": sha(data)})
    return ",".join(bindings), entries


def archive_attempt_failure(archive: Path, attempt_dir: Path, reason: str,
                            gas: int, wall: int, attempt: int) -> None:
    dest = archive / "attempt-failures" / f"attempt-{attempt}"
    dest.mkdir(parents=True, exist_ok=False)
    write_json(dest / "failure.json", {"attempt": attempt, "classification": reason,
                                        "gasBudget": gas, "wallBudgetSeconds": wall})
    for name in ("gate-failure.json", "gate-summary.json", "reopen-summary.json"):
        src = attempt_dir / "direct" / name
        if src.exists():
            shutil.copy2(src, dest / name)
    logs = attempt_dir / "logs"
    if logs.exists():
        shutil.copytree(logs, dest / "logs")
    coordinator_logs = attempt_dir / "coordinator-route/logs"
    if coordinator_logs.exists():
        shutil.copytree(coordinator_logs, dest / "coordinator-logs")


def run_attempt(number: int, gas: int, wall: int, *, build_dir: Path,
                fixtures_dir: Path, run_root: Path, engine: dict,
                coordinator: dict, direct_binary: Path, matrix_zip: Path,
                bindings: str) -> tuple[dict, list[dict[str, object]]]:
    attempt_dir = run_root / "attempts" / f"attempt-{number}"
    attempt_dir.mkdir(parents=True, exist_ok=False)
    (attempt_dir / "logs").mkdir()
    deadline = time.monotonic() + wall
    commands: list[dict[str, object]] = []
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1", NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"),
               TMPDIR=str(attempt_dir / "tmp"))
    (attempt_dir / "tmp").mkdir()

    def execute(label: str, command: list[str], call_env: dict[str, str] | None = None) -> int:
        left = int(deadline - time.monotonic())
        if left <= 0:
            raise WallBudgetShortage(f"attempt {number} exceeded {wall}s test-only wall budget before {label}")
        row = run_checked(command, cwd=ROOT, env=call_env or env,
                          log=attempt_dir / "logs" / f"{label}.log", timeout=left)
        row["label"] = label
        commands.append(row)
        write_json(attempt_dir / "commands.json", commands)
        if row["timedOut"]:
            raise WallBudgetShortage(f"attempt {number} timed out in {label} at {wall}s")
        return int(row["exit"])

    canonical_src = attempt_dir / "tools/canonical_generated_driver.go"
    canonical_bin = attempt_dir / "tools/canonical_generated_driver"
    make_canonical_source(engine, coordinator, gas, canonical_src)
    canonical_rel = "./" + canonical_src.relative_to(ROOT).as_posix()
    code = execute("build-canonical-driver", ["go", "build", "-trimpath", "-o", str(canonical_bin), canonical_rel])
    if code != 0:
        raise GateFailure(f"attempt {number}: canonical driver build failed")

    direct_dir = attempt_dir / "direct"
    direct_dir.mkdir()
    fixture_manifest = fixtures_dir / "fixture-manifest.json"
    direct_cmd = [str(direct_binary), "gate", str(build_dir / "engine/MCEntryInterpreter.json"),
                  str(build_dir / "coordinator/MCEntryCoordinator.json"), str(fixture_manifest),
                  str(fixtures_dir), str(direct_dir), str(gas)]
    code = execute("direct-generated-evm-gate", direct_cmd)
    if code == 42:
        detail = json.loads((direct_dir / "gate-failure.json").read_text())
        if detail.get("failure", {}).get("classification") == "test-only-gas-budget":
            raise GasBudgetShortage(detail["failure"].get("error", "positive direct EVM case exhausted per-call gas"))
        raise GateFailure("driver exit42 without explicit test-only-gas classification")
    if code != 0:
        failure_path = direct_dir / "gate-failure.json"
        explanation = failure_path.read_text() if failure_path.exists() else "no structured driver failure"
        raise GateFailure(f"direct generated EVM gate failed ({code}): {explanation[:1200]}")

    code = execute("fresh-process-q1-reopen", [str(direct_binary), "reopen",
                  str(build_dir / "engine/MCEntryInterpreter.json"),
                  str(build_dir / "coordinator/MCEntryCoordinator.json"), str(fixture_manifest),
                  str(fixtures_dir), str(direct_dir), str(gas)])
    if code == 42:
        raise GasBudgetShortage("read-only fresh-process EVM reopen exhausted per-call gas")
    if code != 0:
        raise GateFailure(f"fresh-process EVM reopen failed ({code})")

    coordinator_dir = attempt_dir / "coordinator-route"
    coordinator_dir.mkdir()
    world = coordinator_dir / "world-q1"
    coordinator_env = dict(env, MC_ENTRY_BINDINGS=bindings)
    base_args = [str(canonical_bin)]
    shared = [str(world), str(build_dir / "coordinator/MCEntryCoordinator.json"),
              str(build_dir / "engine/MCEntryInterpreter.json"), str(matrix_zip), "1"]
    for label, mode in (("coordinator-start-q1", "setup-chain"),
                        ("coordinator-resume-q1", "finish"),
                        ("coordinator-reopen-q1", "verify")):
        code = execute(label, base_args + [mode] + shared, coordinator_env)
        if code != 0:
            log = (attempt_dir / "logs" / f"{label}.log").read_text(errors="replace")
            if re.search(r"out of gas|ErrOutOfGas", log, re.IGNORECASE):
                raise GasBudgetShortage(f"canonical positive EVM transport exhausted per-call gas in {label}: {log[-600:]}")
            raise GateFailure(f"canonical coordinator route failed in {label} ({code}): {log[-1200:]}")

    direct_report = json.loads((direct_dir / "gate-summary.json").read_text())
    reopen_report = json.loads((direct_dir / "reopen-summary.json").read_text())
    if direct_report["status"] != "generated EVM gates passed; original replay/Done not part of this worker":
        raise GateFailure("direct driver did not publish its complete success sentinel")
    if not reopen_report.get("distinctProcess") or reopen_report.get("stateRoot") != next(
        x["stateRoot"] for x in direct_report["schedules"] if x["name"] == "q1-matrix"):
        raise GateFailure("fresh-process q1 database/head/checkpoint verification did not match")
    world_head = json.loads((world / "durable-head.json").read_text())
    world_report = json.loads((coordinator_dir / "reports/world-q1/world-report.json").read_text())
    start_report = json.loads((coordinator_dir / "reports/world-q1/start.json").read_text())
    direct_q1 = next(x for x in direct_report["schedules"] if x["name"] == "q1-matrix")
    if (world_head["stage"] != "final-reopened" or world_head["lifecycle"] != 2 or
        world_head["outcome"] != 2 or world_head["result"] != 0 or
        world_head["epoch"] != 336 or world_head["jvmSteps"] != direct_q1["final"]["totalJvmSteps"] or
        world_head["internalSteps"] != direct_q1["final"]["totalInternalSteps"] or
        world_head["machineRoot"] != direct_q1["final"]["machineStateRoot"] or
        world_head["engineCodeHash"].lower() != "0x" + engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x").lower() or
        world_head["coordinatorCodeHash"].lower() != "0x" + coordinator["codeHashes"]["runtimeKeccak256"].removeprefix("0x").lower()):
        raise GateFailure("canonical coordinator q1 terminal/reopen manifest mismatch")
    if world_head["totalClassBytes"] != 1177 or world_head["slices"] != 336:
        raise GateFailure("canonical route class size/slice count mismatch")
    if world_head["counters"]["readFragmentCount"] != 336 or world_head["counters"]["readByteCount"] != 336 * 1177:
        raise GateFailure("canonical DI0 resource read receipts mismatch")
    if world_head["counters"]["maxGas"] >= gas:
        raise GateFailure("canonical per-call gas reached/exceeded supplied test-only gas budget")
    if start_report["actualReadSizes"] != [1177] or start_report["slice"]["lifecycle"] != 1:
        raise GateFailure("canonical first q1 coordinator result/read-size proof mismatch")
    if world_report["manifest"]["trieRoot"] != world_head["trieRoot"]:
        raise GateFailure("canonical verify/reopen root mismatch")
    if world_report["manifest"]["vfsRoot"] != direct_q1["final"]["vfsStateRoot"]:
        raise GateFailure("canonical/direct q1 VFS state roots differ")
    result = {"attempt": number, "gasBudgetPerEVMCall": gas,
              "wallBudgetSeconds": wall, "directGate": direct_report,
              "freshProcessReopen": reopen_report,
              "canonicalCoordinatorRoute": {
                  "status": "generated-only EVM AS0/ZI0/DI0 -> newly paired coordinator -> engine q1 start/resume/fresh-process verify passed",
                  "worldHead": world_head, "worldReport": world_report,
                  "startReport": start_report, "matrixZipBytes": matrix_zip.stat().st_size,
                  "matrixZipSHA256": sha(matrix_zip.read_bytes()), "bindings": bindings,
                  "zipEntries": json.loads((run_root / "matrix-zip-entries.json").read_text()),
                  "readFragments": world_head["counters"]["readFragmentCount"],
                  "readBytes": world_head["counters"]["readByteCount"],
              },
              "commands": commands}
    return result, commands


def main() -> int:
    if len(sys.argv) > 2:
        raise SystemExit("usage: run_gate.py [RUN_ID]")
    run_id = sys.argv[1] if len(sys.argv) == 2 else time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{os.getpid()}"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise SystemExit("RUN_ID must be a simple filesystem token")
    build_dir = ROOT / "build" / f"java-diff-mc-array-list-local1m-build-{run_id}"
    fixtures_dir = ROOT / "build" / f"java-diff-mc-array-list-local1m-fixtures-{run_id}"
    transient_run = ROOT / "build" / f"java-diff-mc-array-list-local1m-gate-{run_id}"
    archive = STAGE / "runs" / run_id
    if archive.exists() or build_dir.exists() or fixtures_dir.exists() or transient_run.exists():
        raise SystemExit(f"run/build path already exists; refusing to overwrite: {run_id}")
    transient_run.mkdir(parents=True)
    (transient_run / "build-logs").mkdir()
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1", NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"),
               TMPDIR=str(transient_run / "build-tmp"))
    (transient_run / "build-tmp").mkdir()
    build_row = run_checked([sys.executable, str(STAGE / "tools/build_candidate.py"), str(build_dir)],
                            cwd=ROOT, env=env, log=transient_run / "build-logs/candidate.log", timeout=900)
    if build_row["exit"] != 0 or build_row["timedOut"]:
        write_json(transient_run / "build-failure.json", build_row)
        raise GateFailure(f"fresh candidate build failed: see {build_row['log']}")
    engine_artifact_path = build_dir / "engine/MCEntryInterpreter.json"
    engine = json.loads(engine_artifact_path.read_text())
    if len(bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))) != 394435:
        raise GateFailure("fresh candidate runtime size drifted from pinned LOCAL1M build")

    coord_stage = STAGE / "coordinator"
    coord_build = build_dir / "coordinator"
    shutil.copytree(coord_stage, coord_build)
    coord_source = (coord_build / "MCEntryCoordinator.sol").read_text()
    pin_match = re.search(r'ENGINE_CODEHASH\s*=\s*hex"([0-9a-fA-F]{64})"', coord_source)
    if not pin_match or pin_match.group(1).lower() != engine["codeHashes"]["runtimeKeccak256"].lower():
        raise GateFailure("coordinator source does not pin the fresh candidate engine codehash")
    coord_log = transient_run / "build-logs/coordinator.log"
    coord_env = dict(env, TMPDIR=str(transient_run / "build-tmp"))
    coord_row = run_checked(["node", str(coord_build / "build.js")], cwd=ROOT, env=coord_env,
                            log=coord_log, timeout=900)
    if coord_row["exit"] != 0 or coord_row["timedOut"]:
        write_json(transient_run / "build-logs/coordinator-command.json", coord_row)
        raise GateFailure(f"fresh paired coordinator compilation failed: see {coord_log}")
    coordinator = json.loads((coord_build / "MCEntryCoordinator.json").read_text())
    if len(bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))) != 5394:
        raise GateFailure("fresh coordinator runtime size drifted from frozen P28 coordinator")
    if sha(bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))) != coordinator["codeHashes"]["runtimeSHA256"]:
        raise GateFailure("fresh coordinator runtime SHA pin mismatch")
    pair_pins = {
        "profile": "P28-ARRAY-LIST-LOCAL1M-GENERATED-EVM-TESTS",
        "candidateEngine": {"runtimeBytes": 394435, **engine["codeHashes"]},
        "pairedCoordinator": {"runtimeBytes": 5394, **coordinator["codeHashes"],
                              "sourceSHA256": sha((coord_build / "MCEntryCoordinator.sol").read_bytes()),
                              "buildScriptSHA256": sha((coord_build / "build.js").read_bytes())},
        "coordinatorPinsCandidateEngineKeccak": pin_match.group(1).lower(),
        "coordinatorCompiler": coordinator["compiler"],
        "pairVerifiedFromFreshBuild": True,
        "engineExecutionMode": "LOCAL preinstalled-code Call, not CREATE deployment",
        "coordinatorAndResourceTransport": "ordinary generated-only AS0/ZI0/DI0 CREATE plus coordinator; no external/original assets",
    }
    write_json(build_dir / "paired-pins.json", pair_pins)

    fixture_row = run_checked([sys.executable, str(STAGE / "tools/generate_fixtures.py"), str(fixtures_dir)],
                              cwd=ROOT, env=env, log=transient_run / "build-logs/fixtures.log", timeout=300)
    if fixture_row["exit"] != 0 or fixture_row["timedOut"]:
        write_json(transient_run / "build-logs/fixtures-command.json", fixture_row)
        raise GateFailure(f"fresh generated fixture build/oracles failed: see {fixture_row['log']}")
    fixture_manifest = json.loads((fixtures_dir / "fixture-manifest.json").read_text())
    if len(fixture_manifest["cases"]) != 19 or len(fixture_manifest["hostOracles"]) != 14:
        raise GateFailure("generated fixture manifest case/oracle count mismatch")
    driver_bin = build_dir / "tools/evm_driver"
    driver_bin.parent.mkdir(parents=True)
    direct_build = run_checked(["go", "build", "-trimpath", "-o", str(driver_bin),
                                "./" + (STAGE / "tools/evm_driver.go").relative_to(ROOT).as_posix()],
                               cwd=ROOT, env=env, log=transient_run / "build-logs/direct-driver.log", timeout=300)
    if direct_build["exit"] != 0 or direct_build["timedOut"]:
        write_json(transient_run / "build-logs/direct-driver-command.json", direct_build)
        raise GateFailure(f"fresh EVM driver build failed: see {direct_build['log']}")

    matrix_zip = build_dir / "ArrayListMatrix.generated.zip"
    bindings, zip_entries = create_matrix_zip(fixtures_dir, matrix_zip)
    write_json(transient_run / "matrix-zip-entries.json", zip_entries)
    archive.mkdir(parents=True, exist_ok=False)
    history: list[dict[str, object]] = []
    gas, wall = INITIAL_GAS, INITIAL_WALL_SECONDS
    success: dict | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            success, commands = run_attempt(attempt, gas, wall, build_dir=build_dir,
                                            fixtures_dir=fixtures_dir, run_root=transient_run,
                                            engine=engine, coordinator=coordinator,
                                            direct_binary=driver_bin, matrix_zip=matrix_zip,
                                            bindings=bindings)
            history.append({"attempt": attempt, "status": "passed", "gasBudget": gas,
                            "wallBudgetSeconds": wall, "commands": commands})
            break
        except GasBudgetShortage as exc:
            history.append({"attempt": attempt, "status": "budget-insufficient", "classification": "test-only-gas-budget",
                            "gasBudget": gas, "wallBudgetSeconds": wall, "error": str(exc)})
            archive_attempt_failure(archive, transient_run / "attempts" / f"attempt-{attempt}",
                                    "test-only-gas-budget", gas, wall, attempt)
            if gas > (2**64 - 1) // 2:
                raise GateFailure("local test-only gas budget cannot be doubled safely")
            gas *= 2
        except WallBudgetShortage as exc:
            history.append({"attempt": attempt, "status": "budget-insufficient", "classification": "test-only-wall-clock-budget",
                            "gasBudget": gas, "wallBudgetSeconds": wall, "error": str(exc)})
            archive_attempt_failure(archive, transient_run / "attempts" / f"attempt-{attempt}",
                                    "test-only-wall-clock-budget", gas, wall, attempt)
            wall *= 2
        except GateFailure as exc:
            history.append({"attempt": attempt, "status": "failed", "gasBudget": gas,
                            "wallBudgetSeconds": wall, "error": str(exc)})
            attempt_dir = transient_run / "attempts" / f"attempt-{attempt}"
            if attempt_dir.exists():
                archive_attempt_failure(archive, attempt_dir, "semantic-or-harness-failure", gas, wall, attempt)
            write_json(archive / "failed-run.json", {"status": "failed", "attempts": history,
                                                        "gitHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                                        "error": str(exc), "pairedPins": pair_pins})
            raise
    if success is None:
        write_json(archive / "failed-run.json", {"status": "failed-after-budget-expansions", "attempts": history,
                                                    "pairedPins": pair_pins,
                                                    "gitHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
        raise GateFailure(f"generated gate did not pass after {MAX_ATTEMPTS} finite test-only budget attempts")

    attempt_dir = transient_run / "attempts" / f"attempt-{success['attempt']}"
    direct_dir = attempt_dir / "direct"
    canonical_dir = attempt_dir / "coordinator-route"
    shutil.copy2(fixtures_dir / "fixture-manifest.json", archive / "fixture-manifest.json")
    shutil.copy2(direct_dir / "gate-summary.json", archive / "gate-summary.json")
    shutil.copy2(direct_dir / "reopen-summary.json", archive / "reopen-summary.json")
    shutil.copy2(build_dir / "paired-pins.json", archive / "paired-pins.json")
    shutil.copy2(direct_dir / "checkpoints/q1-matrix.checkpoint.bin", archive / "direct-q1-matrix.checkpoint.bin")
    shutil.copy2(direct_dir / "checkpoints/arraylist-maximum-legal-capacity.checkpoint.bin",
                 archive / "arraylist-maximum-legal-capacity.checkpoint.bin")
    shutil.copy2(canonical_dir / "world-q1/checkpoints" /
                 (json.loads((canonical_dir / "world-q1/durable-head.json").read_text())["checkpointSHA256"] + ".bin"),
                 archive / "coordinator-q1-matrix.checkpoint.bin")
    report_dir = canonical_dir / "reports/world-q1"
    for name in ("world-report.json", "start.json"):
        shutil.copy2(report_dir / name, archive / f"coordinator-{name}")
    shutil.copy2(canonical_dir / "world-q1/durable-head.json", archive / "coordinator-durable-head.json")
    process_receipts = []
    for path in sorted(report_dir.glob("process-*.json")):
        row = json.loads(path.read_text())
        process_receipts.append({"file": path.name, **row})
    write_json(archive / "coordinator-process-receipts.json", process_receipts)
    for attempt_row in history:
        if attempt_row["status"] == "passed":
            continue
        # Failure attempts were already copied byte-for-byte at the time they
        # failed; keep the compact attempt ledger next to those retained logs.
        pass

    source_paths = [STAGE / "engine/MCEntryInterpreter.sol", STAGE / "engine/build.js",
                    STAGE / "coordinator/MCEntryCoordinator.sol", STAGE / "coordinator/build.js",
                    STAGE / "tools/build_candidate.py", STAGE / "tools/verify_source.py",
                    STAGE / "tools/generate_fixtures.py", STAGE / "tools/evm_driver.go",
                    STAGE / "tools/run_gate.py", BASE_DRIVER]
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in source_paths}
    for p in sorted((STAGE / "fixtures/src").rglob("*.java")):
        source_hashes[p.relative_to(ROOT).as_posix()] = sha(p.read_bytes())
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_report = {
        "status": "generated LOCAL1M ArrayList EVM gates passed; candidate stage acceptance and original Minecraft replay remain separate",
        "runId": run_id, "gitHead": git_head, "attemptBudgetHistory": history,
        "engineRuntimeBytes": len(bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))),
        "coordinatorRuntimeBytes": len(bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))),
        "pairedPins": pair_pins, "freshBuildCommands": [build_row, coord_row, fixture_row, direct_build],
        "hostOracleCases": len(fixture_manifest["hostOracles"]),
        "generatedCaseCount": len(fixture_manifest["cases"]),
        "maximumLegalArrayListCapacity": {"length": 65536, "evidenceCheckpoint": "arraylist-maximum-legal-capacity.checkpoint.bin"},
        "sourceSHA256": source_hashes,
        "testTransports": [
            "Direct raw-class startMain/resumeMain via geth core/vm/runtime.Call with locally preinstalled engine; no host bytecode interpreter.",
            "Canonical package route via ordinary CREATE of accepted AS0/ZI0/DI0 and paired coordinator, calling local preinstalled engine; generated matrix class only.",
        ],
        "scopeCaveats": [
            "Generated Java 8 classes only; no official Minecraft class/JAR/resource/world/checkpoint was loaded or executed.",
            "No EULA/config/world/listener setup and no original Minecraft Done marker.",
            "LOCAL engine runtime exceeds EIP-170 and was preinstalled for explicit local Call; no standard CREATE claim.",
            "Engine, bootstrap, EVM opcode/gas, consensus, and independent execution quotas were not changed by this test harness.",
            "Only the test-driver per-call gas or external wall watchdog may double, and every attempt is retained separately.",
            "Checkpoint heap audit is read-only observer code; execution and Java outcomes come from geth EVM calls.",
        ],
        "evidenceFiles": ["gate-summary.json", "reopen-summary.json", "fixture-manifest.json",
                          "paired-pins.json", "direct-q1-matrix.checkpoint.bin",
                          "arraylist-maximum-legal-capacity.checkpoint.bin",
                          "coordinator-q1-matrix.checkpoint.bin", "coordinator-durable-head.json",
                          "coordinator-world-report.json", "coordinator-start.json",
                          "coordinator-process-receipts.json"],
    }
    write_json(archive / "run-report.json", run_report)
    write_json(archive / "attempt-history.json", history)
    readme = f"""# LOCAL1M generated ArrayList EVM run `{run_id}`

This run was produced by `tools/run_gate.py` from the generated fixtures and
fresh paired engine/coordinator artifacts. It is test/harness evidence only.

- Summary: `run-report.json`
- Direct EVM schedules, Java controls, typed refusals and checkpoint heap audit: `gate-summary.json`
- Separate-process LevelDB reopen / `head` / EVM `validateCheckpoint`: `reopen-summary.json`
- Canonical generated class package through AS0/ZI0/DI0 and the freshly paired coordinator at q1: `coordinator-world-report.json`, `coordinator-durable-head.json`
- Exact final machine checkpoints and their digests are in the reports.
- Source class bytes are regenerated by `tools/generate_fixtures.py`; their SHA-256s are pinned in `fixture-manifest.json`.

No official Minecraft inputs or original checkpoint/world data were used. No
Minecraft startup, EULA, listener, or genuine `Done` result is claimed. The
engine is LOCAL preinstalled code (not an EIP-170 CREATE deployment).
"""
    (archive / "README.md").write_text(readme)
    print(json.dumps({"status": run_report["status"], "runId": run_id,
                      "archive": str(archive), "engineRuntimeSHA256": engine["codeHashes"]["runtimeSHA256"],
                      "coordinatorRuntimeKeccak256": coordinator["codeHashes"]["runtimeKeccak256"],
                      "q1JavaSteps": success["canonicalCoordinatorRoute"]["worldHead"]["jvmSteps"],
                      "q1BackingLengths": success["directGate"]["schedules"][0]["readOnlyCheckpointHeapAudit"]["arrayListBackingLengths"],
                      "q1CanonicalReadFragments": success["canonicalCoordinatorRoute"]["readFragments"],
                      "gasBudgetPerCall": success["gasBudgetPerEVMCall"],
                      "wallBudgetSeconds": success["wallBudgetSeconds"]}, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateFailure as exc:
        print(f"LOCAL1M gate failure: {exc}", file=sys.stderr)
        raise SystemExit(1)
