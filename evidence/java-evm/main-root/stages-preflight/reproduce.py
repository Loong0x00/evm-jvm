#!/usr/bin/env python3
"""Fresh MR0 pre-Java phase COPY reproducer (functional, not acceptance gate)."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "transport" / "mr0_stages_session.go.txt"
ART = ROOT / "evidence/java-evm/main-root/session-preflight/artifacts"
ZIP = ROOT / "evidence/java-evm/main-root/session-preflight/results/final3/fixtures/positive.zip"


def run(out, deadline, label, argv, check=True):
    remain = deadline - time.monotonic()
    if remain <= 0:
        raise RuntimeError("single 20-minute budget expired")
    env = dict(os.environ, TMPDIR=str(out / "tmp"), PYTHONDONTWRITEBYTECODE="1")
    with (out / (label + ".log")).open("w") as log:
        # Deliberately no start_new_session and no GNU timeout: all children retain
        # the caller's process group. This functional recipe does not claim RSS.
        p = subprocess.run(list(map(str, argv)), cwd=out if label == "go-build" else ROOT,
                           env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=remain, check=False)
    if check and p.returncode:
        raise RuntimeError(f"{label}: exit {p.returncode}; see {label}.log")
    return p.returncode


def head(world):
    return json.loads((world / "durable-head.json").read_text())


def invoke(out, deadline, exe, world, mode):
    return run(out, deadline, mode, [exe, mode, world,
        ART / "coordinator/MR0MainCoordinator.json", ART / "engine/MR0MainInterpreter.json", ZIP, "1"])


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: reproduce.py build/java-diff-mc-main-root-stages-NAME")
    out = Path(sys.argv[1]).resolve()
    required = ROOT / "build/java-diff-mc-main-root-stages-"
    if not str(out).startswith(str(required)) or out.exists():
        raise SystemExit("refuse nonfresh ignored stages output")
    if not ART.is_dir() or not ZIP.is_file():
        raise SystemExit("pinned prior COPY artifacts/fixture absent")
    out.mkdir(parents=True); (out / "tmp").mkdir()
    shutil.copy2(SOURCE, out / "main.go")
    began = time.monotonic(); deadline = began + 1200
    run(out, deadline, "go-build", ["go", "build", "-o", "mr0-stages", "."])
    exe, world = out / "mr0-stages", out / "world"

    # A real owned failpoint proves a factory error creates no authoritative Head.
    failworld = out / "factory-failure"
    env = dict(os.environ, TMPDIR=str(out / "tmp"), MR0_ATOMICITY_TESTING="1", MR0_ATOMICITY_FAULT="manifest-before-create")
    with (out / "factory-failure.log").open("w") as log:
        failed = subprocess.run([exe, "factory-initial", failworld, ART / "coordinator/MR0MainCoordinator.json", ART / "engine/MR0MainInterpreter.json", ZIP, "1"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    assert failed != 0 and not (failworld / "durable-head.json").exists()

    phases = ["factory-initial", "verify-initial", "as0-input", "index-scan", "di0-live", "di0-final", "package-ready", "start-ready"]
    observed = []
    for phase in phases:
        invoke(out, deadline, exe, world, phase)
        h = head(world)
        observed.append({"operation": phase, "phase": h["phase"], "root": h["trieRoot"], "epoch": h["epoch"], "lifecycle": h["lifecycle"], "decoders": len(h.get("decoders") or [])})
    initial = observed[0]
    assert initial["phase"] == "input-open"
    h = head(world)
    assert h["phase"] == "java-running" and h["epoch"] == 1 and h["lifecycle"] == 1
    assert h["engine"] == "0x4d52304d41494e454e47494e4500000000000001" and h["engineNonce"] == 0
    assert h["store"] == "0x4452f819ec6aae900eb2ca0cb4f372144ec129b9" and h["index"] != "0x0000000000000000000000000000000000000000"
    (out / "summary.json").write_text(json.dumps({
        "base": "752e9d56d", "sourceSHA256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "zipSHA256": hashlib.sha256(ZIP.read_bytes()).hexdigest(), "factoryFailureNoHead": True,
        "operations": observed, "elapsedSeconds": time.monotonic() - began,
        "scope": "COPY functional phase proof only; no acceptance, full Session, resource gate, or Java readiness claim"
    }, indent=2) + "\n")

if __name__ == "__main__":
    main()
