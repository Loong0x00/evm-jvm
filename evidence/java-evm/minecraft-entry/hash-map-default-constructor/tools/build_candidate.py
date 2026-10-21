#!/usr/bin/env python3
"""Build the P35 LOCAL engine from the exact authorized P34 source baseline."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
PINS = json.loads((STAGE / "pins.json").read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_candidate.py OUTPUT_DIR")
    out = Path(sys.argv[1]).resolve()
    if out.parent != ROOT / "build" or not out.name.startswith("java-diff-mc-hash-map-default-constructor-build-"):
        raise SystemExit("OUTPUT_DIR must be a fresh build/java-diff-mc-hash-map-default-constructor-build-* path")
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.mkdir(parents=True)
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               PYTHONDONTWRITEBYTECODE="1", NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))

    proof = run([sys.executable, str(STAGE / "tools/verify_source.py")], cwd=ROOT, env=env, timeout=240)
    (out / "source-proof.log").write_text(proof.stdout)
    if proof.returncode != 0:
        raise RuntimeError(f"append-only source/classfile proof failed ({proof.returncode}):\n{proof.stdout[-4000:]}")
    proof_data = json.loads(proof.stdout)
    if proof_data.get("status") != "PASS" or proof_data.get("bootstrapRoot") != PINS["bootstrapRoot"]:
        raise RuntimeError("source proof did not authenticate the pinned 101-leaf bootstrap root")

    engine_dir = out / "engine"
    engine_dir.mkdir()
    for filename in ("MCEntryInterpreter.sol", "build.js"):
        shutil.copy2(STAGE / "engine" / filename, engine_dir / filename)
    built = run(["node", str(engine_dir / "build.js")], cwd=ROOT, env=env)
    (out / "engine-build.log").write_text(built.stdout)
    if built.returncode != 0:
        raise RuntimeError(f"fresh solc build failed ({built.returncode}):\n{built.stdout[-4000:]}")
    artifact_path = engine_dir / "MCEntryInterpreter.json"
    artifact = json.loads(artifact_path.read_text())
    runtime = bytes.fromhex(artifact["deployedBytecode"].removeprefix("0x"))
    runtime_sha = sha(runtime)
    runtime_keccak = artifact["codeHashes"]["runtimeKeccak256"].removeprefix("0x")
    if len(runtime) != PINS["engineRuntimeBytes"] or len(runtime) > PINS["runtimeCapBytes"]:
        raise RuntimeError(f"engine runtime length {len(runtime)} disagrees with P35 LOCAL cap/pin")
    if runtime_sha != PINS["engineRuntimeSHA256"] or runtime_keccak != PINS["engineRuntimeKeccak256"]:
        raise RuntimeError("freshly compiled engine runtime differs from its pinned SHA-256/Keccak")
    if sha((engine_dir / "MCEntryInterpreter.sol").read_bytes()) != PINS["engineSourceSHA256"]:
        raise RuntimeError("fresh engine source copy differs from stage pin")
    if artifact["compiler"]["version"] != "0.8.30+commit.73712a01.Emscripten.clang":
        raise RuntimeError("unexpected Solidity compiler version")
    (out / "source-proof.json").write_text(json.dumps({
        **proof_data,
        "engineRuntimeBytes": len(runtime),
        "engineRuntimeSHA256": runtime_sha,
        "engineRuntimeKeccak256": runtime_keccak,
        "engineInitBytes": len(bytes.fromhex(artifact["bytecode"].removeprefix("0x"))),
        "engineSourceSHA256": PINS["engineSourceSHA256"],
        "runtimeExecutionBoundary": "LOCAL preinstalled-code Call; oversized runtime is not a CREATE/EIP170 claim",
    }, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "profile": PINS["profile"],
        "status": "fresh P34-based source proof and LOCAL engine artifact built",
        "bootstrapRoot": PINS["bootstrapRoot"],
        "bootstrapCount": PINS["bootstrapCount"],
        "engineRuntimeBytes": len(runtime),
        "engineRuntimeSHA256": runtime_sha,
        "engineRuntimeKeccak256": runtime_keccak,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
