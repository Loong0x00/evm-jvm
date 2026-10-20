#!/usr/bin/env python3
"""Prove raw150 is only a quota/config-root append to guarded LOCAL1M source."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
PINS = json.loads((STAGE / "pins.json").read_text())
BASE_COMMIT = PINS["baseCommit"]
BASE_STAGE = "evidence/java-evm/minecraft-entry/array-list-local1m-safe"


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{BASE_STAGE}/{path}"], cwd=ROOT)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old)
    return text.replace(old, new, 1)


base_engine = git_blob("engine/MCEntryInterpreter.sol").decode()
engine_path = STAGE / "engine/MCEntryInterpreter.sol"
engine = engine_path.read_text()
assert sha(base_engine.encode()) == "5fcfe78e13f0e0b2b18e5ccb8bb875f5c2f699a4c4805a8811a33effa6b0d32f"
expected_engine = replace_once(base_engine, "MAX_RAW_CLASSES = 75", "MAX_RAW_CLASSES = 150")
expected_engine = replace_once(expected_engine, "MAX_RAW_BYTES = 531965", "MAX_RAW_BYTES = 1063930")
expected_engine = replace_once(expected_engine, "uint32(75), uint32(531965),", "uint32(150), uint32(1063930),")
assert engine == expected_engine, "engine has changes beyond the two scoped guards and matching config-root quotas"
assert PINS["engineSourceSHA256"] == sha(engine.encode())
assert "MAX_CHECKPOINT_BYTES = 1048576" in engine, "checkpoint quota changes only after a measured refusal"
assert "uint32(1048576)" in engine, "runtime/checkpoint config dimensions must remain pinned unless measured"

base_coord = git_blob("coordinator/MCEntryCoordinator.sol").decode()
coord_path = STAGE / "coordinator/MCEntryCoordinator.sol"
coord = coord_path.read_text()
expected_coord = base_coord
for typ in ("address", "bytes32", "uint32", "bytes"):
    expected_coord = replace_once(expected_coord, f"{typ}[75]", f"{typ}[150]")
expected_coord = replace_once(expected_coord, "n == 0 || n > 75", "n == 0 || n > 150")
expected_coord = replace_once(expected_coord, "if (size == 0 || size > 531965) revert MR0Error(11);",
                              "if (size == 0 || size > 1063930) revert MR0Error(11);")
expected_coord = replace_once(expected_coord, "if (uint256(total) + size > 531965) revert MR0Error(12);",
                              "if (uint256(total) + size > 1063930) revert MR0Error(12);")
old_hash = "54a6ccd0ea830c5b0665d8a97587db038539d3faa46583462a7b64c2f0f74880"
new_hash = PINS.get("engineRuntimeKeccak256", "").removeprefix("0x")
assert len(new_hash) == 64, "pins must contain the freshly built engine runtime Keccak"
expected_coord = replace_once(expected_coord, old_hash, new_hash)
assert coord == expected_coord, "coordinator has changes beyond fixed array/quota/hash binding updates"
assert PINS["coordinatorSourceSHA256"] == sha(coord.encode())

# The generated fixtures and bootstrap compiler inputs are byte-identical to
# the accepted safe stage. Source equality plus the exact engine patch proves
# all 99 image literals/root ordering and all Java code remain unchanged.
for directory in ("bootstrap", "fixtures/src"):
    rows = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE_COMMIT, f"{BASE_STAGE}/{directory}"],
        cwd=ROOT, text=True,
    ).splitlines()
    expected_names = {row.removeprefix(f"{BASE_STAGE}/") for row in rows}
    actual_names = {p.relative_to(STAGE).as_posix() for p in (STAGE / directory).rglob("*") if p.is_file()}
    assert actual_names == expected_names, (directory, sorted(actual_names ^ expected_names))
    for name in sorted(expected_names):
        assert (STAGE / name).read_bytes() == git_blob(name), name

assert PINS["rawClassLimit"] == 150
assert PINS["rawByteLimit"] == 1063930
assert PINS["runtimeCapBytes"] == 1048576
assert PINS["checkpointCapBytes"] == 1048576
assert PINS["bootstrapCount"] == 99
assert PINS["globalNativeBindings"] == 21
assert PINS["stringLocalBinding"] == 12
print(json.dumps({
    "profile": PINS["profile"],
    "baseCommit": BASE_COMMIT,
    "engineSourceSHA256": sha(engine.encode()),
    "coordinatorSourceSHA256": sha(coord.encode()),
    "scopedChangesOnly": True,
    "bootstrapImages": 99,
    "rawClassLimit": 150,
    "rawByteLimit": 1063930,
    "diagnosticClassMaximum": 249,
    "runtimeCapBytes": 1048576,
    "checkpointCapBytes": 1048576,
}, indent=2))
