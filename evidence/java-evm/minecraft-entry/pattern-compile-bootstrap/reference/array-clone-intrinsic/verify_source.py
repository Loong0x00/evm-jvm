#!/usr/bin/env python3
"""Source-only P36->array-clone-intrinsic append proof; never reads original Minecraft inputs."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[6]
STAGE = REPO / "evidence/java-evm/minecraft-entry/pattern-compile-bootstrap"
BASE = REPO / "evidence/java-evm/minecraft-entry/array-clone-source-base-p36"
CANDIDATE = STAGE / "bootstrap/array-clone-intrinsic"
ENGINE_ARTIFACTS = Path(os.environ.get(
    "ARRAY_CLONE_ENGINE_ARTIFACT_DIR",
    STAGE / "tools/array-clone-intrinsic/generated/engine"))
COORDINATOR_ARTIFACTS = Path(os.environ.get(
    "ARRAY_CLONE_COORDINATOR_ARTIFACT_DIR",
    STAGE / "tools/array-clone-intrinsic/generated/coordinator"))
RESULT = Path(os.environ.get(
    "ARRAY_CLONE_SOURCE_PROOF_OUTPUT",
    STAGE / "reference/array-clone-intrinsic/source-proof.json"))
OLD_DOMAIN = "MC-PATTERN-COMPILE-P36-PARENT"
NEW_DOMAIN = "MC-ARRAY-CLONE-INTRINSIC-P37"
OLD_BOOTSTRAP_ROOT = "851a47c08ef61b29471de2db8b764c88989b18e2c523490bbe9b0588a8725faa"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def function_blocks(source: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^    function\s+([A-Za-z0-9_]+)\s*\(", source, re.M))
    out = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        out.append((match.group(1), source[match.start():end]))
    return out


def function_map(source: str) -> dict[tuple[str, int], str]:
    counts: dict[str, int] = {}
    out = {}
    for name, body in function_blocks(source):
        ordinal = counts.get(name, 0)
        counts[name] = ordinal + 1
        out[(name, ordinal)] = body
    return out


def constants(source: str) -> dict[str, str]:
    rows = {}
    for match in re.finditer(r"^\s*[^\n;]*?\bconstant\s+([A-Za-z0-9_]+)\s*=\s*([^;]+);", source, re.M):
        rows[match.group(1)] = match.group(2).strip()
    return rows


def root_record(root_helper: Path, source: str, domain: str) -> dict:
    spec = importlib.util.spec_from_file_location("array_clone_root_helper", root_helper)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    env = dict(os.environ, NODE_PATH=str(REPO / "jvmevm/runtime/node_modules"))
    return module.root_record(source, f"JVMEVM:{domain}:BOOTSTRAP:1", REPO, env)


def main() -> None:
    manifest_bytes = (BASE / "SOURCE_MANIFEST.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest["sourceOnly"] is True
    assert manifest["noOriginalJarClassesResourcesWorldsCheckpointsReceiptsOrBindingLists"] is True
    verified = []
    for row in manifest["files"]:
        data = (BASE / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
        verified.append(row["path"])
    base_pins = json.loads((BASE / "pins.json").read_text())
    assert base_pins["bootstrapCount"] == 103
    assert base_pins["bootstrapRoot"] == OLD_BOOTSTRAP_ROOT

    baseline = (BASE / "engine/MCEntryInterpreter.sol").read_text()
    candidate = (CANDIDATE / "MCEntryInterpreter.sol").read_text()
    base_root = root_record(BASE / "reference/root_helper.py", baseline, OLD_DOMAIN)
    candidate_root = root_record(STAGE / "reference/array-clone-intrinsic/root_helper.py",
                                 candidate, OLD_DOMAIN)
    assert base_root["root"] == candidate_root["root"] == OLD_BOOTSTRAP_ROOT
    assert len(base_root["leaves"]) == len(candidate_root["leaves"]) == 103
    assert base_root["leaves"] == candidate_root["leaves"], "bootstrap image bytes/order changed"

    before_functions = function_map(baseline)
    after_functions = function_map(candidate)
    assert before_functions.keys() == after_functions.keys(), "function inventory changed"
    changed = sorted(name for name in before_functions if before_functions[name] != after_functions[name])
    assert changed == [("_execute", 0), ("_resolveVirtual", 0)], changed
    for name in ("_nativeBinding", "_stringNativeBinding", "_vfsNativeBinding"):
        before = [body for function, body in function_blocks(baseline) if function == name]
        after = [body for function, body in function_blocks(candidate) if function == name]
        assert before == after, f"native binding semantics changed: {name}"

    before_constants = constants(baseline)
    after_constants = constants(candidate)
    assert before_constants.keys() == after_constants.keys(), "constant inventory changed"
    changed_constants = sorted(k for k in before_constants if before_constants[k] != after_constants[k])
    expected_constants = sorted([
        "EMPTY_ARGS_COMMITMENT", "DROOT", "DART", "DCFG", "DMACH", "DSEED", "DVFS", "DFILE",
    ])
    assert changed_constants == expected_constants, changed_constants
    assert after_constants["DBOOT"] == before_constants["DBOOT"]
    assert NEW_DOMAIN in candidate and OLD_DOMAIN in candidate

    engine_artifact = json.loads((ENGINE_ARTIFACTS / "MCEntryInterpreter.json").read_text())
    coordinator_artifact = json.loads((COORDINATOR_ARTIFACTS / "MCEntryCoordinator.json").read_text())
    old_engine_artifact = json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())
    old_coordinator_artifact = json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())
    coordinator_source = (CANDIDATE / "MCEntryCoordinator.sol").read_text()
    before_coord_source = (BASE / "coordinator/MCEntryCoordinator.sol").read_text()
    before_coord_functions = function_map(before_coord_source)
    after_coord_functions = function_map(coordinator_source)
    assert before_coord_functions == after_coord_functions, "coordinator function semantics changed"
    before_coord_constants = constants(before_coord_source)
    after_coord_constants = constants(coordinator_source)
    assert before_coord_constants.keys() == after_coord_constants.keys(), "coordinator constant inventory changed"
    changed_coord_constants = sorted(k for k in before_coord_constants
                                     if before_coord_constants[k] != after_coord_constants[k])
    assert changed_coord_constants == ["CLASS_DOMAIN", "ENGINE_CODEHASH", "PACKAGE_DOMAIN",
                                       "SEED_DOMAIN", "VM_DOMAIN"], changed_coord_constants
    assert engine_artifact["abi"] == old_engine_artifact["abi"], "engine ABI changed"
    assert engine_artifact["storageLayout"] == old_engine_artifact["storageLayout"], "engine storage changed"
    assert coordinator_artifact["abi"] == old_coordinator_artifact["abi"], "coordinator ABI changed"
    assert coordinator_artifact["storageLayout"] == old_coordinator_artifact["storageLayout"], "coordinator storage changed"
    engine_runtime = bytes.fromhex(engine_artifact["deployedBytecode"].removeprefix("0x"))
    coordinator_runtime = bytes.fromhex(coordinator_artifact["deployedBytecode"].removeprefix("0x"))
    engine_init = bytes.fromhex(engine_artifact["bytecode"].removeprefix("0x"))
    coordinator_init = bytes.fromhex(coordinator_artifact["bytecode"].removeprefix("0x"))
    engine_keccak = engine_artifact["codeHashes"]["runtimeKeccak256"]
    coordinator_keccak = coordinator_artifact["codeHashes"]["runtimeKeccak256"]
    env = dict(os.environ, NODE_PATH=str(REPO / "jvmevm/runtime/node_modules"))
    for label, runtime, artifact in (("engine", engine_runtime, engine_artifact),
                                     ("coordinator", coordinator_runtime, coordinator_artifact)):
        actual_sha = sha(runtime)
        actual_keccak = subprocess.check_output(
            ["node", "-e", "const{keccak256}=require('js-sha3');const fs=require('fs');process.stdout.write(keccak256(Buffer.from(fs.readFileSync(0,'utf8').trim(),'hex')));"],
            cwd=REPO, env=env, input=runtime.hex(), text=True,
        ).strip()
        assert actual_sha == artifact["codeHashes"]["runtimeSHA256"], f"{label} runtime SHA mismatch"
        assert actual_keccak == artifact["codeHashes"]["runtimeKeccak256"], f"{label} runtime Keccak mismatch"
    assert engine_keccak.removeprefix("0x") in coordinator_source
    assert len(engine_runtime) < 1048576 and len(coordinator_runtime) <= 24576
    assert engine_artifact["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"
    assert coordinator_artifact["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"

    pins = json.loads((BASE / "pins.json").read_text())
    proof = {
        "status": "PASS",
        "profile": "MC-ARRAY-CLONE-INTRINSIC-P37",
        "sourceOnly": True,
        "baseSourceManifestSHA256": sha(manifest_bytes),
        "baseSourceFilesVerified": verified,
        "baseSourceCommit": manifest["acceptedSourceCommit"],
        "baseBootstrapRoot": base_root["root"],
        "candidateBootstrapRoot": candidate_root["root"],
        "bootstrapCount": len(candidate_root["leaves"]),
        "bootstrapLeavesAndOrderIdentical": True,
        "changedFunctions": [name for name, _ in changed],
        "changedTypes": ["VirtualResolution: arrayCloneIntrinsic + symbolic ArrayType"],
        "changedEngineConstants": changed_constants,
        "changedCoordinatorConstants": changed_coord_constants,
        "engineABIUnchanged": True,
        "engineStorageLayoutUnchanged": True,
        "coordinatorABIUnchanged": True,
        "coordinatorStorageLayoutUnchanged": True,
        "globalNativeBindingsBefore": pins["globalNativeBindings"],
        "globalNativeBindingsAfter": pins["globalNativeBindings"],
        "stringLocalBindingsBefore": pins["stringLocalBinding"],
        "stringLocalBindingsAfter": pins["stringLocalBinding"],
        "newOperationalBindings": 0,
        "systemArraycopyAndWireCodecFunctionsUnchanged": True,
        "runtimeCapBytes": 1048576,
        "engine": {
            "sourceSHA256": sha((CANDIDATE / "MCEntryInterpreter.sol").read_bytes()),
            "initBytes": len(engine_init),
            "runtimeBytes": len(engine_runtime),
            **engine_artifact["codeHashes"],
        },
        "coordinator": {
            "sourceSHA256": sha((CANDIDATE / "MCEntryCoordinator.sol").read_bytes()),
            "initBytes": len(coordinator_init),
            "runtimeBytes": len(coordinator_runtime),
            **coordinator_artifact["codeHashes"],
        },
        "runtimeBoundary": "local preinstalled-code Call; engine is not an EIP170/CREATE deployment claim",
        "originalMinecraftInputsRead": False,
        "hostOriginalExecution": False,
    }
    RESULT.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
