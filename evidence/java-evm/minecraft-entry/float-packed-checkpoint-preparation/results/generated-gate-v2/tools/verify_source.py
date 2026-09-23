#!/usr/bin/env python3
"""Verify the float-only MR01 wire delta against the durable P5 baseline."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import os

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
baseline_path = stage.parent / "parent-56f2377a5/artifacts/engine/MCEntryInterpreter.sol"
source_path = stage / "engine/MCEntryInterpreter.sol"
baseline = baseline_path.read_text()
source = source_path.read_text()
driver_path = stage / "tools/Go.txt"
baseline_driver_path = stage.parent / "parent-56f2377a5/canonical-driver.go.txt"
coordinator_path = stage / "coordinator/MCEntryCoordinator.sol"
baseline_coordinator_path = stage.parent / "parent-56f2377a5/artifacts/coordinator/MCEntryCoordinator.sol"
assert driver_path.read_bytes() == baseline_driver_path.read_bytes(), "transport driver changed"
assert coordinator_path.read_bytes() == baseline_coordinator_path.read_bytes(), "coordinator changed"
expected_base_sha = "d26038e0aaf3c2d8754b073c18b2e2a33c0180386abe9e3e891267583d983c81"
assert hashlib.sha256(baseline.encode()).hexdigest() == expected_base_sha


def function(text, name):
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def normalise(candidate):
    # Remove only this feature's marker definitions and bounded float helpers.
    marker = (
        "    // Bit 30 is reserved for canonical raw-u32 float-cell checkpoint records.\n"
        "    // This is only a transport encoding: restored guest arrays remain dense uint64[].\n"
        "    uint256 private constant PACKED_FLOAT_ARRAY_FLAG = uint256(1) << 30;\n"
        "    uint256 private constant ARRAY_WIRE_FLAGS = SPARSE_ARRAY_FLAG | PACKED_FLOAT_ARRAY_FLAG;\n"
        "    uint256 private constant ARRAY_WIRE_COUNT_MASK = (uint256(1) << 30) - 1;\n"
    )
    assert candidate.count(marker) == 1
    candidate = candidate.replace(marker, "", 1)
    start = candidate.index("    function _checkpointArrayNonzeroCount(")
    end = candidate.index("    function _machineSize(", start)
    candidate = candidate[:start] + candidate[end:]
    for name in ("_machineSize", "_encodeMachine", "_decodeMachine"):
        candidate = candidate.replace(function(candidate, name), function(baseline, name), 1)
    return candidate

assert normalise(source) == baseline, "semantic delta escaped checkpoint layout functions/helpers/constants"
base_bootstraps = {m.group(1) for m in re.finditer(r"    function (_bootstrap\w+)\(", baseline)}
new_bootstraps = {m.group(1) for m in re.finditer(r"    function (_bootstrap\w+)\(", source)}
assert base_bootstraps == new_bootstraps
for name in base_bootstraps:
    assert function(source, name) == function(baseline, name), name
assert function(source, "_bootstrapRoot") == function(baseline, "_bootstrapRoot")

# Derive the 97-image commitment from the actual Solidity RHS values. A legacy
# P1 root pin is deliberately not treated as authority for this P5 domain.
body = function(source, "_bootstrapRoot")
assignments = {int(i): rhs.strip() for i, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
assert set(assignments) == set(range(97)), len(assignments)
pairs = []
for i in range(97):
    rhs = assignments[i]
    call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
    if call:
        image_body = function(source, call.group(1))
        chunks = re.findall(r'hex"([0-9a-f]+)"', image_body)
        assert len(chunks) == 1, (i, call.group(1), len(chunks))
        pairs.append(["image", chunks[0]])
        continue
    assert re.fullmatch(r"DBOOT_[A-Z_]+", rhs), (i, rhs)
    expr = re.search(r"bytes32 private constant " + rhs + r"\s*=\s*([^;]+);", source).group(1).strip()
    chunks = re.findall(r'hex"([0-9a-f]+)"', expr)
    assert len(chunks) == 1, (i, rhs, expr)
    pairs.append(["image" if expr.startswith("keccak256(hex\"") else "hexhash", chunks[0]])
node = r'''const fs=require('fs'),{keccak256}=require('js-sha3');const a=JSON.parse(fs.readFileSync(0,'utf8'));const k=s=>keccak256(Buffer.from(s,'hex'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');const hs=a.pairs.map(([t,v])=>t==='image'?k(v):v);const x=Buffer.concat([Buffer.from(keccak256(a.domain),'hex'),w(64),w(hs.length),...hs.map(v=>Buffer.from(v,'hex'))]);console.log(keccak256(x));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
actual_root = subprocess.run(["node", "-e", node], cwd=root, env=env,
    input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P5:BOOTSTRAP:1", "pairs": pairs}),
    text=True, capture_output=True, check=True).stdout.strip()
assert actual_root == "1651f62e6a1d02c7fe9935f2944f04dbc12d1423e0a69ed44fa9a1e2a5334f3b"

for invariant in (
    "uint256 private constant SPARSE_ARRAY_FLAG = uint256(1) << 31;",
    "uint256 private constant PACKED_FLOAT_ARRAY_FLAG = uint256(1) << 30;",
    "MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;",
    "return 19;", "return 12;", "PRIMITIVE_FLOAT", "4 * length < 4 + 12 * nonzero",
    "wireCount & PACKED_FLOAT_ARRAY_FLAG", "sparseArray && packedFloatArray",
    "meta == PRIMITIVE_FLOAT && cell > type(uint32).max",
    "keccak256(canonical) != keccak256(env.machineBytes)",
):
    assert invariant in source, invariant
report = {
    "result": "PASS", "baselineCommit": "56f2377a5",
    "baselineSourceSHA256": expected_base_sha,
    "candidateSourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "onlySemanticFunctionsChanged": ["_machineSize", "_encodeMachine", "_decodeMachine"],
    "addedLayoutHelpers": ["_checkpointArrayNonzeroCount", "_usePackedFloatArray"],
    "addedLayoutConstants": ["PACKED_FLOAT_ARRAY_FLAG=0x40000000", "ARRAY_WIRE_FLAGS", "ARRAY_WIRE_COUNT_MASK"],
    "bootstrapCount": 97, "actualP5BootstrapRoot": actual_root,
    "bootstrapImagesAndRootFunctionByteIdentical": True,
    "transportDriverSHA256": hashlib.sha256(driver_path.read_bytes()).hexdigest(),
    "transportDriverByteIdenticalToBaseline": True,
    "coordinatorSHA256": hashlib.sha256(coordinator_path.read_bytes()).hexdigest(),
    "coordinatorByteIdenticalToBaseline": True,
    "rawLimits": [71, 471911], "globalNativeBindings": 19, "stringLocalBinding": 12,
    "runtimeCapBytes": 393216,
}
(stage / "results/source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
