#!/usr/bin/env python3
"""Build P38 and run generated-only String.replaceAll plus retained regressions."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[3]
REF = STAGE / "reference/string-replaceall-bounded"
# Earlier isolated generated direct replays measured 1B/2B/4B/8B insufficient;
# 8B exhausted to a 25M-reserve shortfall. Start the full gate at the next
# coherent doubled test-only budgets so those known failures are not replayed.
INITIAL_GAS, INITIAL_WALL = 16_000_000_000, 4800
ARRAY_CLONE_GAS, ARRAY_CLONE_WALL = 1_000_000_000, 1200
RETAINED_GAS, RETAINED_WALL = 2_000_000_000, 2400
MAX_RETRIES = 5


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int,
        log: Path) -> dict[str, object]:
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with log.open("w") as stream:
            proc = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout)
        return {"command": command, "exit": proc.returncode, "timedOut": False,
                "timeoutSeconds": timeout, "wallSeconds": round(time.monotonic() - started, 3),
                "log": str(log)}
    except subprocess.TimeoutExpired:
        return {"command": command, "exit": -999, "timedOut": True,
                "timeoutSeconds": timeout, "wallSeconds": round(time.monotonic() - started, 3),
                "log": str(log)}


def copy_if_file(source: Path, target: Path) -> None:
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    if len(sys.argv) not in (2, 3) or not sys.argv[1].replace("-", "").replace("_", "").isalnum():
        raise SystemExit("usage: run_gate.py RUN_ID [REUSE_COMPLETED_P38_SCHEDULE_RUN_ID]")
    run_id = sys.argv[1]
    reuse_p38_run_id = sys.argv[2] if len(sys.argv) == 3 else None
    if reuse_p38_run_id is not None and not reuse_p38_run_id.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("reuse run id must be a simple filesystem token")
    build = ROOT / "build" / f"java-diff-mc-string-replaceall-bounded-build-{run_id}"
    fixtures = ROOT / "build" / f"java-diff-mc-string-replaceall-bounded-fixtures-{run_id}"
    results = REF / "results" / run_id
    if any(path.exists() for path in (build, fixtures, results)):
        raise SystemExit("refusing to overwrite an existing run/build/evidence path")
    results.mkdir(parents=True)
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1",
               NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    manifest: dict[str, object] = {
        "schema": 1, "runId": run_id, "profile": "MC-STRING-REPLACEALL-BOUNDED-P38",
        "sourceOnlyBaseline": "evidence/java-evm/minecraft-entry/string-replaceall-source-base-p37",
        "reuseCompletedP38ScheduleRunId": reuse_p38_run_id,
        "originalMinecraftInputsRead": False, "hostOriginalExecution": False,
        "acceptedBudgetsChanged": False, "ordinaryEvmGasAccountingChanged": False,
        "newP38SelectedTestGasBudget": INITIAL_GAS,
        "newP38InitialTestGasBudget": 1_000_000_000,
        "newP38MeasuredInsufficientBudgets": [1_000_000_000, 2_000_000_000,
                                               4_000_000_000, 8_000_000_000],
        "newP38SelectedWallBudgetSeconds": INITIAL_WALL,
        "newP38InitialWallBudgetSeconds": 1200,
        "newP38MeasuredInsufficientWallBudgets": [1200, 2400],
        "newP38MaxContinuationCalls": 40_000,
        "retainedP36MaxContinuationCalls": 20_000,
        "arrayCloneInitialTestGasBudget": ARRAY_CLONE_GAS,
        "retainedP36TestGasBudget": RETAINED_GAS, "retainedP36WallBudgetSeconds": RETAINED_WALL,
        "attempts": [],
    }
    write_json(results / "run-start.json", manifest)

    row = run([sys.executable, str(HERE / "build_candidate.py"), str(build)],
              cwd=ROOT, env=env, timeout=1200, log=build.with_suffix(".build.log"))
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"fresh P38 engine/coordinator build or source proof failed: {row}")
    artifacts = build
    engine_path = artifacts / "engine/MCEntryInterpreter.json"
    coordinator_path = artifacts / "coordinator/MCEntryCoordinator.json"
    engine = json.loads(engine_path.read_text())
    coordinator = json.loads(coordinator_path.read_text())
    engine_code = bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))
    coordinator_code = bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))
    source_proof = json.loads((build / "source-proof.json").read_text())
    copy_if_file(build / "source-proof.json", results / "source-proof.json")
    fixture_build_log = build / "logs" / "fixture-build.log"
    fixture_build_log.parent.mkdir(parents=True, exist_ok=True)
    row = run([sys.executable, str(HERE / "generate_fixtures.py"), str(fixtures)],
              cwd=ROOT, env=env, timeout=900, log=fixture_build_log)
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"generated Java 8 fixture/oracle build failed: {row}")
    fixture_manifest_path = fixtures / "fixture-manifest.json"
    fixture_manifest = json.loads(fixture_manifest_path.read_text())
    required = {"StringReplaceAllMatrix", "StringReplaceAllUnsupported",
                "string-replaceall-surrogate-unsupported", "matcher-raw-platform-replacement",
                "PatternCompileMatrix", "PatternSyntaxFailures", "raw150-envelope",
                "raw-bytes-exact", "raw151-refusal", "ArrayCloneMatrix"}
    if not required.issubset(fixture_manifest["cases"]):
        raise RuntimeError("generated fixture manifest omitted a P38 or retained regression case")
    for name in ("StringReplaceAllMatrix", "StringReplaceAllUnsupported",
                 "StringReplaceAllSurrogateUnsupported", "MatcherRawReplacementMain",
                 "PatternCompileMatrix", "ArrayCloneMatrix"):
        if fixture_manifest["hostOracles"].get(name, {}).get("exit") != 0:
            raise RuntimeError(f"Java 8 generated host oracle missing/failed: {name}")
    manifest["generatedFixtureManifestSHA256"] = sha(fixture_manifest_path.read_bytes())
    copy_if_file(fixture_manifest_path, results / "fixture-manifest.json")
    copy_if_file(build / "build-summary.json", results / "build-summary.json")
    copy_if_file(build / "source-proof.log", results / "source-proof.log")

    driver = build / "evm_driver"
    relative = "./" + HERE.relative_to(ROOT).as_posix()
    row = run(["go", "build", "-trimpath", "-o", str(driver), relative],
              cwd=ROOT, env=env, timeout=600, log=build / "go-driver-build.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"generated EVM driver build failed: {row}")

    shared = [str(engine_path), str(coordinator_path), str(fixture_manifest_path), str(fixtures)]

    def execute(label: str, mode: str, gas: int, wall: int, output: Path, attempt: int) -> dict[str, object]:
        log = build / "logs" / f"{label}-attempt-{attempt}.log"
        row_out = run([str(driver), mode, *shared, str(output), str(gas)],
                      cwd=ROOT, env=env, timeout=wall + 5, log=log)
        result: dict[str, object] = {"label": label, "mode": mode, "gasBudget": gas,
                                     "wallBudgetSeconds": wall, **row_out}
        if row_out["timedOut"]:
            result["classification"] = "test-only-wall-budget"
        elif row_out["exit"] == 42:
            failure_path = output / "gate-failure.json"
            failure = json.loads(failure_path.read_text()) if failure_path.is_file() else {}
            detail = failure.get("failure", {})
            result["classification"] = detail.get("classification", "unclassified")
            result["failure"] = detail
        elif row_out["exit"] != 0:
            result["classification"] = "semantic-or-harness-failure"
            failure_path = output / "gate-failure.json"
            result["failure"] = json.loads(failure_path.read_text()).get("failure") if failure_path.is_file() else None
        else:
            result["classification"] = "passed"
        manifest["attempts"].append(result)
        write_json(results / "run-progress.json", manifest)
        return result

    def run_with_reopen(label: str, mode: str, gas: int, wall: int) -> tuple[int, int, Path]:
        for attempt in range(1, MAX_RETRIES + 1):
            output = build / f"{label}-attempt-{attempt}"
            row_out = execute(label, mode, gas, wall, output, attempt)
            if row_out["classification"] == "passed":
                reopen = execute(label + "-fresh-reopen", "reopen", gas, wall, output, attempt)
                copy_if_file(output / "reopen-summary.json", results / f"{label}-attempt-{attempt}/reopen-summary.json")
                copy_if_file(output / "gate-failure.json", results / f"{label}-attempt-{attempt}/reopen-failure.json")
                if reopen["classification"] == "passed":
                    copy_if_file(output / f"{mode}-gate-summary.json", results / f"{label}-attempt-{attempt}/{mode}-gate-summary.json")
                    copy_if_file(output / "gate-summary.json", results / f"{label}-attempt-{attempt}/gate-summary.json")
                    copy_if_file(output / "array-clone-gate-summary.json", results / f"{label}-attempt-{attempt}/array-clone-gate-summary.json")
                    copy_if_file(build / "logs" / f"{label}-attempt-{attempt}.log", results / f"{label}-attempt-{attempt}/driver.log")
                    copy_if_file(build / "logs" / f"{label}-fresh-reopen-attempt-{attempt}.log", results / f"{label}-attempt-{attempt}/reopen.log")
                    return gas, wall, output
                row_out = reopen
            copy_if_file(output / "gate-failure.json", results / f"{label}-attempt-{attempt}/gate-failure.json")
            copy_if_file(build / "logs" / f"{label}-attempt-{attempt}.log", results / f"{label}-attempt-{attempt}/driver.log")
            if row_out["classification"] == "test-only-gas-budget":
                gas *= 2
            elif row_out["classification"] == "test-only-wall-budget":
                wall *= 2
            else:
                raise RuntimeError(f"{label} semantic/harness gate failed: {row_out}")
        raise RuntimeError(f"{label} exceeded the adaptive test-budget retry count")

    def reuse_completed_p38_schedule(reuse_id: str) -> Path:
        old_results = REF / "results" / reuse_id
        old_build = ROOT / "build" / f"java-diff-mc-string-replaceall-bounded-build-{reuse_id}"
        old_output = old_build / "string-replaceall-attempt-1"
        old_gate = old_results / "string-replaceall-attempt-1/gate-failure.json"
        old_progress_path = old_results / "run-progress.json"
        old_proof_path = old_results / "source-proof.json"
        if not all(path.is_file() for path in (old_gate, old_progress_path, old_proof_path,
                                                old_output / "reopen-requests/q1-string-replaceall-matrix.json",
                                                old_output / "checkpoints/q1-string-replaceall-matrix.checkpoint.bin")):
            raise RuntimeError(f"completed P38 schedule reuse evidence/state missing for {reuse_id}")
        prior_progress = json.loads(old_progress_path.read_text())
        prior_proof = json.loads(old_proof_path.read_text())
        prior_gate = json.loads(old_gate.read_text())
        expected_error = "smaller-quantum replaceAll schedule used fewer calls: q65536-string-replaceall-matrix=1 q4096-string-replaceall-matrix=9"
        prior_run = next((row for row in reversed(prior_progress.get("attempts", []))
                          if row.get("label") == "string-replaceall" and row.get("mode") == "replaceall" and
                          row.get("failure", {}).get("error") == expected_error), None)
        if prior_run is None or prior_run.get("classification") != "semantic-or-harness-failure":
            raise RuntimeError("reused P38 schedule source is not the recorded comparator-only harness failure")
        if prior_gate.get("failure", {}).get("error") != expected_error:
            raise RuntimeError("refusing to reuse P38 schedule with a different failure cause")
        current_fixture_sha = sha(fixture_manifest_path.read_bytes())
        if prior_progress.get("generatedFixtureManifestSHA256") != current_fixture_sha:
            raise RuntimeError("P38 schedule reuse fixture manifest differs from current generated inputs")
        if (prior_proof.get("candidateBootstrapRoot") != source_proof.get("candidateBootstrapRoot") or
                prior_proof.get("engine", {}).get("runtimeSHA256") != source_proof.get("engine", {}).get("runtimeSHA256") or
                prior_proof.get("coordinator", {}).get("runtimeSHA256") != source_proof.get("coordinator", {}).get("runtimeSHA256")):
            raise RuntimeError("P38 schedule reuse source proof differs from the fresh current build")
        if (prior_gate.get("engineRuntimeSHA256") != engine["codeHashes"]["runtimeSHA256"] or
                prior_gate.get("engineRuntimeKeccak256", "").removeprefix("0x") != engine["codeHashes"]["runtimeKeccak256"] or
                prior_gate.get("coordinatorRuntimeSHA256") != coordinator["codeHashes"]["runtimeSHA256"] or
                prior_gate.get("coordinatorRuntimeKeccak256", "").removeprefix("0x") != coordinator["codeHashes"]["runtimeKeccak256"] or
                prior_gate.get("localGasBudget") != INITIAL_GAS):
            raise RuntimeError("P38 schedule reuse engine/coordinator/gas identity mismatch")
        rows = prior_gate.get("schedules", [])
        expected = [("q65536-string-replaceall-matrix", 65536),
                    ("q4096-string-replaceall-matrix", 4096),
                    ("q7-string-replaceall-matrix", 7),
                    ("q1-string-replaceall-matrix", 1)]
        if len(rows) != len(expected):
            raise RuntimeError("P38 schedule reuse report lacks all four quantum schedules")
        base_final = None
        previous_calls = -1
        compact_rows = []
        for row, (name, quantum) in zip(rows, expected):
            final = row.get("final", {})
            audit = row.get("readOnlyCheckpointHeapAudit", {})
            if (row.get("name") != name or row.get("quantum") != quantum or
                    row.get("callLimit") != 40_000 or row.get("callCount", 0) > 40_000 or
                    row.get("rawCount") != 1 or row.get("rawBytes") != 2446 or
                    row.get("bootstrapCount") != 104 or row.get("diagnosticClassCount") != 105 or
                    final.get("lifecycle") != 2 or final.get("outcome") != 2 or
                    final.get("javaKind") != 0 or final.get("javaRef") != 0 or final.get("javaClass", "") or
                    row.get("checkpointBytes", 0) > 2_097_152 or
                    not audit.get("allMatcherLinksValid") or audit.get("matcherClassIndex") != 104 or
                    audit.get("matcherObjectCount", 0) <= 0 or audit.get("patternObjectCount", 0) <= 0):
                raise RuntimeError(f"invalid terminal/class/heap receipt in reused P38 schedule {name}")
            if row.get("callCount", 0) < previous_calls:
                raise RuntimeError("cached P38 schedule call counts are not monotone for descending quantum")
            previous_calls = row["callCount"]
            if base_final is None:
                base_final = final
            elif any(final.get(key) != base_final.get(key) for key in
                     ("machineStateRoot", "vfsStateRoot", "totalJvmSteps", "totalInternalSteps")):
                raise RuntimeError("cached P38 q1/q7/q65536/q4096 terminal roots or step totals differ")
            if audit != rows[0].get("readOnlyCheckpointHeapAudit"):
                raise RuntimeError("cached P38 Pattern/Matcher heap audit differs across quantum")
            compact_rows.append({key: row[key] for key in
                                 ("name", "quantum", "callCount", "callLimit", "totalGas", "maxCallGas",
                                  "wallMs", "checkpointBytes", "checkpointSHA256")})
        if prior_gate.get("failure", {}).get("case") != "unknown" or prior_gate.get("localGasBudget") != INITIAL_GAS:
            raise RuntimeError("cached P38 schedule report has an unexpected terminal failure")
        q1 = rows[-1]
        request_path = old_output / "reopen-requests/q1-string-replaceall-matrix.json"
        request = json.loads(request_path.read_text())
        checkpoint = old_output / "checkpoints/q1-string-replaceall-matrix.checkpoint.bin"
        if (sha(checkpoint.read_bytes()) != q1.get("checkpointSHA256") or
                request.get("checkpointRoot") != q1.get("final", {}).get("checkpointRoot") or
                request.get("machineStateRoot") != q1.get("final", {}).get("machineStateRoot") or
                request.get("epoch") != q1.get("final", {}).get("epoch") or
                request.get("gas") != INITIAL_GAS or
                request.get("preReopenPID") != prior_gate.get("processId")):
            raise RuntimeError("cached P38 q1 reopen request/checkpoint does not bind to its terminal receipt")

        source_gate_sha = sha(old_gate.read_bytes())
        reused_summary = {
            "schema": 1, "status": "reused completed EVM schedules; corrected only the post-schedule call-count assertion",
            "sourceRunId": reuse_id, "sourceGateFailureSHA256": source_gate_sha,
            "sourceFixtureManifestSHA256": current_fixture_sha,
            "bootstrapRoot": source_proof["candidateBootstrapRoot"],
            "engineRuntimeSHA256": engine["codeHashes"]["runtimeSHA256"],
            "coordinatorRuntimeSHA256": coordinator["codeHashes"]["runtimeSHA256"],
            "gasBudget": INITIAL_GAS, "scheduleRows": compact_rows,
            "crossQuantumMachineVfsAndHeapEquivalent": True,
            "terminalOutcome": {key: base_final[key] for key in
                                 ("lifecycle", "outcome", "javaKind", "totalJvmSteps", "totalInternalSteps",
                                  "machineStateRoot", "vfsStateRoot")},
            "q1CheckpointSHA256": q1["checkpointSHA256"],
            "scheduleWallSeconds": prior_run.get("wallSeconds"),
        }
        reuse_dir = results / "string-replaceall-attempt-1"
        reuse_dir.mkdir(parents=True, exist_ok=True)
        copy_if_file(old_gate, reuse_dir / "schedule-source-gate-failure.json")
        copy_if_file(request_path, reuse_dir / "reopen-request.json")
        copy_if_file(checkpoint, reuse_dir / "q1-terminal-checkpoint.bin")
        write_json(reuse_dir / "reused-schedule-summary.json", reused_summary)
        manifest["attempts"].append({
            "label": "string-replaceall-reused-completed-schedules", "mode": "verified cached EVM receipts",
            "gasBudget": INITIAL_GAS, "wallBudgetSeconds": prior_run.get("wallBudgetSeconds"),
            "wallSeconds": prior_run.get("wallSeconds"), "classification": "passed",
            "sourceRunId": reuse_id, "sourceGateFailureSHA256": source_gate_sha,
        })
        write_json(results / "run-progress.json", manifest)

        reopened = execute("string-replaceall-fresh-reopen", "reopen", INITIAL_GAS, INITIAL_WALL,
                           old_output, 1)
        if reopened["classification"] != "passed":
            raise RuntimeError(f"reused P38 terminal failed distinct-process reopen: {reopened}")
        reopen_path = old_output / "reopen-summary.json"
        if not reopen_path.is_file():
            raise RuntimeError("reused P38 fresh-process reopen did not produce its summary")
        copy_if_file(reopen_path, reuse_dir / "reopen-summary.json")

        controls_output = build / "string-replaceall-controls-reuse"
        controls_row = None
        controls_gas, controls_wall = INITIAL_GAS, INITIAL_WALL
        for attempt in range(1, MAX_RETRIES + 1):
            controls_output = build / f"string-replaceall-controls-reuse-attempt-{attempt}"
            controls_row = execute("string-replaceall-controls", "replaceall-controls",
                                   controls_gas, controls_wall, controls_output, attempt)
            if controls_row["classification"] == "passed":
                break
            if controls_row["classification"] == "test-only-gas-budget":
                controls_gas *= 2
            elif controls_row["classification"] == "test-only-wall-budget":
                controls_wall *= 2
            else:
                raise RuntimeError(f"reused P38 refusal controls failed: {controls_row}")
        if controls_row is None or controls_row["classification"] != "passed":
            raise RuntimeError("reused P38 refusal controls exceeded adaptive test-budget retries")
        controls_summary_path = controls_output / "string-replaceall-controls-summary.json"
        controls_summary = json.loads(controls_summary_path.read_text())
        expected_controls = {"valid-quantifier-refusal-q1", "valid-quantifier-refusal-q7",
                             "surrogate-input-refusal-q1", "surrogate-input-refusal-q7",
                             "raw-matcher-replacement-refusal"}
        if ({row.get("name") for row in controls_summary.get("controls", [])} != expected_controls or
                not all(row.get("atomic") for row in controls_summary.get("controls", []))):
            raise RuntimeError("reused P38 refusal controls did not produce all atomic refusal receipts")
        copy_if_file(controls_summary_path, reuse_dir / "controls-summary.json")
        reused_summary["freshReopen"] = json.loads(reopen_path.read_text())
        reused_summary["refusalControls"] = controls_summary.get("controls", [])
        write_json(reuse_dir / "reused-schedule-summary.json", reused_summary)
        manifest["stringReplaceAllGate"] = {
            "status": "passed using byte-identical completed EVM schedules, new-process reopen, and fresh refusal controls",
            "gasBudget": INITIAL_GAS, "wallBudgetSeconds": INITIAL_WALL,
            "scheduleSourceRunId": reuse_id,
            "directSummary": str(reuse_dir / "reused-schedule-summary.json"),
        }
        write_json(results / "run-progress.json", manifest)
        return reuse_dir / "reused-schedule-summary.json"

    if reuse_p38_run_id is None:
        replace_gas, replace_wall, replace_output = run_with_reopen(
            "string-replaceall", "replaceall", INITIAL_GAS, INITIAL_WALL)
        manifest["stringReplaceAllGate"] = {
            "status": "passed", "gasBudget": replace_gas, "wallBudgetSeconds": replace_wall,
            "directSummary": str(replace_output / "string-replaceall-gate-summary.json"),
        }
    else:
        reuse_summary = reuse_completed_p38_schedule(reuse_p38_run_id)
        replace_gas, replace_wall = INITIAL_GAS, INITIAL_WALL
        replace_output = reuse_summary.parent

    clone_gas, clone_wall, clone_output = run_with_reopen(
        "array-clone", "array-clone", ARRAY_CLONE_GAS, ARRAY_CLONE_WALL)
    manifest["arrayCloneGate"] = {
        "status": "passed", "gasBudget": clone_gas, "wallBudgetSeconds": clone_wall,
        "directSummary": str(clone_output / "array-clone-gate-summary.json"),
    }

    retained_gas, retained_wall, retained_output = run_with_reopen(
        "retained-p36", "gate", RETAINED_GAS, RETAINED_WALL)
    manifest["retainedP36Gate"] = {
        "status": "passed", "gasBudget": retained_gas, "wallBudgetSeconds": retained_wall,
        "directSummary": str(retained_output / "gate-summary.json"),
    }

    coordinator_pass = False
    coordinator_gas, coordinator_wall = retained_gas, retained_wall
    for attempt in range(1, MAX_RETRIES + 1):
        output = build / f"coordinator-attempt-{attempt}"
        row_out = execute("coordinator", "coordinator", coordinator_gas, coordinator_wall, output, attempt)
        copy_if_file(output / "coordinator-summary.json", results / f"coordinator-attempt-{attempt}/coordinator-summary.json")
        copy_if_file(output / "gate-failure.json", results / f"coordinator-attempt-{attempt}/gate-failure.json")
        copy_if_file(build / "logs" / f"coordinator-attempt-{attempt}.log", results / f"coordinator-attempt-{attempt}/driver.log")
        if row_out["classification"] == "passed":
            coordinator_pass = True
            break
        if row_out["classification"] == "test-only-gas-budget":
            coordinator_gas *= 2
        elif row_out["classification"] == "test-only-wall-budget":
            coordinator_wall *= 2
        else:
            raise RuntimeError(f"P38 paired coordinator route failed: {row_out}")
    if not coordinator_pass:
        raise RuntimeError("coordinator route exceeded the adaptive test-budget retry count")
    manifest["coordinatorRoute"] = {"status": "passed", "gasBudget": coordinator_gas,
                                    "wallBudgetSeconds": coordinator_wall}

    manifest["sourceProof"] = {
        "status": source_proof["status"], "bootstrapRoot": source_proof["candidateBootstrapRoot"],
        "bootstrapCount": source_proof["bootstrapCount"], "unchangedPriorLeaves": source_proof["unchangedPriorLeaves"],
        "changedPriorSlots": source_proof["changedPriorSlots"],
        "engineRuntimeBytes": source_proof["engine"]["runtimeBytes"],
        "engineRuntimeSHA256": source_proof["engine"]["runtimeSHA256"],
        "coordinatorRuntimeBytes": source_proof["coordinator"]["runtimeBytes"],
        "coordinatorRuntimeSHA256": source_proof["coordinator"]["runtimeSHA256"],
    }
    manifest["engine"] = {"sourceSHA256": engine["sourceHashes"]["MCEntryInterpreter.sol"],
                          "runtimeBytes": len(engine_code), **engine["codeHashes"]}
    manifest["coordinator"] = {"sourceSHA256": coordinator["sourceHashes"]["MCEntryCoordinator.sol"],
                               "runtimeBytes": len(coordinator_code), **coordinator["codeHashes"]}
    manifest["status"] = "generated-only P38 String.replaceAll, fresh-reopen, retained P36/P37, and coordinator gates passed; no Minecraft execution"
    write_json(results / "run-summary.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("status", "runId", "stringReplaceAllGate",
                                                "arrayCloneGate", "retainedP36Gate", "coordinatorRoute",
                                                "sourceProof", "engine", "coordinator")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
