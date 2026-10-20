#!/usr/bin/env python3
"""Pinned offline build and exact normalized-source check for raw72/q65536."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parents[3]
BASE = STAGE.parent / "parent-max-objects-4096"
if len(sys.argv) != 2:
    raise SystemExit("usage: build.py build/java-diff-mc-raw72-q65536-build-TAG")
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build" and OUT.name.startswith("java-diff-mc-raw72-q65536-build-")
assert not OUT.exists(), "build output is append-only"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


base_engine = (BASE / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (STAGE / "engine/MCEntryInterpreter.sol").read_text()
expected_engine = base_engine
for old, new in (
    ("uint256 private constant MAX_RAW_CLASSES = 71;", "uint256 private constant MAX_RAW_CLASSES = 72;"),
    ("uint256 private constant MAX_RAW_BYTES = 471911;", "uint256 private constant MAX_RAW_BYTES = 513384;"),
    ("if (jvm == 0 || jvm > 4096 || internalSteps == 0 || internalSteps > 4096) {",
     "if (jvm == 0 || jvm > 65536 || internalSteps == 0 || internalSteps > 4096) {"),
    ("            uint32(71), uint32(471911), uint32(64), uint32(32), uint32(65536),",
     "            uint32(72), uint32(513384), uint32(64), uint32(32), uint32(65536),"),
):
    expected_engine = replace_once(expected_engine, old, new)
assert engine == expected_engine, "engine source differs outside four authorized exact edits"
assert "JVMEVM:MC-RANDOM-CLASS-P24" in engine
for invariant in (
    "uint256 private constant MAX_CONSTANT_POOL = 4096;",
    "uint256 private constant MAX_ARRAYS = 4096;",
    "uint256 private constant MAX_ARRAY_ELEMENTS = 262144;",
    "uint256 private constant MAX_OBJECTS = 4096;",
    "uint256 private constant MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS",
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint256 private constant COMMIT_RESERVE = 25_000_000;",
    "uint32 private constant MAX_TRANSFER = 4096;",
):
    assert invariant in engine, invariant
assert "if (jvm == 0 || jvm > 65536 || internalSteps == 0 || internalSteps > 4096)" in engine

base_coord = (BASE / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
# Engine hash is filled from the independently compiled engine artifact below;
# all coordinator capacity edits are otherwise an exact normalized delta.
coord_without_hash = re.sub(r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',
                            r'\g<1>ENGINEHASH\g<2>', coord)
base_without_hash = re.sub(r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',
                           r'\g<1>ENGINEHASH\g<2>', base_coord)
expected_coord = base_without_hash
for old, new in (
    ("address[71] private decoders;", "address[72] private decoders;"),
    ("bytes32[71] private classRoots;", "bytes32[72] private classRoots;"),
    ("uint32[71] private classSizes;", "uint32[72] private classSizes;"),
    ("bytes[71] private rawNames;", "bytes[72] private rawNames;"),
    ("n == 0 || n > 71 || fixedRawNames.length != n ||\n            assertedIndexRoots.length != n", "n == 0 || n > 72 || fixedRawNames.length != n ||\n            assertedIndexRoots.length != n"),
    ("if (size == 0 || size > 471911) revert MR0Error(11);", "if (size == 0 || size > 513384) revert MR0Error(11);"),
    ("if (uint256(total) + size > 471911) revert MR0Error(12);", "if (uint256(total) + size > 513384) revert MR0Error(12);"),
):
    expected_coord = replace_once(expected_coord, old, new)
assert coord_without_hash == expected_coord, "coordinator source differs outside allowed raw count/bytes edits and engine hash"
assert (STAGE / "engine/build.js").read_bytes() == (BASE / "artifacts/engine/build.js").read_bytes()
assert (STAGE / "coordinator/build.js").read_bytes() == (BASE / "artifacts/coordinator/build.js").read_bytes()

# Recompute the ordered Merkle-like bootstrap commitment from each actual source leaf.
def bootstrap_root(text: str, domain: str) -> tuple[str, list[str]]:
    body = text[text.index("    function _bootstrapRoot("):]
    body = body[:body.index("\n    function ", 1)]
    assignments = {int(i): v.strip() for i, v in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(assignments) == set(range(97)), (len(assignments), sorted(assignments))
    pairs = []
    for i in range(97):
        expr = assignments[i]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", expr)
        if call:
            f = text[text.index("    function " + call.group(1) + "("):]
            f = f[:f.index("\n    function ", 1)]
            values = re.findall(r'hex"([0-9a-f]+)"', f)
            assert len(values) == 1, (i, call.group(1), len(values))
            pairs.append(("image", values[0]))
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", expr), (i, expr)
            rhs = re.search(r"bytes32 private constant " + expr + r"\s*=\s*([^;]+);", text).group(1).strip()
            values = re.findall(r'hex"([0-9a-f]+)"', rhs)
            assert len(values) == 1, (i, expr, rhs)
            pairs.append(("image" if rhs.startswith("keccak256(") else "hexhash", values[0]))
    js = r'''const fs=require('fs'),{keccak256:k}=require('js-sha3');const x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');let hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(JSON.stringify({root:k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(97),...hs.map(v=>Buffer.from(v,'hex'))])),leaves:hs}));'''
    env = {**os.environ, "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules")}
    result = subprocess.run(["node", "-e", js], cwd=ROOT, env=env,
                            input=json.dumps({"domain": domain, "pairs": pairs}),
                            text=True, capture_output=True, check=True)
    out = json.loads(result.stdout)
    return out["root"], out["leaves"]

prior_pins = json.loads((BASE / "artifacts/parent-build-pins.json").read_text())
old_root, old_leaves = bootstrap_root(base_engine, "JVMEVM:MC-RANDOM-CLASS-P24:BOOTSTRAP:1")
new_root, new_leaves = bootstrap_root(engine, "JVMEVM:MC-RANDOM-CLASS-P24:BOOTSTRAP:1")
assert old_root == new_root == prior_pins["bootstrapRoot"]
assert old_leaves == new_leaves and len(new_leaves) == 97

OUT.mkdir()
(OUT / "tmp").mkdir()
env = {
    **os.environ,
    "TMPDIR": str(OUT / "tmp"),
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GOTOOLCHAIN": "local",
}

def run(label: str, args: list[str]) -> None:
    with (OUT / f"{label}.log").open("w") as log:
        subprocess.run(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=900)

# Ensure the constructor's runtime anchor is exactly the compiled engine hash.
engine_json_path = STAGE / "engine/MCEntryInterpreter.json"
run("engine-build", ["node", str(STAGE / "engine/build.js")])
engine_art = json.loads(engine_json_path.read_text())
engine_run = bytes.fromhex(engine_art["deployedBytecode"])
assert len(engine_run) <= 393216
engine_hash = engine_art["codeHashes"]["runtimeKeccak256"]
assert f'ENGINE_CODEHASH = hex"{engine_hash}";' in coord
run("coordinator-build", ["node", str(STAGE / "coordinator/build.js")])
coord_art = json.loads((STAGE / "coordinator/MCEntryCoordinator.json").read_text())
coord_run = bytes.fromhex(coord_art["deployedBytecode"])
assert len(coord_run) <= 24576

# Keep only explicit pins/hashes in the observer. The stack/watchdog stays30s and
# all fixed transfer, checkpoint, frame and object budgets are source-normalized above.
driver_path = STAGE / "driver.go"
driver = driver_path.read_text()
assert "const ordinaryGas = uint64(1_000_000_000)" in driver
assert "return 30 * time.Second" in driver
assert "func fixtureNames() [][]byte { return fixtureNamesLimit(72) }" in driver and "len(m.Decoders) > 72" in driver
assert "len(engineRun) != 392091" in driver and "len(run) != 392091" in driver
assert f'const immutableEngineSHA256 = "{engine_art["codeHashes"]["runtimeSHA256"]}"' in driver
assert f'const immutableEngineKeccak = "0x{engine_hash}"' in driver
assert f'const immutableCoordinatorKeccak = "0x{coord_art["codeHashes"]["runtimeKeccak256"]}"' in driver
assert "n == 0 || n > 72 || fixedRawNames.length != n" in coord
assert "uint32 private constant MAX_TRANSFER = 4096;" in engine
assert "uint32(4096)" in engine[engine.index("function _configRoot"):engine.index("function _bootstrapRoot")]
assert "uint32(1048576)" in engine[engine.index("function _configRoot"):engine.index("function _bootstrapRoot")]

run("gofmt", ["gofmt", "-w", str(driver_path)])
run("go-build", ["go", "build", "-trimpath", "-o", str(OUT / "driver"), str(driver_path)])
run("go-vet", ["go", "vet", str(driver_path)])

coord_engine_hash = re.search(r'ENGINE_CODEHASH = hex"([0-9a-f]{64})"', coord).group(1)
assert coord_engine_hash == engine_hash
pins = {
    "profile": "MC-RANDOM-CLASS-P24-RAW72-Q65536-LOCAL",
    "basis": "320e595338462e5abdbb38c5086a275547b9139c",
    "domain": "MC-RANDOM-CLASS-P24",
    "address": "0x4d432d52414e444f4d2d434c4153532d50310050",
    "owner": "0x4d432d52414e444f4d2d434c4153532d50310051",
    "bootstrapCount": 97,
    "bootstrapRoot": new_root,
    "orderedBootstrapLeaves": new_leaves,
    "diagnosticClassBound": 169,
    "rawLimits": [72, 513384],
    "maxJvmSteps": 65536,
    "maxInternalSteps": 4096,
    "zeroBudgetsRefuse": True,
    "maxArrays": 4096,
    "maxObjects": 4096,
    "maxHandles": 8449,
    "maxConstantPool": 4096,
    "maxTransfer": 4096,
    "maxCheckpointBytes": 1048576,
    "commitReserve": 25000000,
    "callWatchdogMs": 30000,
    "ordinaryGas": 1000000000,
    "runtimeCap": 393216,
    "engine": {"bytes": len(engine_run), **engine_art["codeHashes"]},
    "coordinator": {"bytes": len(coord_run), **coord_art["codeHashes"]},
    "driverSHA256": sha(driver_path.read_bytes()),
    "sourceHashes": {
        "engine": sha(engine.encode()), "coordinator": sha(coord.encode()),
        "engineBuild": sha((STAGE / "engine/build.js").read_bytes()),
        "coordinatorBuild": sha((STAGE / "coordinator/build.js").read_bytes()),
    },
    "normalizedChanges": {
        "engine": ["MAX_RAW_CLASSES 71->72", "MAX_RAW_BYTES 471911->513384",
                   "_configRoot raw-count/bytes leaves only", "maxJvmSteps 4096->65536"],
        "coordinator": ["fixed arrays 71->72", "count guard 71->72",
                        "per-class and aggregate bytes 471911->513384", "engine codehash pin"],
        "observer": ["raw driver bound 71->72", "MR01 class bound 168->169"],
    },
    "sourceInvariants": {
        "bootstrapLeavesEqualAcceptedP24": old_leaves == new_leaves,
        "historicalP24LabelsRetained": True,
        "noBootstrapImagesAdded": True,
        "internalBudgetUnchanged": True,
        "noOther4096CapsChanged": True,
    },
}
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(OUT / "source-audit.json").write_text(json.dumps({
    "acceptedP24EngineSourceSHA256": sha(base_engine.encode()),
    "candidateEngineSourceSHA256": sha(engine.encode()),
    "acceptedP24CoordinatorSourceSHA256": sha(base_coord.encode()),
    "candidateCoordinatorSourceSHA256": sha(coord.encode()),
    "normalizedEngineExact": True,
    "normalizedCoordinatorExactExceptEngineCodehash": True,
    "bootstrapLeaves": 97,
    "acceptedP24BootstrapRoot": old_root,
    "candidateBootstrapRoot": new_root,
    "bootstrapLeavesByteIdentical": old_leaves == new_leaves,
    "runtimeCodeHashPinnedByCoordinator": coord_engine_hash,
}, indent=2) + "\n")
print(json.dumps({"engine": pins["engine"], "coordinator": pins["coordinator"],
                  "bootstrapRoot": new_root, "bootstrapLeaves": len(new_leaves),
                  "rawLimits": pins["rawLimits"], "maxJvmSteps": pins["maxJvmSteps"],
                  "driver": str(OUT / "driver")}, indent=2))
