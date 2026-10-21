#!/usr/bin/env python3
"""Verify the append-only P33 2 MiB checkpoint-only source delta."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
BASE = STAGE.parent / "checkpoint-2m-base-p33"
ROOT = STAGE.parents[3]
PINS = json.loads((STAGE / "pins.json").read_text())
MANIFEST_PATH = BASE / "SOURCE_MANIFEST.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old)
    return text.replace(old, new, 1)

assert sha(MANIFEST_PATH.read_bytes()) == PINS["baseSourceManifestSHA256"]
assert MANIFEST["acceptedSourceCommit"] == "217e2e2b6"
assert MANIFEST["profile"] == "MC-MATH-DOUBLE-MIN-MAX-P33"
assert MANIFEST["runtimeBytes"] == PINS["baseEngineRuntimeBytes"] == 398336
assert MANIFEST["runtimeCapBytes"] == 1048576
assert MANIFEST["checkpointCapBytes"] == 1048576
assert MANIFEST["bootstrapImages"] == PINS["bootstrapCount"] == 100
assert MANIFEST["globalNativeBindings"] == PINS["globalNativeBindings"] == 21
assert MANIFEST["rawLimits"] == [PINS["rawClassLimit"], PINS["rawByteLimit"]] == [150, 1063930]
assert MANIFEST["noOriginalJarClassResourceOrWorldData"] is True
assert MANIFEST["noOriginalReceiptsOrCheckpoints"] is True
assert len(MANIFEST["files"]) == 64
for row in MANIFEST["files"]:
    snapshot_file = BASE / row["file"]
    data = snapshot_file.read_bytes()
    assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["file"]

base_engine_path = BASE / "engine/MCEntryInterpreter.sol"
base_coordinator_path = BASE / "coordinator/MCEntryCoordinator.sol"
base_engine = base_engine_path.read_text()
base_coordinator = base_coordinator_path.read_text()
file_rows = {row["file"]: row for row in MANIFEST["files"]}
assert sha(base_engine_path.read_bytes()) == PINS["baseEngineSourceSHA256"] == file_rows["engine/MCEntryInterpreter.sol"]["sha256"]
assert sha(base_coordinator_path.read_bytes()) == PINS["baseCoordinatorSourceSHA256"] == file_rows["coordinator/MCEntryCoordinator.sol"]["sha256"]
assert sha(bytes.fromhex(json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())["deployedBytecode"].removeprefix("0x"))) == PINS["baseEngineRuntimeSHA256"]

expected_engine = replace_once(base_engine, "MAX_CHECKPOINT_BYTES = 1048576", "MAX_CHECKPOINT_BYTES = 2097152")
expected_engine = replace_once(expected_engine, "uint32(1048576)", "uint32(2097152)")
engine_path = STAGE / "engine/MCEntryInterpreter.sol"
engine = engine_path.read_text()
assert engine == expected_engine, "engine differs from authenticated P33 snapshot beyond checkpoint budget + config-root leaf"
assert engine.count("MAX_CHECKPOINT_BYTES = 2097152") == 1
assert "MAX_CHECKPOINT_BYTES = 1048576" not in engine
assert engine.count("uint32(2097152)") == 1
assert "uint32(1048576)" not in engine
assert "MAX_ARRAY_ELEMENTS = 262144" in engine
assert "MAX_RAW_CLASSES = 150" in engine and "MAX_RAW_BYTES = 1063930" in engine

# Exact source replacement above proves the same ordered 100 bootstrap images,
# 21 bindings, domains, heap/array/class/raw caps, schema, and EVM semantics.
bootstrap_functions = re.findall(r"function (_bootstrap\w+)\(", engine)
assert len(bootstrap_functions) == 101 and "_bootstrapRoot" in bootstrap_functions
assert "bytes32[] memory h = new bytes32[](100);" in engine
# The exact P33 source replacement above is the binding-preservation proof; the
# authenticated snapshot pin records the existing 21 bindings, with no addition.
assert PINS["runtimeCapBytes"] == 1048576
assert PINS["checkpointCapBytes"] == 2097152
assert PINS["rawClassLimit"] == 150 and PINS["rawByteLimit"] == 1063930
assert PINS["newNativeBindings"] == 0

expected_coordinator = replace_once(
    base_coordinator,
    PINS["baseEngineRuntimeKeccak256"],
    PINS["engineRuntimeKeccak256"],
)
coordinator_path = STAGE / "coordinator/MCEntryCoordinator.sol"
coordinator = coordinator_path.read_text()
assert coordinator == expected_coordinator, "coordinator differs beyond exact P34 engine-codehash authentication repin"
assert f'hex"{PINS["engineRuntimeKeccak256"]}"' in coordinator
assert f'hex"{PINS["engineAddress"][2:]}"' in coordinator
assert f'engineHex   = "{PINS["engineAddress"]}"' in (STAGE / "tools/evm_driver.go").read_text()
assert f'callerHex   = "{PINS["ownerAddress"]}"' in (STAGE / "tools/evm_driver.go").read_text()
assert sha(engine_path.read_bytes()) == PINS["engineSourceSHA256"]
assert sha(coordinator_path.read_bytes()) == PINS["coordinatorSourceSHA256"]
assert PINS["engineRuntimeBytes"] <= PINS["runtimeCapBytes"] == 1048576
assert PINS["engineRuntimeSHA256"] and PINS["engineRuntimeKeccak256"]
assert PINS["coordinatorRuntimeBytes"] <= 24576
assert PINS["coordinatorRuntimeSHA256"] and PINS["coordinatorRuntimeKeccak256"]

transport = (STAGE / "transport/checkpoint.go").read_text()
assert "Legacy1MiB CheckpointProfile = iota" in transport
assert "MinecraftCheckpoint2MiB" in transport
assert "legacyCheckpointBytes = uint32(1 << 20)" in transport
assert "checkpoint2MBytes     = uint32(2 << 20)" in transport

print(json.dumps({
    "status": "checkpoint-only P33 source delta verified",
    "baseSourceManifestSHA256": sha(MANIFEST_PATH.read_bytes()),
    "engineSourceSHA256": sha(engine_path.read_bytes()),
    "coordinatorSourceSHA256": sha(coordinator_path.read_bytes()),
    "runtimeCapBytes": PINS["runtimeCapBytes"],
    "checkpointCapBytes": PINS["checkpointCapBytes"],
    "bootstrapCount": 100,
    "nativeBindings": 21,
    "rawLimits": [150, 1063930],
    "sourceDelta": ["MAX_CHECKPOINT_BYTES 1048576->2097152", "config-root checkpoint leaf 1048576->2097152",
                    "coordinator engine codehash repinned to newly compiled runtime"],
}, indent=2))
