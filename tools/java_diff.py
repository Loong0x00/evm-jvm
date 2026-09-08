#!/usr/bin/env python3
"""Differential runner for the staged Java-inside-EVM fixtures.

The reference JVM is a test oracle only.  The EVM command always receives the
unchanged class file emitted by javac.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shlex
import subprocess
import tempfile
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1
DEFAULT_SEED = 56
FAST_SAMPLE_SIZE = 20
COMPILE_TIMEOUT_SECONDS = 60.0
VERSION_TIMEOUT_SECONDS = 10.0
GIT_TIMEOUT_SECONDS = 5.0
MAX_CASE_TIMEOUT_SECONDS = 300.0
MAX_GAS_LIMIT = 100_000_000
INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
JAVA_NAME_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
JAVA_BINARY_NAME_RE = re.compile(
    r"^[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*$"
)
JAVA_FQCN_RE = re.compile(
    r"^[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+$"
)
KV_RE = re.compile(r"^([a-z0-9_]+)=(.*)$")
KNOWN_JAVA_EXCEPTIONS = frozenset({
    "java.lang.ArithmeticException",
    "java.lang.StackOverflowError",
    "java.lang.ExceptionInInitializerError",
    "java.lang.NegativeArraySizeException",
    "java.lang.ArrayIndexOutOfBoundsException",
    "java.lang.NullPointerException",
    "java.lang.OutOfMemoryError",
    "java.lang.ClassCastException",
    "java.lang.ArrayStoreException",
    "java.lang.IncompatibleClassChangeError",
    "java.lang.AbstractMethodError",
})


class HarnessError(Exception):
    """A manifest, configuration, or runner error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def confined_file(fixtures: Path, relative: Any, label: str) -> Tuple[str, Path]:
    if not isinstance(relative, str) or not relative:
        raise HarnessError(f"{label} must be a nonempty relative path")
    rel = Path(relative)
    if rel.is_absolute():
        raise HarnessError(f"{label} must be relative to the fixture directory: {relative!r}")
    root = fixtures.resolve()
    try:
        resolved = (root / rel).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise HarnessError(f"{label} is missing or escapes the fixture directory: {relative!r}")
    if not resolved.is_file():
        raise HarnessError(f"{label} is not a file: {relative!r}")
    return relative, resolved


def checked_class_relative_path(relative: Any, label: str) -> str:
    """Validate manifest metadata without looking at or parsing a class file."""
    if not isinstance(relative, str) or not relative:
        raise HarnessError(f"{label} must be a nonempty relative .class path")
    # Manifest class paths are javac-output paths and therefore use '/' even on
    # hosts where pathlib has other native path rules. Reject normalization so
    # the recorded and supplied path is exactly the manifest path.
    if ("\\" in relative or "\x00" in relative or relative.startswith("/")
            or re.match(r"^[A-Za-z]:/", relative)):
        raise HarnessError(f"{label} must be a relative .class path: {relative!r}")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise HarnessError(f"{label} contains empty or traversal components: {relative!r}")
    if not relative.endswith(".class"):
        raise HarnessError(f"{label} must end in .class: {relative!r}")
    return relative


def confined_compiled_class(classes: Path, relative: str, label: str) -> Path:
    """Resolve a previously validated class path under this run's output."""
    root = classes.resolve()
    candidate = root.joinpath(*relative.split("/"))
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise HarnessError(
            f"{label} is missing or escapes the javac output directory: {relative!r}"
        )
    if not resolved.is_file():
        raise HarnessError(f"{label} is not a compiled file: {relative!r}")
    return candidate


def load_manifest(fixtures: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Path]:
    manifest_path = fixtures / "cases.json"
    try:
        _, manifest_path = confined_file(fixtures, "cases.json", "cases.json")
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot read manifest {manifest_path}: {exc}")
    if not isinstance(manifest, dict):
        raise HarnessError("manifest root must be an object")
    if not is_int(manifest.get("schema_version")) or manifest["schema_version"] != SCHEMA_VERSION:
        raise HarnessError(f"manifest schema_version must be integer {SCHEMA_VERSION}")
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise HarnessError("manifest cases must be a nonempty array")

    required = {
        "id", "stage", "sources", "class", "method", "args",
        "gas_limit", "timeout_seconds", "smoke", "expected_kind",
    }
    seen_ids = set()
    cases: List[Dict[str, Any]] = []
    for index, original in enumerate(raw_cases):
        where = f"cases[{index}]"
        if not isinstance(original, dict):
            raise HarnessError(f"{where} must be an object")
        missing = sorted(required - original.keys())
        if missing:
            raise HarnessError(f"{where} missing required keys: {', '.join(missing)}")
        case = dict(original)
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise HarnessError(f"{where}.id must be a nonempty string")
        if case_id in seen_ids:
            raise HarnessError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)
        if case["stage"] not in ("m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc", "m5a", "m5ba"):
            raise HarnessError(
                f"{case_id}: stage must be m1, m2, m2b, m3a, m3b, m3c, m3d, m4a, m4b, m4c, m4d, m4e, m4fa, m4fb, m4fc, m5a, or m5ba"
            )
        expected_kind = case["expected_kind"]
        if expected_kind not in ("value", "java_exception"):
            raise HarnessError(
                f"{case_id}: expected_kind must be value or java_exception"
            )
        if expected_kind == "java_exception":
            expected_exception = case.get("expected_exception")
            if (not isinstance(expected_exception, str)
                    or not JAVA_FQCN_RE.fullmatch(expected_exception)):
                raise HarnessError(
                    f"{case_id}: expected_exception must be a syntactically valid "
                    "fully-qualified Java class name"
                )
            if expected_exception not in KNOWN_JAVA_EXCEPTIONS:
                raise HarnessError(
                    f"{case_id}: expected_exception is not a known supported Java outcome"
                )
        elif "expected_exception" in case:
            raise HarnessError(
                f"{case_id}: expected_exception is only valid for java_exception cases"
            )
        if not isinstance(case["smoke"], bool):
            raise HarnessError(f"{case_id}: smoke must be a boolean")
        if not JAVA_BINARY_NAME_RE.fullmatch(
                case["class"] if isinstance(case["class"], str) else ""):
            raise HarnessError(
                f"{case_id}: class must be an ASCII dotted binary Java class name"
            )
        if not JAVA_NAME_RE.fullmatch(case["method"] if isinstance(case["method"], str) else ""):
            raise HarnessError(f"{case_id}: method must be a simple Java method name")
        args = case["args"]
        if not isinstance(args, list):
            raise HarnessError(f"{case_id}: args must be an array")
        for arg_index, value in enumerate(args):
            if not is_int(value) or not INT32_MIN <= value <= INT32_MAX:
                raise HarnessError(f"{case_id}: args[{arg_index}] is not a signed int32 integer")
        gas = case["gas_limit"]
        if not is_int(gas) or not 1 <= gas <= MAX_GAS_LIMIT:
            raise HarnessError(
                f"{case_id}: gas_limit must be an integer in [1, {MAX_GAS_LIMIT}]"
            )
        timeout = case["timeout_seconds"]
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise HarnessError(f"{case_id}: timeout_seconds must be numeric")
        if (not 0 < timeout <= MAX_CASE_TIMEOUT_SECONDS
                or (isinstance(timeout, float) and not math.isfinite(timeout))):
            raise HarnessError(
                f"{case_id}: timeout_seconds must be finite and in (0, {MAX_CASE_TIMEOUT_SECONDS}]"
            )
        sources = case["sources"]
        if not isinstance(sources, list) or not sources:
            raise HarnessError(f"{case_id}: sources must be a nonempty array")
        if len(set(str(item) for item in sources)) != len(sources):
            raise HarnessError(f"{case_id}: sources contains duplicates")
        checked_sources = []
        source_paths = []
        for source_index, source in enumerate(sources):
            rel, resolved = confined_file(fixtures, source, f"{case_id}.sources[{source_index}]")
            if not rel.endswith(".java"):
                raise HarnessError(f"{case_id}: source must end in .java: {rel!r}")
            checked_sources.append(rel)
            source_paths.append(resolved)
        case["sources"] = checked_sources
        case["_source_paths"] = source_paths
        if "class_files" in case:
            raw_class_files = case["class_files"]
            if not isinstance(raw_class_files, list) or not raw_class_files:
                raise HarnessError(f"{case_id}: class_files must be a nonempty array")
            checked_class_files = [
                checked_class_relative_path(value, f"{case_id}.class_files[{class_index}]")
                for class_index, value in enumerate(raw_class_files)
            ]
            if len(set(checked_class_files)) != len(checked_class_files):
                raise HarnessError(f"{case_id}: class_files contains duplicates")
            case["class_files"] = checked_class_files
        cases.append(case)

    confined_file(fixtures, "OracleMain.java", "OracleMain.java")
    return manifest, cases, manifest_path.resolve()


def select_cases(cases: Sequence[Dict[str, Any]], stage: str, tier: str,
                 seed: int, exact_case: Optional[str]) -> List[Dict[str, Any]]:
    if stage == "m1":
        allowed_stages = {"m1"}
    elif stage == "m2":
        allowed_stages = {"m1", "m2"}
    elif stage == "m2b":
        allowed_stages = {"m1", "m2", "m2b"}
    elif stage == "m3a":
        allowed_stages = {"m1", "m2", "m2b", "m3a"}
    elif stage == "m3b":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b"}
    elif stage == "m3c":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c"}
    elif stage == "m3d":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d"}
    elif stage == "m4a":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a"}
    elif stage == "m4b":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b"}
    elif stage == "m4c":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c"}
    elif stage == "m4d":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d"}
    elif stage == "m4e":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e"}
    elif stage == "m4fa":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa"}
    elif stage == "m4fb":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb"}
    elif stage == "m4fc":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc"}
    elif stage == "m5a":
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc", "m5a"}
    elif stage in ("m5ba", "all"):
        allowed_stages = {"m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc", "m5a", "m5ba"}
    else:
        raise HarnessError(f"unknown stage: {stage}")
    stage_cases = [case for case in cases if case["stage"] in allowed_stages]
    if exact_case is not None:
        matches = [case for case in cases if case["id"] == exact_case]
        if not matches:
            raise HarnessError(f"unknown case id: {exact_case}")
        if matches[0] not in stage_cases:
            raise HarnessError(f"case {exact_case} is excluded by --stage {stage}")
        return matches
    if tier == "full":
        selected = stage_cases
    elif tier == "smoke":
        selected = [case for case in stage_cases if case["smoke"]]
    else:
        smoke_ids = {case["id"] for case in stage_cases if case["smoke"]}
        candidates = sorted(
            (case for case in stage_cases if case["id"] not in smoke_ids),
            key=lambda case: case["id"],
        )
        count = min(FAST_SAMPLE_SIZE, len(candidates))
        sampled_ids = {case["id"] for case in random.Random(seed).sample(candidates, count)}
        selected = [
            case for case in stage_cases
            if case["id"] in smoke_ids or case["id"] in sampled_ids
        ]
    if not selected:
        raise HarnessError(
            f"no cases selected for stage={stage} tier={tier}; empty suites do not pass"
        )
    return selected


def command_text(argv: Sequence[str]) -> str:
    return shlex.join([str(item) for item in argv])


def run_command(argv: Sequence[str], timeout: float, cwd: Optional[Path] = None) -> Dict[str, Any]:
    args = [str(item) for item in argv]
    started = time.monotonic()
    record: Dict[str, Any] = {
        "argv": args,
        "command": command_text(args),
        "timeout_seconds": timeout,
        "cwd": str(cwd) if cwd else None,
    }
    try:
        completed = subprocess.run(
            args, cwd=str(cwd) if cwd else None, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
            check=False,
        )
        record.update({
            "status": "exited",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
    except subprocess.TimeoutExpired as exc:
        record.update({
            "status": "timeout",
            "returncode": None,
            "stdout": _timeout_text(exc.stdout),
            "stderr": _timeout_text(exc.stderr),
        })
    except OSError as exc:
        record.update({
            "status": "spawn_error",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        })
    record["duration_seconds"] = round(time.monotonic() - started, 6)
    return record


def _timeout_text(value: Any) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def parse_oracle(record: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[str]]:
    if record["status"] == "timeout":
        return "oracle_timeout", None, "oracle process timed out"
    if record["status"] != "exited" or record["returncode"] != 0:
        return "oracle_failure", None, "oracle process failed"
    lines = record["stdout"].splitlines()
    if len(lines) != 1:
        return "oracle_failure", None, "oracle output must contain exactly one line"
    line = lines[0]
    if line.startswith("exception="):
        exception_class = line[len("exception="):]
        if not JAVA_FQCN_RE.fullmatch(exception_class):
            return "oracle_failure", None, "oracle exception is not a valid fully-qualified class name"
        return "oracle_exception", None, exception_class
    if not line.startswith("value="):
        return "oracle_failure", None, "malformed oracle output"
    try:
        value = int(line[len("value="):], 10)
    except ValueError:
        return "oracle_failure", None, "oracle value is not decimal int32"
    if not INT32_MIN <= value <= INT32_MAX:
        return "oracle_failure", None, "oracle value is outside signed int32"
    return "value", value, None


def extract_failure_metadata(stderr: str) -> Tuple[Optional[int], Optional[str]]:
    gas_match = re.search(r"gas_used=(\d+)", stderr)
    runtime_match = re.search(r"runtime_sha256=([0-9a-fA-F]{64})", stderr)
    gas = int(gas_match.group(1)) if gas_match else None
    runtime_hash = runtime_match.group(1).lower() if runtime_match else None
    return gas, runtime_hash


def parse_evm(record: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Optional[str]]:
    if record["status"] == "timeout":
        return "evm_timeout", {}, "EVM process timed out"
    if record["status"] != "exited":
        return "harness_error", {}, "could not start EVM CLI"
    if record["returncode"] != 0:
        lower = (record["stdout"] + "\n" + record["stderr"]).lower()
        metadata: Dict[str, Any] = {}
        gas, runtime_hash = extract_failure_metadata(record["stderr"])
        if gas is not None:
            metadata["gas_used"] = gas
        if runtime_hash is not None:
            metadata["runtime_sha256"] = runtime_hash
        if "out of gas" in lower:
            return "evm_oog", metadata, "EVM execution ran out of gas"
        if "execution reverted" in lower:
            return "evm_revert", metadata, "EVM execution reverted"
        return "evm_failure", metadata, "EVM CLI exited nonzero"

    values: Dict[str, str] = {}
    for line in record["stdout"].splitlines():
        match = KV_RE.fullmatch(line)
        if not match or match.group(1) in values:
            return "evm_malformed", {}, "malformed or duplicate EVM output line"
        values[match.group(1)] = match.group(2)
    common = {"engine", "runtime_bytes", "runtime_sha256", "gas_used"}
    outcome_keys = {"result", "exception"} & set(values)
    if (set(values) - {"result", "exception"} != common
            or len(outcome_keys) != 1
            or values.get("engine") != "evm-jvm-subset-interpreter"):
        return "evm_malformed", {}, "EVM output must have common keys and exactly one outcome"
    try:
        runtime_bytes = int(values["runtime_bytes"], 10)
        gas_used = int(values["gas_used"], 10)
    except ValueError:
        return "evm_malformed", {}, "EVM numeric output is malformed"
    runtime_hash = values["runtime_sha256"].lower()
    if (runtime_bytes <= 0 or gas_used < 0 or not SHA256_RE.fullmatch(runtime_hash)):
        return "evm_malformed", {}, "EVM output values are out of range"
    parsed: Dict[str, Any] = {
        "runtime_bytes": runtime_bytes,
        "runtime_sha256": runtime_hash,
        "gas_used": gas_used,
    }
    if "result" in outcome_keys:
        try:
            result = int(values["result"], 10)
        except ValueError:
            return "evm_malformed", {}, "EVM numeric output is malformed"
        if not INT32_MIN <= result <= INT32_MAX:
            return "evm_malformed", {}, "EVM output values are out of range"
        parsed["value"] = result
        return "value", parsed, None
    exception_class = values["exception"]
    if not JAVA_FQCN_RE.fullmatch(exception_class):
        return "evm_malformed", {}, "EVM exception is not a valid fully-qualified class name"
    if exception_class not in KNOWN_JAVA_EXCEPTIONS:
        return "evm_malformed", {}, "EVM exception is not a known supported Java outcome"
    parsed["exception"] = exception_class
    return "java_exception", parsed, None


def clean_case(case: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in case.items() if not key.startswith("_")}


def git_commit(repo: Path) -> Optional[str]:
    record = run_command(["git", "rev-parse", "HEAD"], GIT_TIMEOUT_SECONDS, repo)
    if record["status"] == "exited" and record["returncode"] == 0:
        value = record["stdout"].strip()
        if re.fullmatch(r"[0-9a-fA-F]{40,64}", value):
            return value.lower()
    return None


def replay_command(repo: Path, args: argparse.Namespace, case: Dict[str, Any],
                   artifacts: Path, fixtures: Path, evm_bin: Path) -> str:
    argv = [
        sys.executable, str((repo / "tools/java_diff.py").resolve()),
        "--stage", args.stage, "--tier", args.tier, "--seed", str(args.seed),
        "--case", case["id"], "--fixtures", str(fixtures),
        "--artifacts", str(artifacts), "--evm-bin", str(evm_bin),
    ]
    return command_text(argv)


def write_report(artifacts: Path, report: Dict[str, Any]) -> None:
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    failures = []
    for case in report.get("cases", []):
        if case.get("status") != "pass":
            failures.append(f"{case.get('id', '<suite>')}: {case.get('status')}: {case.get('detail', '')}")
            if case.get("replay_command"):
                failures.append(f"  replay: {case['replay_command']}")
    if report.get("harness_error"):
        failures.append(f"harness_error: {report['harness_error']}")
    failure_text = ("\n".join(failures) + "\n") if failures else ""
    (artifacts / "failures.txt").write_text(failure_text, encoding="utf-8")
    # Keep evidence alongside this run's classes; the top-level files are latest-run pointers.
    if report.get("run_directory"):
        archived = Path(report["run_directory"])
        (archived / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (archived / "failures.txt").write_text(failure_text, encoding="utf-8")


def execute(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    repo = Path(__file__).resolve().parents[1]
    fixtures = Path(args.fixtures).expanduser().resolve()
    artifacts = Path(args.artifacts).expanduser().resolve()
    evm_bin = Path(args.evm_bin).expanduser().resolve()
    report: Dict[str, Any] = {
        "schema_version": 1,
        "stage": args.stage,
        "tier": args.tier,
        "seed": args.seed,
        "fixtures": str(fixtures),
        "artifacts": str(artifacts),
        "evm_bin": str(evm_bin),
        "git_commit": git_commit(repo),
        "selected_ids": [],
        "commands": {},
        "cases": [],
        "runtime_sha256": None,
        "replay_note": (
            "Replay recompiles fixtures and invokes the selected EVM binary; it depends "
            "on the current fixture sources, javac/JVM, CLI, and embedded runtime. Verify hashes."
        ),
    }
    try:
        manifest, cases, manifest_path = load_manifest(fixtures)
        selected = select_cases(cases, args.stage, args.tier, args.seed, args.case)
        report["manifest_sha256"] = sha256_file(manifest_path)
        report["selected_ids"] = [case["id"] for case in selected]
        report["manifest_descriptive_keys"] = sorted(
            set(manifest.keys()) - {"schema_version", "cases"}
        )
    except HarnessError as exc:
        report["harness_error"] = str(exc)
        return 1, report

    javac_version = run_command(["javac", "-version"], VERSION_TIMEOUT_SECONDS)
    java_version = run_command(["java", "-version"], VERSION_TIMEOUT_SECONDS)
    report["commands"]["javac_version"] = javac_version
    report["commands"]["java_version"] = java_version
    if any(record["status"] != "exited" or record["returncode"] != 0
           for record in (javac_version, java_version)):
        detail = "could not query javac/java version"
        for case in selected:
            report["cases"].append(failed_case_record(
                case, "harness_error", detail,
                replay_command(repo, args, case, artifacts, fixtures, evm_bin),
            ))
        return 1, finish_report(report)

    try:
        artifacts.mkdir(parents=True, exist_ok=True)
        # --artifacts is user-selectable: never assume an existing directory is ours
        # to delete. Each invocation gets new output and preserves earlier evidence.
        run_directory = Path(tempfile.mkdtemp(prefix="run-", dir=artifacts))
        report["run_directory"] = str(run_directory)
        classes = run_directory / "compiled"
        classes.mkdir()
    except OSError as exc:
        detail = f"cannot prepare compile directory: {exc}"
        report["harness_error"] = detail
        for case in selected:
            report["cases"].append(failed_case_record(
                case, "harness_error", detail,
                replay_command(repo, args, case, artifacts, fixtures, evm_bin),
            ))
        return 1, finish_report(report)

    source_paths: Dict[str, Path] = {}
    for case in selected:
        for rel, source_path in zip(case["sources"], case["_source_paths"]):
            source_paths[rel] = source_path
    oracle_path = (fixtures / "OracleMain.java").resolve()
    compile_argv = ["javac", "--release", "8", "-d", str(classes), str(oracle_path)]
    compile_argv.extend(str(source_paths[key]) for key in sorted(source_paths))
    report["source_sha256"] = {
        "OracleMain.java": sha256_file(oracle_path),
        **{key: sha256_file(path) for key, path in sorted(source_paths.items())},
    }
    compile_record = run_command(compile_argv, COMPILE_TIMEOUT_SECONDS)
    report["commands"]["compile"] = compile_record
    if compile_record["status"] == "timeout":
        compile_status, detail = "compile_timeout", "javac timed out"
    elif compile_record["status"] != "exited" or compile_record["returncode"] != 0:
        compile_status, detail = "compile_failure", "javac failed"
    else:
        compile_status, detail = "", ""
    if compile_status:
        for case in selected:
            report["cases"].append(failed_case_record(
                case, compile_status, detail,
                replay_command(repo, args, case, artifacts, fixtures, evm_bin),
            ))
        return 1, finish_report(report)

    runtime_hash: Optional[str] = None
    for case in selected:
        replay = replay_command(repo, args, case, artifacts, fixtures, evm_bin)
        result: Dict[str, Any] = {
            "id": case["id"], "stage": case["stage"], "status": "harness_error",
            "detail": "", "fixture": clean_case(case), "replay_command": replay,
            "gas_limit": case["gas_limit"],
        }
        root_relative = case["class"].replace(".", "/") + ".class"
        try:
            class_path = confined_compiled_class(
                classes, root_relative, f"{case['id']} root class"
            )
            supplied_paths = []
            if "class_files" in case:
                supplied_paths = [
                    confined_compiled_class(
                        classes, relative, f"{case['id']}.class_files[{index}]"
                    )
                    for index, relative in enumerate(case["class_files"])
                ]
        except HarnessError as exc:
            result["detail"] = str(exc)
            report["cases"].append(result)
            continue
        result["class_path"] = str(class_path)
        result["class_sha256"] = sha256_file(class_path)
        if "class_files" in case:
            result["class_files"] = list(case["class_files"])
            result["class_paths"] = [str(path) for path in supplied_paths]
            result["class_file_sha256"] = [
                {"path": relative, "sha256": sha256_file(path)}
                for relative, path in zip(case["class_files"], supplied_paths)
            ]
            result["entry_class"] = case["class"].replace(".", "/")

        decimal_args = [str(value) for value in case["args"]]
        oracle_argv = [
            "java", "-cp", str(classes), "OracleMain", case["class"], case["method"],
            *decimal_args,
        ]
        oracle_record = run_command(oracle_argv, float(case["timeout_seconds"]))
        result["oracle"] = oracle_record
        oracle_status, oracle_value, oracle_detail = parse_oracle(oracle_record)
        result["oracle_status"] = oracle_status
        if oracle_value is not None:
            result["oracle_value"] = oracle_value
        if oracle_status == "oracle_exception":
            result["oracle_exception"] = oracle_detail
        elif oracle_status != "value":
            result["status"] = oracle_status
            result["detail"] = oracle_detail
            report["cases"].append(result)
            continue

        expected_kind = case["expected_kind"]
        if oracle_status == "oracle_exception":
            if expected_kind != "java_exception":
                result["status"] = "oracle_exception"
                result["detail"] = f"unexpected oracle exception: {oracle_detail}"
                report["cases"].append(result)
                continue
            if oracle_detail != case["expected_exception"]:
                result["status"] = "oracle_exception"
                result["detail"] = (
                    f"expected oracle exception {case['expected_exception']}, got {oracle_detail}"
                )
                report["cases"].append(result)
                continue
        elif expected_kind == "java_exception":
            result["status"] = "mismatch"
            result["detail"] = (
                f"expected oracle exception {case['expected_exception']}, got value={oracle_value}"
            )
            report["cases"].append(result)
            continue

        evm_args = ",".join(decimal_args)
        evm_argv = [str(evm_bin)]
        if "class_files" in case:
            for supplied_path in supplied_paths:
                evm_argv.extend(["-class", str(supplied_path)])
            evm_argv.extend(["-entry-class", result["entry_class"]])
        else:
            # Keep the historical one-class CLI invocation byte-for-byte in the
            # absence of explicit bundle metadata.
            evm_argv.extend(["-class", str(class_path)])
        evm_argv.extend([
            "-method", case["method"], f"-args={evm_args}",
            "-gas", str(case["gas_limit"]),
        ])
        result["evm_argv"] = list(evm_argv)
        evm_record = run_command(evm_argv, float(case["timeout_seconds"]))
        result["evm"] = evm_record
        evm_status, evm_values, evm_detail = parse_evm(evm_record)
        result["evm_status"] = evm_status
        result.update(evm_values)
        if evm_status == "value":
            result["evm_value"] = evm_values["value"]
        elif evm_status == "java_exception":
            result["evm_exception"] = evm_values["exception"]
        observed_runtime_hash = evm_values.get("runtime_sha256")
        runtime_mismatch = False
        if observed_runtime_hash is not None:
            if runtime_hash is None:
                runtime_hash = observed_runtime_hash
            elif observed_runtime_hash != runtime_hash:
                runtime_mismatch = True
        if runtime_mismatch:
            result["status"] = "harness_error"
            result["detail"] = (
                f"runtime_sha256 differs across cases: {observed_runtime_hash} != {runtime_hash}; "
                f"underlying EVM classification={evm_status}"
            )
        elif evm_status not in ("value", "java_exception"):
            result["status"] = evm_status
            result["detail"] = evm_detail
        elif not 0 < evm_values["gas_used"] <= case["gas_limit"]:
            result["status"] = "evm_malformed"
            result["detail"] = "successful EVM gas_used must be positive and within gas_limit"
        elif expected_kind == "value" and evm_status == "java_exception":
            result["status"] = "mismatch"
            result["detail"] = (
                f"oracle=value={oracle_value} evm_exception={evm_values['exception']}"
            )
        elif expected_kind == "java_exception" and evm_status == "value":
            result["status"] = "mismatch"
            result["detail"] = (
                f"oracle_exception={oracle_detail} evm=value={evm_values['value']}"
            )
        elif expected_kind == "value" and evm_values["value"] != oracle_value:
            result["status"] = "mismatch"
            result["detail"] = f"oracle={oracle_value} evm={evm_values['value']}"
        elif (expected_kind == "java_exception"
              and evm_values["exception"] != case["expected_exception"]):
            result["status"] = "mismatch"
            result["detail"] = (
                f"expected exception {case['expected_exception']}; "
                f"oracle_exception={oracle_detail} evm_exception={evm_values['exception']}"
            )
        else:
            result["status"] = "pass"
            result["detail"] = ""
        report["cases"].append(result)

    report["runtime_sha256"] = runtime_hash
    report = finish_report(report)
    return (0 if report["failed"] == 0 else 1), report


def failed_case_record(case: Dict[str, Any], status: str, detail: str,
                       replay: str) -> Dict[str, Any]:
    return {
        "id": case["id"], "stage": case["stage"], "fixture": clean_case(case),
        "status": status, "detail": detail, "gas_limit": case["gas_limit"],
        "replay_command": replay,
    }


def finish_report(report: Dict[str, Any]) -> Dict[str, Any]:
    counts = Counter(case["status"] for case in report.get("cases", []))
    report["status_counts"] = dict(sorted(counts.items()))
    report["passed"] = counts.get("pass", 0)
    report["failed"] = sum(count for status, count in counts.items() if status != "pass")
    return report


def parser_for(repo: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=("m1", "m2", "m2b", "m3a", "m3b", "m3c", "m3d", "m4a", "m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc", "m5a", "m5ba", "all"), default="m5ba"
    )
    parser.add_argument("--tier", choices=("smoke", "fast", "full"), default="smoke")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--case", help="run one exact case (still subject to --stage)")
    parser.add_argument(
        "--artifacts", default=str(repo / "build/java-diff"),
        help="report and compiled-class output directory",
    )
    parser.add_argument(
        "--evm-bin", default=str(repo / "build/bin/jvmevm"),
        help="prebuilt jvmevm CLI path",
    )
    parser.add_argument(
        "--fixtures", default=str(repo / "jvmevm/testdata/differential"),
        help="fixture directory containing cases.json and OracleMain.java",
    )
    return parser


def print_summary(report: Dict[str, Any]) -> None:
    if report.get("harness_error") and not report.get("cases"):
        print(f"java-diff: harness_error: {report['harness_error']}", file=sys.stderr)
        return
    counts = report.get("status_counts", {})
    count_text = " ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    print(
        f"java-diff: selected={len(report.get('selected_ids', []))} "
        f"passed={report.get('passed', 0)} failed={report.get('failed', 0)} {count_text}".rstrip()
    )
    for case in report.get("cases", []):
        if case.get("status") != "pass":
            print(f"  {case['id']}: {case['status']}: {case.get('detail', '')}", file=sys.stderr)
    print(f"java-diff: report={Path(report['artifacts']) / 'report.json'}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    repo = Path(__file__).resolve().parents[1]
    args = parser_for(repo).parse_args(argv)
    artifacts = Path(args.artifacts).expanduser().resolve()
    try:
        code, report = execute(args)
    except Exception as exc:  # Last-resort artifact rather than an unreported pass/failure.
        report = {
            "schema_version": 1, "stage": args.stage, "tier": args.tier,
            "seed": args.seed, "selected_ids": [], "cases": [],
            "artifacts": str(artifacts), "harness_error": f"unexpected harness error: {exc}",
        }
        code = 1
    try:
        write_report(artifacts, report)
    except OSError as exc:
        print(f"java-diff: cannot write artifacts: {exc}", file=sys.stderr)
        return 1
    print_summary(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
