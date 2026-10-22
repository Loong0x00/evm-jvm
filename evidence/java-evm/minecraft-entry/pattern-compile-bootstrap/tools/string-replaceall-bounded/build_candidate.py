#!/usr/bin/env python3
"""Freshly build and source-prove the P38 candidate from the exact P37 snapshot."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[3]
REF = STAGE / "reference/string-replaceall-bounded"
SOURCE = STAGE / "bootstrap/string-replaceall-bounded"
PINS = json.loads((REF / "pins.json").read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_candidate.py OUTPUT_DIR")
    out = Path(sys.argv[1]).resolve()
    if out.parent != ROOT / "build" or not out.name.startswith("java-diff-mc-string-replaceall-bounded-build-"):
        raise SystemExit("OUTPUT_DIR must be a fresh build/java-diff-mc-string-replaceall-bounded-build-* path")
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.mkdir(parents=True)
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1",
               NODE_PATH="/home/user/evm-jvm/string-replaceall-bounded/jvmevm/runtime/node_modules")

    for role in ("engine", "coordinator"):
        target = out / role
        target.mkdir()
        shutil.copy2(REF / role / f"MCEntry{'Interpreter' if role == 'engine' else 'Coordinator'}.sol", target)
        shutil.copy2(REF / role / "build.js", target)
        built = run(["node", str(target / "build.js")], cwd=ROOT, env=env)
        (out / f"{role}-build.log").write_text(built.stdout)
        if built.returncode:
            raise RuntimeError(f"fresh {role} build failed ({built.returncode}):\n{built.stdout[-5000:]}")

    engine_path = out / "engine/MCEntryInterpreter.json"
    coordinator_path = out / "coordinator/MCEntryCoordinator.json"
    engine = json.loads(engine_path.read_text())
    coordinator = json.loads(coordinator_path.read_text())
    engine_runtime = bytes.fromhex(engine["deployedBytecode"].removeprefix("0x"))
    coordinator_runtime = bytes.fromhex(coordinator["deployedBytecode"].removeprefix("0x"))
    if len(engine_runtime) > PINS["runtimeCapBytes"]:
        raise RuntimeError(f"engine runtime {len(engine_runtime)} exceeds explicit LOCAL cap")
    if len(engine_runtime) != PINS["engineRuntimeBytes"] or sha(engine_runtime) != PINS["engineRuntimeSHA256"]:
        raise RuntimeError("fresh engine runtime differs from P38 size/SHA pin")
    if engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x") != PINS["engineRuntimeKeccak256"]:
        raise RuntimeError("fresh engine Keccak differs from P38 pin")
    if len(coordinator_runtime) > 24576:
        raise RuntimeError("coordinator exceeds ordinary-CREATE code size")
    if len(coordinator_runtime) != PINS["coordinatorRuntimeBytes"] or sha(coordinator_runtime) != PINS["coordinatorRuntimeSHA256"]:
        raise RuntimeError("fresh coordinator runtime differs from P38 size/SHA pin")
    if coordinator["codeHashes"]["runtimeKeccak256"].removeprefix("0x") != PINS["coordinatorRuntimeKeccak256"]:
        raise RuntimeError("fresh coordinator Keccak differs from P38 pin")
    if engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x") not in (REF / "coordinator/MCEntryCoordinator.sol").read_text():
        raise RuntimeError("coordinator does not authenticate this engine runtime")

    proof = run([sys.executable, str(REF / "verify_source.py"), "--artifacts", str(out),
                 str(out / "source-proof.json")], cwd=ROOT, env=env, timeout=900)
    (out / "source-proof.log").write_text(proof.stdout)
    if proof.returncode:
        raise RuntimeError(f"P37 source/root/ABI proof failed ({proof.returncode}):\n{proof.stdout[-5000:]}")
    result = json.loads((out / "source-proof.json").read_text())
    if result.get("status") != "PASS" or result.get("candidateBootstrapRoot") != PINS["bootstrap"]["root"]:
        raise RuntimeError("fresh P38 source proof did not authenticate its pinned root")
    summary = {
        "profile": PINS["profile"],
        "status": "fresh P37-source-based engine/coordinator build and source proof passed",
        "bootstrapRoot": result["candidateBootstrapRoot"],
        "bootstrapCount": result["bootstrapCount"],
        "engineRuntimeBytes": len(engine_runtime),
        "engineRuntimeSHA256": sha(engine_runtime),
        "engineRuntimeKeccak256": engine["codeHashes"]["runtimeKeccak256"].removeprefix("0x"),
        "coordinatorRuntimeBytes": len(coordinator_runtime),
        "coordinatorRuntimeSHA256": sha(coordinator_runtime),
        "coordinatorRuntimeKeccak256": coordinator["codeHashes"]["runtimeKeccak256"].removeprefix("0x"),
        "executionBoundary": "LOCAL preinstalled-code Call for engine; coordinator only is standard CREATE-sized",
        "sourceProof": "source-proof.json",
    }
    (out / "build-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
