#!/usr/bin/env python3
"""Genuine generated-fixture EVM equivalence gate for replay_controller.py.

All source inputs, build roots, and outputs are explicit CLI paths. This gate
uses only locally generated Java/ZIP fixtures and the frozen public Go transport.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import replay_controller as rc  # noqa: E402


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_source_manifest(frozen: Path) -> dict[str, Any]:
    """Must be the first read from the frozen source snapshot."""
    manifest = json.loads((frozen / "SOURCE_MANIFEST.json").read_text())
    if manifest.get("sourceOnly") is not True or manifest.get("noOriginalJarClassesResourcesWorldsCheckpointsReceiptsOrBindingLists") is not True:
        raise RuntimeError("frozen source manifest does not assert the authorized source-only boundary")
    if manifest.get("noJVMEngineModificationsAuthorizedForPerformanceWork") is not True:
        raise RuntimeError("frozen source manifest does not prohibit runtime/engine edits")
    for row in manifest["files"]:
        path = frozen / row["path"]
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
            raise RuntimeError(f"frozen source manifest mismatch: {row['path']}")
    return manifest


def call(command: list[str], env: dict[str, str], log: Path, cwd: Path, timeout: float) -> dict[str, Any]:
    began = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as f:
        p = subprocess.run(command, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT,
                           timeout=max(0.1, timeout), check=False)
        f.flush()
        os.fsync(f.fileno())
    return {"command": command, "exitCode": p.returncode, "wallSeconds": time.monotonic() - began,
            "logSHA256": rc.sha256_file(log), "logPath": str(log)}


def copy_build(frozen: Path, target: Path) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=False)
    (target / "engine").mkdir()
    (target / "coordinator").mkdir()
    shutil.copyfile(frozen / "pins.json", target / "pins.json")
    for sub, name in (("engine", "MCEntryInterpreter.json"), ("coordinator", "MCEntryCoordinator.json")):
        shutil.copyfile(frozen / sub / name, target / sub / name)
    pins = json.loads((target / "pins.json").read_text())
    (target / "authorization.json").write_text(json.dumps({"gas": str(pins["externalLocalGas"])}, indent=2) + "\n")
    return pins


def patch_driver(source: Path, out: Path) -> dict[str, str]:
    original = source.read_text()
    old = '''\tcase "resume-one-q1":
\t\tdoResumeBudget(os.Args[2], os.Args[3], true, 1)
\tcase "resume-one", "atomicity-resume":'''
    new = '''\tcase "resume-one-q1":
\t\tdoResumeBudget(os.Args[2], os.Args[3], true, 1)
\tcase "resume-one-qn":
\t\tdoResumeBudget(os.Args[2], os.Args[3], true, q)
\tcase "resume-one", "atomicity-resume":'''
    if original.count(old) != 1:
        raise RuntimeError("frozen generated driver CLI insertion point changed")
    patched = original.replace(old, new)
    out.write_text(patched)
    return {"sourceSHA256": digest(original.encode()), "patchedSourceSHA256": digest(patched.encode()),
            "onlyPatch": "add resume-one-qn dispatch to existing doResumeBudget; no gas/ABI/runtime change"}


def build_driver(repo_root: Path, source: Path, binary: Path, log: Path, remaining: float) -> dict[str, Any]:
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOFLAGS="-mod=readonly")
    began = time.monotonic()
    p = subprocess.run(["go", "build", "-mod=readonly", "-o", str(binary), str(source)], cwd=repo_root,
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=remaining, check=False)
    log.write_bytes(p.stdout)
    if p.returncode:
        raise RuntimeError(f"go build failed ({p.returncode}); see {log}")
    binary.chmod(0o755)
    return {"command": ["go", "build", "-mod=readonly", "-o", str(binary), str(source)],
            "exitCode": p.returncode, "wallSeconds": time.monotonic() - began,
            "sourceSHA256": rc.sha256_file(source), "binarySHA256": rc.sha256_file(binary),
            "logSHA256": digest(p.stdout)}


def compile_zip(repo_root: Path, sources: list[Path], output: Path, entry: str, classes_to_zip: list[str], log: Path,
                remaining: float) -> dict[str, Any]:
    classes = output.parent / (output.stem + "-classes")
    classes.mkdir(parents=True, exist_ok=False)
    cmd = ["javac", "--release", "8", "-g:none", "-d", str(classes), *map(str, sources)]
    p = subprocess.run(cmd, cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=remaining, check=False)
    log.write_bytes(p.stdout)
    if p.returncode:
        raise RuntimeError(f"generated javac fixture failed ({p.returncode}); see {log}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as z:
        for name in classes_to_zip:
            b = (classes / name).read_bytes()
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            z.writestr(info, b)
    omitted = classes / "perfcheck/missing/MissingDependency.class" if "missing" in output.stem else None
    return {"command": cmd, "exitCode": 0, "classFiles": classes_to_zip,
            "zipSHA256": rc.sha256_file(output), "zipBytes": output.stat().st_size,
            "includedClassSHA256": {name: digest((classes / name).read_bytes()) for name in classes_to_zip},
            "omittedGeneratedDependency": ("perfcheck/missing/MissingDependency.class" if omitted else None),
            "omittedGeneratedDependencySHA256": digest(omitted.read_bytes()) if omitted else None}


def make_bindings(path: Path, class_entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "bindings": [class_entry], "selectedResource": ""}, indent=2) + "\n")


def env_for(bindings: Path, max_gas: int, q: int) -> dict[str, str]:
    obj = json.loads(bindings.read_text())
    return dict(os.environ, MC_ENTRY_BINDINGS=",".join(obj["bindings"]),
                MC_ENTRY_SELECTED_RESOURCE=obj.get("selectedResource", ""),
                GOPROXY="off", GOSUMDB="off", PYTHONDONTWRITEBYTECODE="1",
                MC_GATE_BINDINGS=str(bindings), MC_GATE_MAX_CALL_GAS=str(max_gas),
                MC_GATE_INITIAL_QUANTUM=str(q), MC_GATE_MAX_QUANTUM=str(q))


def base_run_args(driver: Path, build: Path, fixture: Path, bindings: Path, world: Path, results: Path,
                  package_hash: str, pins: dict[str, Any], mode: str, action: str,
                  wall: int, q: int, continue_from: Path | None = None) -> list[str]:
    engine = pins["engine"]
    coordinator = pins["coordinator"]
    args = [sys.executable, str(HERE / "replay_controller.py"), "--mode", mode, "--action", action,
            "--driver", str(driver), "--build", str(build), "--fixture-zip", str(fixture),
            "--bindings", str(bindings), "--package-hash", package_hash,
            "--engine-runtime-sha256", engine["runtimeSHA256"], "--engine-runtime-keccak256", engine["runtimeKeccak256"],
            "--coordinator-runtime-sha256", coordinator["runtimeSHA256"], "--coordinator-runtime-keccak256", coordinator["runtimeKeccak256"],
            "--max-call-gas", str(pins["externalLocalGas"]), "--wall-limit-seconds", str(wall),
            "--world", str(world), "--results", str(results), "--initial-quantum", str(q), "--max-quantum", str(q),
            "--max-calls", "600"]
    if continue_from is not None:
        args.extend(["--continue-from", str(continue_from)])
    return args


def make_legacy_precise(source: Path, target: Path) -> dict[str, Any]:
    text = source.read_text()
    patches = []
    def sub(old: str, new: str, label: str) -> None:
        nonlocal text
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"legacy precise generated-fixture patch {label}: expected one match, found {count}")
        text = text.replace(old, new)
        patches.append(label)
    sub("HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];MAX=(1<<64)-1",
        'HERE=Path(__file__).resolve().parent;ROOT=Path(os.environ["MC_GATE_ROOT"]);MAX=int(os.environ["MC_GATE_MAX_CALL_GAS"])',
        "generated ROOT/gas inputs")
    sub("assert hashlib.sha256(jar.read_bytes()).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e'",
        "assert jar.is_file()", "replace original-only SHA guard with explicit fixture file check")
    sub("names=json.load(open(HERE.parent/'parent-original85-maps/original86-bindings.json'));assert len(names)==86 and len(set(names))==86",
        'binding_input=json.load(open(os.environ["MC_GATE_BINDINGS"]));names=binding_input["bindings"];assert len(names)==len(set(names)) and names',
        "replace original-only binding list with explicit generated input")
    sub("env.update(MC_ENTRY_BINDINGS=','.join(names),MC_ENTRY_SELECTED_RESOURCE='META-INF/log4j-provider.properties')",
        'env.update(MC_ENTRY_BINDINGS=\',\'.join(names),MC_ENTRY_SELECTED_RESOURCE=binding_input.get("selectedResource", ""))',
        "replace original-selected-resource default with explicit binding input")
    sub("q=65536;limit=int(sys.argv[6]) if len(sys.argv)>6 else 600;",
        'q=int(os.environ["MC_GATE_INITIAL_QUANTUM"]);limit=int(sys.argv[6]) if len(sys.argv)>6 else 600;',
        "use bounded generated-fixture quantum")
    sub("q=min(65536,q*2)", 'q=min(int(os.environ["MC_GATE_MAX_QUANTUM"]),q*2)', "respect explicit generated quantum ceiling")
    sub("r['executionBudget']=='LOCAL-U64MAX-USER-AUTHORIZED'", "r['executionBudget']=='LOCAL1B-USER-AUTHORIZED'",
        "align label to frozen P34 1B transport pin; no gas change")
    target.write_text(text)
    return {"sourceSHA256": digest(source.read_bytes()), "patchedSHA256": digest(text.encode()),
            "patches": patches, "scope": "disposable generated-fixture compatibility copy; frozen precise-replay.py unchanged"}


def run_legacy(script: Path, suite_root: Path, build: Path, fixture: Path, bindings: Path, world: Path,
               out: Path, q: int, max_gas: int, repo_root: Path, log: Path, remaining: float) -> dict[str, Any]:
    env = env_for(bindings, max_gas, q)
    env["MC_GATE_ROOT"] = str(suite_root)
    command = [sys.executable, str(script), "start", str(build), str(world), str(out), str(fixture), "600"]
    result = call(command, env, log, repo_root, remaining)
    if result["exitCode"] != 0:
        raise RuntimeError(f"legacy precise replay failed; see {log}")
    return result


def run_controller(driver: Path, build: Path, fixture: Path, bindings: Path, world: Path, results: Path,
                   package_hash: str, pins: dict[str, Any], mode: str, action: str,
                   wall: int, q: int, repo_root: Path, log: Path, remaining: float,
                   continue_from: Path | None = None) -> dict[str, Any]:
    env = env_for(bindings, pins["externalLocalGas"], q)
    command = base_run_args(driver, build, fixture, bindings, world, results, package_hash,
                            pins, mode, action, wall, q, continue_from)
    result = call(command, env, log, repo_root, remaining)
    if result["exitCode"] != 0:
        tail = log.read_text(errors="replace")[-4000:]
        raise RuntimeError(f"controller failed ({result['exitCode']}): {tail}")
    return result


def canonical_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for e in events:
        kind = e.get("kind")
        row = {"kind": kind}
        if kind in ("start", "success"):
            row.update({k: e.get(k) for k in ("q", "epoch", "checkpointSHA256", "checkpointBytes", "deltaJvm", "deltaInternal", "lifecycle", "gasUsed") if k in e})
            if kind == "start":
                row["checkpointBytes"] = e.get("checkpointBytes")
        elif kind == "refusal":
            row.update({k: e.get(k) for k in ("q", "selector", "missingClass", "rootBefore", "rootAfter", "gas", "checkpointBytes")})
        else:
            # Ignore only non-execution bookkeeping events; all EVM slice/refusal rows are compared.
            continue
        normalized.append(row)
    return normalized


def legacy_result(build: Path, world: Path, out: Path, q: int) -> tuple[dict[str, Any], list[dict[str, Any]], bytes, dict[str, Any]]:
    summary = json.loads((out / "summary.json").read_text())
    head = json.loads((world / "durable-head.json").read_text())
    rows = []
    report_root = world.parent / "reports" / world.name
    start = json.loads((report_root / "start.json").read_text())
    first_slice = json.loads((report_root / f"slice-{start['slice']['epoch']:020d}.json").read_text())
    rows.append({"kind": "start", "q": q,
                 "epoch": start["slice"]["epoch"],
                 "checkpointSHA256": first_slice["checkpointSHA256"],
                 "checkpointBytes": start["checkpointBytes"]})
    # Find the pre-final Head from epoch receipts rather than relying on volatile Head JSON.
    for old in summary["rows"]:
        if old["ok"]:
            report = json.loads((world.parent / "reports" / world.name / f"slice-{old['epoch']:020d}.json").read_text())
            sl = report["slice"]
            rows.append({"kind": "success", "q": old["q"], "epoch": old["epoch"],
                         "deltaJvm": old["deltaJvm"], "deltaInternal": old["deltaInternal"],
                         "lifecycle": old["lifecycle"], "gasUsed": report["gasUsed"],
                         "checkpointSHA256": report["checkpointSHA256"], "checkpointBytes": report["checkpointBytes"]})
        else:
            receipt_path = out / f"atomic-{old['call']:04d}-q{old['q']}.json"
            if not receipt_path.exists():
                receipt_path = world.parent / "reports" / world.name / "resume-refusal.json"
            receipt = json.loads(receipt_path.read_text())
            rows.append({"kind": "refusal", "q": old["q"], "selector": receipt.get("selector"),
                         "missingClass": (receipt.get("diagnostic") or {}).get("name"),
                         "rootBefore": receipt.get("rootBefore"), "rootAfter": receipt.get("rootAfter"),
                         "gas": receipt.get("gas"), "checkpointBytes": receipt.get("checkpointBytes")})
    cp = world / "checkpoints" / f"{head['checkpointSHA256']}.bin"
    return summary, rows, cp.read_bytes(), head


def compare_runs(label: str, legacy: tuple[dict[str, Any], list[dict[str, Any]], bytes, dict[str, Any]],
                 current_events: list[dict[str, Any]], current_summary: dict[str, Any], current_world: Path,
                 decoder: Any) -> dict[str, Any]:
    old_summary, old_events, old_cp, old_head = legacy
    old_canonical_events = canonical_events(old_events)
    new_events = canonical_events(current_events)
    if old_canonical_events != new_events:
        raise RuntimeError(f"{label}: precise event/q/checkpoint/refusal sequence differs from legacy")
    new_head = current_summary.get("finalHead")
    if new_head != rc.canonical_head(old_head):
        raise RuntimeError(f"{label}: canonical final Head/counters differ from legacy precise")
    cp_path = current_world / "checkpoints" / f"{new_head['checkpointSHA256']}.bin"
    new_cp = cp_path.read_bytes()
    if old_cp != new_cp:
        raise RuntimeError(f"{label}: final opaque MR01 checkpoint differs byte-for-byte")
    old_mr01 = decoder.inspect(old_cp)
    new_mr01 = decoder.inspect(new_cp)
    if old_mr01 != new_mr01:
        raise RuntimeError(f"{label}: read-only MR01 wire views differ")
    old_canonical_head = rc.canonical_head(old_head)
    return {"label": label, "events": len(new_events), "finalLifecycle": new_head["lifecycle"],
            "finalEpoch": new_head["epoch"], "finalJvmSteps": new_head["jvmSteps"],
            "finalInternalSteps": new_head["internalSteps"], "finalCheckpointSHA256": digest(new_cp),
            "finalCheckpointBytes": len(new_cp), "canonicalHeadAndDeterministicCountersEqual": True,
            "canonicalEventSequences": {"legacyPrecise": old_canonical_events, "candidate": new_events},
            "canonicalFinalHeads": {"legacyPrecise": old_canonical_head, "candidate": new_head},
            "MR01BytesEqual": True,
            "MR01": {"sha256": digest(new_cp), "bytes": len(new_cp), "rawHex": new_cp.hex(),
                     "decodedReadOnlyView": new_mr01,
                     "decodedViewSHA256": digest(json.dumps(old_mr01, sort_keys=True).encode())}}


def legacy_setup_record(script: Path, suite_root: Path, build: Path, fixture: Path, bindings: Path,
                        label: str, q: int, max_gas: int, repo_root: Path, work: Path,
                        deadline: float) -> tuple[Path, Path, dict[str, Any]]:
    world = suite_root / "build" / "worlds" / label
    out = suite_root / "build" / f"out-{label}"
    result = run_legacy(script, suite_root, build, fixture, bindings, world, out, q, max_gas,
                        repo_root, work / f"{label}-legacy.log", max(0.1, deadline - time.monotonic()))
    return world, out, result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True, help="explicit root containing go.mod/local Go transport dependencies")
    p.add_argument("--frozen-p34", type=Path, required=True, help="explicit authorized source-only P34 snapshot")
    p.add_argument("--work-root", type=Path, required=True, help="disposable generated-only build/test root")
    p.add_argument("--evidence-output", type=Path, required=True, help="durable small JSON evidence record inside this worker folder")
    p.add_argument("--budget-seconds", type=int, default=1100)
    p.add_argument("--quantum", type=int, default=64)
    p.add_argument("--keep-work", action="store_true", help="keep generated class/ZIP/world intermediates for debugging")
    args = p.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    frozen = args.frozen_p34.resolve(strict=True)
    work_root = args.work_root.resolve()
    evidence_out = args.evidence_output.resolve()
    if work_root.exists() and any(work_root.iterdir()):
        raise RuntimeError("--work-root must be nonexistent or empty; historical runs are never overwritten")
    if evidence_out.exists():
        raise RuntimeError("--evidence-output already exists; choose a new run-specific path")
    if not (1 <= args.quantum <= 65536):
        raise RuntimeError("generated fixture quantum must remain within the unchanged P34 65536 cap")
    started = time.monotonic()
    deadline = started + args.budget_seconds
    manifest = verify_source_manifest(frozen)
    work_root.mkdir(parents=True, exist_ok=True)
    passed = False
    try:
        build = work_root / "p34-build"
        pins = copy_build(frozen, build)
        engine = build / "engine" / "MCEntryInterpreter.json"
        coordinator = build / "coordinator" / "MCEntryCoordinator.json"
        max_gas = pins["externalLocalGas"]
        q = args.quantum
        source_root = HERE / "fixtures"
        generated = work_root / "generated"
        generated.mkdir()
        missing_zip = generated / "missing-fixture.zip"
        complete_zip = generated / "complete-fixture.zip"
        missing_source = [source_root / "missing" / "Main.java", source_root / "missing" / "MissingDependency.java"]
        complete_source = [source_root / "complete" / "Main.java"]
        fixture_manifest = {
            "sourceSHA256": {str(path.relative_to(HERE)): rc.sha256_file(path) for path in missing_source + complete_source},
            "missing": compile_zip(repo_root, missing_source, missing_zip, "perfcheck/missing/Main.class",
                                    ["perfcheck/missing/Main.class"], work_root / "javac-missing.log", deadline - time.monotonic()),
            "complete": compile_zip(repo_root, complete_source, complete_zip, "perfcheck/complete/Main.class",
                                    ["perfcheck/complete/Main.class"], work_root / "javac-complete.log", deadline - time.monotonic()),
        }
        missing_bindings = generated / "missing-bindings.json"
        complete_bindings = generated / "complete-bindings.json"
        make_bindings(missing_bindings, "perfcheck/missing/Main.class")
        make_bindings(complete_bindings, "perfcheck/complete/Main.class")

        driver_source = work_root / "generated-driver.go"
        driver_patch = patch_driver(frozen / "reference" / "canonical-driver.go.txt", driver_source)
        driver = work_root / "driver"
        build_record = build_driver(repo_root, driver_source, driver, work_root / "go-build.log", deadline - time.monotonic())
        # Pin the exact public source and its one disposable CLI-coverage patch.
        precise_path = frozen / "reference" / "precise-replay.py"
        legacy_copy = work_root / "precise-replay-generated.py"
        legacy_patch = make_legacy_precise(precise_path, legacy_copy)
        (work_root / "harness-patches.json").write_text(json.dumps({"driver": driver_patch, "legacyPrecise": legacy_patch}, indent=2) + "\n")

        sys.dont_write_bytecode = True
        decoder_spec = importlib.util.spec_from_file_location("frozen_mr01_diagnostic", frozen / "reference" / "checkpoint_diagnostic.py")
        decoder = importlib.util.module_from_spec(decoder_spec)
        assert decoder_spec.loader
        decoder_spec.loader.exec_module(decoder)

        # Establish the package hash by a real public EVM setup with generated data;
        # this probe is not treated as execution output or copied into an acceptance run.
        def package_probe(fixture: Path, bindings: Path, label: str) -> str:
            world = work_root / "probes" / label
            world.parent.mkdir(parents=True, exist_ok=True)
            env = env_for(bindings, max_gas, q)
            cmd = [str(driver), "setup-chain", str(world), str(coordinator), str(engine), str(fixture), str(q)]
            log = work_root / f"probe-{label}.log"
            result = call(cmd, env, log, repo_root, deadline - time.monotonic())
            if result["exitCode"] != 0:
                raise RuntimeError(f"generated EVM package probe failed; see {log}")
            head = json.loads((world / "durable-head.json").read_text())
            if head["lifecycle"] != 1 or head["epoch"] < 1:
                raise RuntimeError("generated package probe did not produce a RUNNING successful checkpoint")
            return head["packageRoot"]

        missing_package = package_probe(missing_zip, missing_bindings, "missing")
        complete_package = package_probe(complete_zip, complete_bindings, "complete")
        # The historical script's directory convention is reproduced in an isolated temporary root.
        suite = work_root / "legacy-root"
        (suite / "build").mkdir(parents=True)
        shutil.copytree(build, suite / "build" / "provided-build")
        legacy_build = suite / "build" / "provided-build"
        shutil.copyfile(driver, legacy_build / "driver")
        (legacy_build / "driver").chmod(0o755)

        # Missing-type equivalence: old precise, new default precise, and early discovery
        # followed by precise continuation from the exact last successful P34 Head.
        miss_legacy_world, miss_legacy_out, legacy_log = legacy_setup_record(
            legacy_copy, suite, legacy_build, missing_zip, missing_bindings, "missing-legacy", q,
            max_gas, repo_root, work_root, deadline)
        legacy_summary, legacy_events, legacy_cp, legacy_head = legacy_result(legacy_build, miss_legacy_world, miss_legacy_out, q)
        if legacy_head["packageRoot"] != missing_package:
            raise RuntimeError("legacy generated replay package hash differs from explicit EVM package probe")

        miss_precise_world = suite / "build" / "worlds" / "missing-controller-precise"
        miss_precise_results = work_root / "controller-results" / "missing-precise"
        precise_log = work_root / "missing-controller-precise.log"
        precise_call = run_controller(driver, legacy_build, missing_zip, missing_bindings, miss_precise_world,
                                      miss_precise_results, missing_package, pins, "precise", "start", 1000, q,
                                      repo_root, precise_log, deadline - time.monotonic())
        precise_state = json.loads((miss_precise_results / "summary.json").read_text())
        precise_equivalence = compare_runs("missing/new-precise", (legacy_summary, legacy_events, legacy_cp, legacy_head),
                                           precise_state["events"], precise_state, miss_precise_world, decoder)

        miss_disc_world = suite / "build" / "worlds" / "missing-controller-discovery"
        miss_disc_results = work_root / "controller-results" / "missing-discovery"
        disc_log = work_root / "missing-controller-discovery.log"
        discovery_call = run_controller(driver, legacy_build, missing_zip, missing_bindings, miss_disc_world,
                                        miss_disc_results, missing_package, pins, "discovery", "start", 500, q,
                                        repo_root, disc_log, deadline - time.monotonic())
        disc_summary = json.loads((miss_disc_results / "summary.json").read_text())
        if disc_summary.get("status") != "discovery-missing-class-not-terminal-success-not-q1-acceptance":
            raise RuntimeError(f"generated EVM fixture did not produce the explicit discovery stop: {disc_summary.get('status')}")
        if disc_summary.get("terminalGuestOutcome") is not False or disc_summary.get("q1FrontierAcceptance") is not False or disc_summary.get("finalAcceptanceEligible") is not False:
            raise RuntimeError("discovery result incorrectly claims guest terminal/q1 acceptance")
        stop = disc_summary["discoveryStop"]
        if stop["missingClass"] != "perfcheck/missing/MissingDependency" or stop["q"] <= 1:
            raise RuntimeError(f"EVM diagnostic did not identify exact generated missing type: {stop}")
        stop_receipt_path = miss_disc_results / stop["receiptArchive"]["path"]
        stop_receipt = json.loads(stop_receipt_path.read_text())
        cont_results = work_root / "controller-results" / "missing-discovery-continued"
        cont_log = work_root / "missing-discovery-continuation.log"
        continuation_call = run_controller(driver, legacy_build, missing_zip, missing_bindings, miss_disc_world,
                                           cont_results, missing_package, pins, "precise", "continue", 1000, q,
                                           repo_root, cont_log, deadline - time.monotonic(),
                                           miss_disc_results / "summary.json")
        continuation_state = json.loads((cont_results / "summary.json").read_text())
        continuation_equivalence = compare_runs("missing/discovery+precise-continuation",
                                                 (legacy_summary, legacy_events, legacy_cp, legacy_head),
                                                 continuation_state["events"], continuation_state, miss_disc_world, decoder)

        # Positive terminal path: discovery is not mistaken for a missing-class stop;
        # completed guest outcome and deterministic transport counters stay unchanged.
        pos_legacy_world, pos_legacy_out, pos_legacy_log = legacy_setup_record(
            legacy_copy, suite, legacy_build, complete_zip, complete_bindings, "complete-legacy", q,
            max_gas, repo_root, work_root, deadline)
        pos_legacy_summary, pos_legacy_events, pos_legacy_cp, pos_legacy_head = legacy_result(legacy_build, pos_legacy_world, pos_legacy_out, q)
        if pos_legacy_head["packageRoot"] != complete_package:
            raise RuntimeError("positive legacy package hash differs from explicit EVM package probe")
        pos_precise_world = suite / "build" / "worlds" / "complete-controller-precise"
        pos_precise_results = work_root / "controller-results" / "complete-precise"
        pos_precise_log = work_root / "complete-controller-precise.log"
        pos_precise_call = run_controller(driver, legacy_build, complete_zip, complete_bindings, pos_precise_world,
                                          pos_precise_results, complete_package, pins, "precise", "start", 1000, q,
                                          repo_root, pos_precise_log, deadline - time.monotonic())
        pos_precise_state = json.loads((pos_precise_results / "summary.json").read_text())
        positive_precise_equivalence = compare_runs("positive/new-precise",
                                                    (pos_legacy_summary, pos_legacy_events, pos_legacy_cp, pos_legacy_head),
                                                    pos_precise_state["events"], pos_precise_state, pos_precise_world, decoder)
        pos_disc_world = suite / "build" / "worlds" / "complete-controller-discovery"
        pos_disc_results = work_root / "controller-results" / "complete-discovery"
        pos_disc_log = work_root / "complete-controller-discovery.log"
        positive_discovery_call = run_controller(driver, legacy_build, complete_zip, complete_bindings, pos_disc_world,
                                                 pos_disc_results, complete_package, pins, "discovery", "start", 1000, q,
                                                 repo_root, pos_disc_log, deadline - time.monotonic())
        pos_disc_state = json.loads((pos_disc_results / "summary.json").read_text())
        if pos_disc_state.get("status") != "terminal-outcome-not-discovery-stop" or not pos_disc_state.get("terminalGuestOutcome"):
            raise RuntimeError("positive discovery-mode execution did not remain a terminal guest outcome")
        positive_discovery_equivalence = compare_runs("positive/discovery-terminal",
                                                      (pos_legacy_summary, pos_legacy_events, pos_legacy_cp, pos_legacy_head),
                                                      pos_disc_state["events"], pos_disc_state, pos_disc_world, decoder)

        def compact_process(record: dict[str, Any]) -> dict[str, Any]:
            out = dict(record)
            out.pop("logPath", None)
            if isinstance(out.get("command"), list):
                out["command"] = [str(x).replace(str(work_root), "$WORK_ROOT") for x in out["command"]]
            return out
        evidence = {
            "schema": 1, "scope": "generated Java 8 fixtures through unchanged P34 engine/coordinator and public Go EVM transport only",
            "acceptedProfile": pins["profile"], "sourceManifest": {"sourceCommit": manifest["sourceCommit"],
                "fileCount": len(manifest["files"]), "allSHA256Verified": True},
            "buildPins": {"engineBytes": pins["engine"]["bytes"], "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
                          "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
                          "coordinatorBytes": pins["coordinator"]["bytes"],
                          "coordinatorRuntimeSHA256": pins["coordinator"]["runtimeSHA256"],
                          "coordinatorRuntimeKeccak256": pins["coordinator"]["runtimeKeccak256"],
                          "maxCallGas": max_gas, "checkpointCap": pins["maxCheckpointBytes"]},
            "generatedFixtures": fixture_manifest, "driverBuild": compact_process(build_record),
            "disposableHarnessPatches": {"driver": driver_patch, "legacyPrecise": legacy_patch},
            "quantum": q, "wallBudgetSeconds": args.budget_seconds, "elapsedSeconds": time.monotonic() - started,
            "packageRoots": {"missing": missing_package, "complete": complete_package},
            "equivalence": [precise_equivalence, continuation_equivalence,
                            positive_precise_equivalence, positive_discovery_equivalence],
            "discovery": {"status": disc_summary["status"], "missingClass": stop["missingClass"],
                          "failedQuantum": stop["q"], "nextPreciseQuantum": stop["nextQuantum"],
                          "terminalGuestOutcome": disc_summary["terminalGuestOutcome"],
                          "q1FrontierAcceptance": disc_summary["q1FrontierAcceptance"],
                          "finalAcceptanceEligible": disc_summary["finalAcceptanceEligible"],
                          "eventSequence": canonical_events(disc_summary["events"]),
                          "lastSuccessfulHead": stop["lastSuccessfulHead"],
                          "priorHeadBytesHex": stop["priorHeadBytesHex"],
                          "refusalReceipt": stop_receipt},
            "runProcessRecords": {"legacyMissing": compact_process(legacy_log), "newPreciseMissing": compact_process(precise_call),
                                  "discoveryMissing": compact_process(discovery_call), "continuation": compact_process(continuation_call),
                                  "legacyComplete": compact_process(pos_legacy_log), "newPreciseComplete": compact_process(pos_precise_call),
                                  "discoveryComplete": compact_process(positive_discovery_call)},
            "reproduction": {"script": "generated_evm_gate.py", "repoRoot": "$REPO_ROOT",
                             "frozenP34": "evidence/java-evm/minecraft-entry/performance-base-p34",
                             "workRoot": "$WORK_ROOT", "budgetSeconds": args.budget_seconds,
                             "quantum": q, "successfulIntermediatesRemoved": not args.keep_work},
            "nonClaims": ["No original JAR/classes/resources/bindings/worlds/checkpoints/receipts read",
                          "No original Minecraft execution", "No EVM/engine/coordinator/runtime/gas/format changes",
                          "Discovery stop is not terminal success or precise q1 acceptance",
                          "Parent independent review and original-input acceptance remain required"],
        }
        evidence_out.parent.mkdir(parents=True, exist_ok=True)
        evidence_out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        evidence_out.with_suffix(evidence_out.suffix + ".sha256").write_text(digest(evidence_out.read_bytes()) + "  " + evidence_out.name + "\n")
        print(json.dumps({"status": "generated-evm-equivalence-pass", "elapsedSeconds": evidence["elapsedSeconds"],
                          "evidence": str(evidence_out), "discovery": evidence["discovery"]}, sort_keys=True))
        passed = True
        return 0
    finally:
        # Keep failed/interrupted runs as reproducible evidence. Only successful
        # disposable intermediates may be removed by default.
        if passed and not args.keep_work:
            shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        print(f"generated-EVM gate exceeded a bounded child timeout: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"generated-EVM gate failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
