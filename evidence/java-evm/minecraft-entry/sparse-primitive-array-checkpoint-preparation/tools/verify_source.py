#!/usr/bin/env python3
"""Verify sparse checkpoint changes are isolated to the wire layout."""
from pathlib import Path
import hashlib
import json
import re

stage = Path(__file__).resolve().parent.parent
root = Path(__file__).resolve().parents[4]
baseline_dir = stage.parent / "parent-511c20c4b"
baseline_path = baseline_dir / "artifacts/engine/MCEntryInterpreter.sol"
baseline_pins = json.loads((stage / "baseline-pins.json").read_text())
source_path = stage / "engine/MCEntryInterpreter.sol"
source = source_path.read_text()
baseline = baseline_path.read_text()
assert hashlib.sha256(baseline.encode()).hexdigest() == "ad6224f15781aee0ae009334a36ff66091efbac048c04f7f23df8307a851cfc5"


def function(text, name):
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def replace_function(text, original, name):
    old, new = function(text, name), function(original, name)
    assert old and new
    return text.replace(old, new, 1)

# Replacing only the sparse marker/constants/helpers and the three named
# checkpoint routines must restore the byte-exact authenticated parent source.
normalized = source
normalized = normalized.replace(
    "    // The high bit of the existing uint32 array-count word discriminates\n"
    "    // canonical sparse primitive-array checkpoint records. Guest arrays stay dense.\n"
    "    uint256 private constant SPARSE_ARRAY_FLAG = uint256(1) << 31;\n"
    "    uint256 private constant SPARSE_ARRAY_MIN_LENGTH = 1024;\n", "")
helper_start = normalized.index("    function _sparsePrimitiveArrayCount(")
helper_end = normalized.index("    function _machineSize(", helper_start)
normalized = normalized[:helper_start] + normalized[helper_end:]
for name in ("_machineSize", "_encodeMachine", "_decodeMachine"):
    normalized = replace_function(normalized, baseline, name)
assert normalized == baseline, "unexpected non-checkpoint semantic edit"

# All bootstrap image bodies and the ordered commitment implementation are
# preserved exactly, not merely by a changed-root-compatible count.
for match in re.finditer(r"function (_bootstrap\w+)\(", baseline):
    name = match.group(1)
    assert function(source, name) == function(baseline, name), name
assert function(source, "_bootstrapRoot") == function(baseline, "_bootstrapRoot")
for invariant in (
    "MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;",
    "MAX_CHECKPOINT_BYTES = 1048576;", "new bytes32[](97)",
    "return 18;", "return 12;", "binding != 18",
    "SPARSE_ARRAY_FLAG | count", "new uint64[](count)",
    "index >= count || (j != 0 && index <= priorIndex) || cell == 0",
    "keccak256(canonical) != keccak256(env.machineBytes)",
):
    assert invariant in source, invariant
assert "uint256 private constant SPARSE_ARRAY_MIN_LENGTH = 1024;" in source
assert "return (4 + 12 * nonzero) * 4 <= (8 * length) * 3;" in source

report = {
    "result": "PASS",
    "baselineCommit": "511c20c4b",
    "baselineSourceSHA256": hashlib.sha256(baseline.encode()).hexdigest(),
    "candidateSourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "onlySemanticFunctionsChanged": ["_machineSize", "_encodeMachine", "_decodeMachine"],
    "sparseHelpers": ["_sparsePrimitiveArrayCount", "_useSparsePrimitiveArray"],
    "bootstrapCount": 97,
    "bootstrapRoot": baseline_pins["bootstrapRoot"],
    "bootstrapSourceAndRootByteIdentical": True,
    "rawLimits": baseline_pins["rawLimits"],
    "globalNativeBindings": baseline_pins["globalNativeBindings"],
    "stringLocalBinding": baseline_pins["stringLocalBinding"],
    "runtimeCapBytes": baseline_pins["runtimeCap"],
}
(stage / "results/source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
