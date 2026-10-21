#!/usr/bin/env python3
"""Generated-only array clone + retained P36 EVM gates; never reads original Minecraft data."""
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

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[3]
EVIDENCE = STAGE / "reference/array-clone-intrinsic"
INITIAL_GAS = 1_000_000_000
INITIAL_WALL = 1200
RETAINED_P36_GAS = 2_000_000_000
RETAINED_P36_WALL = 2400
MAX_RETRIES = 4


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def copy_if_file(source: Path, target: Path) -> None:
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    if len(sys.argv) not in (2, 3) or not re.fullmatch(r"[A-Za-z0-9._-]+", sys.argv[1]):
        raise SystemExit("usage: run_gate.py RUN_ID [--clone-only] (simple filesystem token)")
    clone_only = len(sys.argv) == 3 and sys.argv[2] == "--clone-only"
    if len(sys.argv) == 3 and not clone_only:
        raise SystemExit("the only optional scope is --clone-only")
    run_id = sys.argv[1]
    build = ROOT / "build" / f"java-diff-mc-array-clone-intrinsic-{run_id}"
    fixtures = ROOT / "build" / f"java-diff-mc-array-clone-intrinsic-fixtures-{run_id}"
    results = EVIDENCE / "results" / run_id
    if any(path.exists() for path in (build, fixtures, results)):
        raise SystemExit("refusing to overwrite an existing run/build/evidence path")
    build.mkdir(parents=True)
    (build / "logs").mkdir()
    results.mkdir(parents=True)
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1",
               NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    manifest = {
        "schema": 1,
        "runId": run_id,
        "profile": "MC-ARRAY-CLONE-INTRINSIC-P37",
        "sourceOnlyBaseline": "evidence/java-evm/minecraft-entry/array-clone-source-base-p36",
        "originalMinecraftInputsRead": False,
        "hostOriginalExecution": False,
        "acceptedBudgetsChanged": False,
        "ordinaryEvmGasAccountingChanged": False,
        "initialCloneOnlyTestGasBudget": INITIAL_GAS,
        "initialCloneOnlyWallBudgetSeconds": INITIAL_WALL,
        "retainedP36TestGasBudget": RETAINED_P36_GAS,
        "retainedP36WallBudgetSeconds": RETAINED_P36_WALL,
        "requestedScope": "clone-only with exact fixture/P36 prior cross-check" if clone_only else "full retained P36 regression",
        "attempts": [],
    }
    write_json(results / "run-start.json", manifest)

    engine_artifacts = build / "engine"
    coordinator_artifacts = build / "coordinator"
    build_env = dict(env, ARRAY_CLONE_ARTIFACT_DIR=str(engine_artifacts))
    row = run(["node", str(STAGE / "bootstrap/array-clone-intrinsic/build-engine.js")],
              cwd=ROOT, env=build_env, timeout=900, log=build / "logs/engine-build.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"candidate engine build failed: {row}")
    engine = json.loads((engine_artifacts / "MCEntryInterpreter.json").read_text())
    engine_code = bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))
    if len(engine_code) >= 1048576 or sha(engine_code) != engine["codeHashes"]["runtimeSHA256"]:
        raise RuntimeError("candidate engine codehash/runtime-cap validation failed")
    engine_keccak = engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x")
    coordinator_source = (STAGE / "bootstrap/array-clone-intrinsic/MCEntryCoordinator.sol").read_text()
    if engine_keccak not in coordinator_source:
        raise RuntimeError("paired coordinator does not pin candidate engine runtime codehash")

    coord_env = dict(env, ARRAY_CLONE_ARTIFACT_DIR=str(coordinator_artifacts))
    row = run(["node", str(STAGE / "bootstrap/array-clone-intrinsic/build-coordinator.js")],
              cwd=ROOT, env=coord_env, timeout=900, log=build / "logs/coordinator-build.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"candidate coordinator build failed: {row}")
    coordinator = json.loads((coordinator_artifacts / "MCEntryCoordinator.json").read_text())
    coordinator_code = bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))
    if len(coordinator_code) > 24576 or sha(coordinator_code) != coordinator["codeHashes"]["runtimeSHA256"]:
        raise RuntimeError("coordinator ordinary-CREATE code-size/codehash validation failed")

    proof_env = dict(env, ARRAY_CLONE_ENGINE_ARTIFACT_DIR=str(engine_artifacts),
                     ARRAY_CLONE_COORDINATOR_ARTIFACT_DIR=str(coordinator_artifacts),
                     ARRAY_CLONE_SOURCE_PROOF_OUTPUT=str(results / "source-proof.json"))
    row = run([sys.executable,
               str(STAGE / "reference/array-clone-intrinsic/verify_source.py")],
              cwd=ROOT, env=proof_env, timeout=180,
              log=build / "logs/source-proof.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"candidate source/root/codehash proof failed: {row}")

    row = run([sys.executable,
               str(STAGE / "tools/array-clone-intrinsic/generate_fixtures.py"), str(fixtures)],
              cwd=ROOT, env=env, timeout=900, log=build / "logs/fixture-build.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"generated Java 8 fixture/oracle generation failed: {row}")
    fixture_manifest = json.loads((fixtures / "fixture-manifest.json").read_text())
    clone_cases = fixture_manifest["cases"]
    required = {
        "ArrayCloneMatrix", "ArrayCloneMaximumLength", "ArrayCloneArrayQuotaOOM",
        "ArrayCloneElementQuotaOOM", "ArrayCloneNullReceiver", "clone-unsupported-array-member",
        "clone-wrong-array-descriptor", "clone-malformed-array-owner",
        "clone-incompatible-array-owner", "object-clone-protected-control",
        "clone-empty-owner-control", "object-clone-virtual-control", "raw-bytes-exact",
    }
    if not required.issubset(clone_cases) or clone_cases["raw-bytes-exact"]["entryClass"] != "ArrayCloneMatrix":
        raise RuntimeError("generated fixture manifest omitted clone proofs or canonical entry class")
    for name in ("ArrayCloneMatrix", "ArrayCloneMaximumLength", "ArrayCloneObjectCloneProbe",
                 "ArrayCloneNullReceiver"):
        if fixture_manifest["hostOracles"].get(name, {}).get("exit") != 0:
            raise RuntimeError(f"Java 8 generated host oracle missing/failed: {name}")
    shutil.copy2(fixtures / "fixture-manifest.json", results / "fixture-manifest.json")
    if clone_only:
        prior_summary_path = EVIDENCE / "results/clone-reopen-v1/run-summary.json"
        prior_fixture_path = EVIDENCE / "fixture-manifest-p36-prior-clone-reopen-v1.json"
        prior_summary_bytes = prior_summary_path.read_bytes()
        prior_summary = json.loads(prior_summary_bytes)
        prior_fixture_bytes = prior_fixture_path.read_bytes()
        prior_fixture = json.loads(prior_fixture_bytes)
        if prior_summary["status"] != "generated array-clone, retained P36, fresh-process reopen, and canonical coordinator gates passed":
            raise RuntimeError("referenced retained-P36 run is not a completed full gate")
        if prior_summary["engine"]["runtimeSHA256"] != engine["codeHashes"]["runtimeSHA256"]:
            raise RuntimeError("referenced retained-P36 run used a different engine runtime")
        if sha(prior_fixture_bytes) != prior_summary["generatedFixtureManifestSHA256"]:
            raise RuntimeError("referenced P36 fixture manifest hash differs from its accepted run summary")
        new_clone_source = "fixtures/src/ArrayCloneNullReceiver.java"
        old_sources = prior_fixture["sourceHashes"]
        current_sources = dict(fixture_manifest["sourceHashes"])
        current_sources.pop(new_clone_source, None)
        if old_sources != current_sources:
            raise RuntimeError("P36/previous-clone Java source hashes changed beyond the new null oracle")
        if prior_fixture["cases"] != {k: fixture_manifest["cases"][k] for k in prior_fixture["cases"]}:
            raise RuntimeError("a prior P36/clone fixture bundle changed since the retained full gate")
        old_class_hashes = prior_fixture["fixtureClassHashes"]
        current_class_hashes = dict(fixture_manifest["fixtureClassHashes"])
        current_class_hashes.pop("ArrayCloneNullReceiver.class", None)
        if old_class_hashes != current_class_hashes:
            raise RuntimeError("compiled P36/previous-clone Java class bytes changed beyond the new null oracle")
        manifest["retainedP36PriorReference"] = {
            "status": "previously-verified on the identical engine and byte-identical prior fixtures",
            "sourceRun": "clone-reopen-v1",
            "sourceRunSummarySHA256": sha(prior_summary_bytes),
            "sourceFixtureManifestSHA256": sha(prior_fixture_bytes),
            "sameEngineRuntimeSHA256": engine["codeHashes"]["runtimeSHA256"],
            "priorJavaSourceHashesUnchanged": True,
            "priorBundleManifestsUnchanged": True,
            "priorCompiledJavaClassHashesUnchanged": True,
            "onlyAddedJavaSource": new_clone_source,
        }

    driver = build / "evm_driver"
    relative = "./" + (HERE.relative_to(ROOT)).as_posix()
    row = run(["go", "build", "-trimpath", "-o", str(driver), relative],
              cwd=ROOT, env=env, timeout=600, log=build / "logs/go-driver-build.log")
    if row["exit"] != 0 or row["timedOut"]:
        raise RuntimeError(f"generated EVM driver build failed: {row}")

    shared = [str(engine_artifacts / "MCEntryInterpreter.json"),
              str(coordinator_artifacts / "MCEntryCoordinator.json"),
              str(fixtures / "fixture-manifest.json"), str(fixtures)]

    def execute(label: str, mode: str, gas: int, wall: int, output: Path, attempt: int) -> dict:
        log = build / "logs" / f"{label}-attempt-{attempt}.log"
        args = [str(driver), mode, *shared, str(output), str(gas)]
        result = run(args, cwd=ROOT, env=env, timeout=wall + 5, log=log)
        row_out = {"label": label, "mode": mode, "gasBudget": gas,
                   "wallBudgetSeconds": wall, **result}
        if result["timedOut"]:
            row_out["classification"] = "test-only-wall-budget"
        elif result["exit"] == 42:
            failure_path = output / "gate-failure.json"
            failure = json.loads(failure_path.read_text()) if failure_path.is_file() else {}
            row_out["classification"] = failure.get("failure", {}).get("classification", "unclassified")
            row_out["failure"] = failure.get("failure")
        elif result["exit"] != 0:
            row_out["classification"] = "semantic-or-harness-failure"
            failure_path = output / "gate-failure.json"
            row_out["failure"] = json.loads(failure_path.read_text()) if failure_path.is_file() else None
        else:
            row_out["classification"] = "passed"
        manifest["attempts"].append(row_out)
        write_json(results / "run-progress.json", manifest)
        return row_out

    def run_clone_with_adaptive_budgets() -> tuple[int, int, Path]:
        gas, wall = INITIAL_GAS, INITIAL_WALL
        for attempt in range(1, MAX_RETRIES + 1):
            output = build / f"clone-attempt-{attempt}"
            row = execute("array-clone", "array-clone", gas, wall, output, attempt)
            evidence_dir = results / f"clone-attempt-{attempt}"
            copy_if_file(output / "array-clone-gate-summary.json", evidence_dir / "array-clone-gate-summary.json")
            copy_if_file(output / "gate-failure.json", evidence_dir / "gate-failure.json")
            copy_if_file(build / "logs" / f"array-clone-attempt-{attempt}.log", evidence_dir / "driver.log")
            if row["classification"] == "passed":
                reopen_output = output
                reopen_row = execute("array-clone-reopen", "reopen", gas, wall, reopen_output, attempt)
                reopen_evidence = results / f"clone-attempt-{attempt}"
                copy_if_file(reopen_output / "reopen-summary.json", reopen_evidence / "reopen-summary.json")
                copy_if_file(reopen_output / "gate-failure.json", reopen_evidence / "reopen-failure.json")
                copy_if_file(build / "logs" / f"array-clone-reopen-attempt-{attempt}.log", reopen_evidence / "reopen.log")
                if reopen_row["classification"] == "passed":
                    return gas, wall, output
                row = reopen_row
            if row["classification"] == "test-only-gas-budget":
                gas *= 2
            elif row["classification"] == "test-only-wall-budget":
                wall *= 2
            else:
                raise RuntimeError(f"array-clone semantic/harness gate failed: {row}")
        raise RuntimeError("array-clone gate exceeded its adaptive test-budget retry count")

    clone_gas, clone_wall, clone_output = run_clone_with_adaptive_budgets()
    manifest["cloneGate"] = {"status": "passed", "gasBudget": clone_gas,
                              "wallBudgetSeconds": clone_wall,
                              "directSummary": str(clone_output / "array-clone-gate-summary.json")}

    legacy_gas, legacy_wall = RETAINED_P36_GAS, RETAINED_P36_WALL
    if clone_only:
        prior_gate = prior_summary["retainedP36Gate"]
        if prior_gate.get("status") != "passed":
            raise RuntimeError("referenced prior retained-P36 gate did not pass")
        manifest["retainedP36Gate"] = {
            **prior_gate,
            "status": "cross-referenced-identical-engine-and-byte-identical-prior-fixtures",
            "sourceRun": "clone-reopen-v1",
        }
    else:
        # Retain the exact P36 regression matrix, including its previously measured
        # 65,536-capacity fixture, at its separately labeled 2B/2400s test-only budget.
        legacy_pass = False
        for attempt in range(1, MAX_RETRIES + 1):
            output = build / f"retained-p36-attempt-{attempt}"
            row = execute("retained-p36", "gate", legacy_gas, legacy_wall, output, attempt)
            evidence_dir = results / f"retained-p36-attempt-{attempt}"
            copy_if_file(output / "gate-summary.json", evidence_dir / "gate-summary.json")
            copy_if_file(output / "gate-failure.json", evidence_dir / "gate-failure.json")
            copy_if_file(build / "logs" / f"retained-p36-attempt-{attempt}.log", evidence_dir / "driver.log")
            if row["classification"] == "passed":
                reopen_output = output
                reopen_row = execute("retained-p36-reopen", "reopen", legacy_gas, legacy_wall,
                                     reopen_output, attempt)
                copy_if_file(reopen_output / "reopen-summary.json", evidence_dir / "reopen-summary.json")
                copy_if_file(reopen_output / "gate-failure.json", evidence_dir / "reopen-failure.json")
                copy_if_file(build / "logs" / f"retained-p36-reopen-attempt-{attempt}.log", evidence_dir / "reopen.log")
                if reopen_row["classification"] == "passed":
                    legacy_pass = True
                    break
                row = reopen_row
            if row["classification"] == "test-only-gas-budget":
                legacy_gas *= 2
            elif row["classification"] == "test-only-wall-budget":
                legacy_wall *= 2
            else:
                raise RuntimeError(f"retained P36 generated regression gate failed: {row}")
        if not legacy_pass:
            raise RuntimeError("retained P36 gate exceeded its adaptive test-budget retry count")
        manifest["retainedP36Gate"] = {"status": "passed", "gasBudget": legacy_gas,
                                       "wallBudgetSeconds": legacy_wall}

    # The P36 ordinary-CREATE coordinator route uses the exact 150-class/1,063,930-byte
    # generated bundle whose entry class is ArrayCloneMatrix.
    coordinator_pass = False
    coordinator_gas, coordinator_wall = legacy_gas, legacy_wall
    for attempt in range(1, MAX_RETRIES + 1):
        output = build / f"canonical-coordinator-attempt-{attempt}"
        row = execute("canonical-coordinator", "coordinator", coordinator_gas,
                      coordinator_wall, output, attempt)
        evidence_dir = results / f"canonical-coordinator-attempt-{attempt}"
        copy_if_file(output / "coordinator-summary.json", evidence_dir / "coordinator-summary.json")
        copy_if_file(output / "gate-failure.json", evidence_dir / "gate-failure.json")
        copy_if_file(build / "logs" / f"canonical-coordinator-attempt-{attempt}.log", evidence_dir / "driver.log")
        if row["classification"] == "passed":
            coordinator_pass = True
            break
        if row["classification"] == "test-only-gas-budget":
            coordinator_gas *= 2
        elif row["classification"] == "test-only-wall-budget":
            coordinator_wall *= 2
        else:
            raise RuntimeError(f"canonical ArrayClone coordinator route failed: {row}")
    if not coordinator_pass:
        raise RuntimeError("canonical coordinator route exceeded its adaptive test-budget retry count")

    manifest["canonicalCoordinatorRoute"] = {"status": "passed", "gasBudget": coordinator_gas,
                                              "wallBudgetSeconds": coordinator_wall}
    manifest["engine"] = {
        "sourceSHA256": engine["sourceHashes"]["MCEntryInterpreter.sol"],
        "runtimeBytes": len(engine_code),
        **engine["codeHashes"],
    }
    manifest["coordinator"] = {
        "sourceSHA256": coordinator["sourceHashes"]["MCEntryCoordinator.sol"],
        "runtimeBytes": len(coordinator_code),
        **coordinator["codeHashes"],
    }
    manifest["generatedFixtureManifestSHA256"] = sha((fixtures / "fixture-manifest.json").read_bytes())
    manifest["status"] = (
        "generated array-clone, fresh-process reopen, canonical coordinator, and identical-fixture P36 cross-reference passed"
        if clone_only else
        "generated array-clone, retained P36, fresh-process reopen, and canonical coordinator gates passed"
    )
    write_json(results / "run-summary.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("status", "runId", "cloneGate", "retainedP36Gate",
                                               "canonicalCoordinatorRoute", "engine", "coordinator")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
