#!/usr/bin/env python3
"""Verify the two-function MR01 reservation/shrink delta against accepted P16."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
baseline_path = root / "evidence/java-evm/minecraft-entry/parent-50541377b/artifacts/engine/MCEntryInterpreter.sol"
candidate_path = stage / "engine/MCEntryInterpreter.sol"
baseline = baseline_path.read_text()
candidate = candidate_path.read_text()
P16_ROOT = "8c5bc495513b12e7ee40f71f447c5f8f894d49ec9cf318d2744143f1d20ff310"
P16_SOURCE_SHA = "e53932817b1537f0e06911e4114a2995d1bcf12c946c6529accaa3d75bb1d849"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(text, name):
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]

assert sha(baseline.encode()) == P16_SOURCE_SHA
assert sha(candidate.encode()) != sha(baseline.encode())
normalized = candidate
for name in ("_machineSize", "_encodeMachine"):
    body = function(normalized, name)
    normalized = normalized.replace(body, function(baseline, name), 1)
assert normalized == baseline, "change escaped _machineSize/_encodeMachine"

# The exact bootstrap table and every function that materializes one of its
# leaves remain byte-identical. Independently reconstruct the ordered root.
def ordered_leaves(source):
    body = function(source, "_bootstrapRoot")
    assignments = {
        int(index): rhs.strip()
        for index, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)
    }
    assert set(assignments) == set(range(97)), len(assignments)
    leaves = []
    for index in range(97):
        rhs = assignments[index]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
        if call:
            chunks = re.findall(r'hex"([0-9a-f]+)"', function(source, call.group(1)))
            assert len(chunks) == 1, (index, call.group(1), len(chunks))
            leaves.append(["image", chunks[0]])
            continue
        assert re.fullmatch(r"DBOOT_[A-Z_]+", rhs), (index, rhs)
        expr = re.search(
            r"bytes32 private constant " + rhs + r"\s*=\s*([^;]+);", source
        ).group(1).strip()
        chunks = re.findall(r'hex"([0-9a-f]+)"', expr)
        assert len(chunks) == 1, (index, rhs, expr)
        leaves.append(["image" if expr.startswith("keccak256(hex\"") else "hash", chunks[0]])
    return assignments, leaves

base_assignments, base_leaves = ordered_leaves(baseline)
new_assignments, new_leaves = ordered_leaves(candidate)
assert new_assignments == base_assignments
assert new_leaves == base_leaves
assert function(candidate, "_bootstrapRoot") == function(baseline, "_bootstrapRoot")
for name in re.findall(r"    function (_bootstrap\w+)\(", baseline):
    assert function(candidate, name) == function(baseline, name), name

node = r'''const fs=require('fs'),{keccak256}=require('js-sha3');
const a=JSON.parse(fs.readFileSync(0,'utf8'));
const k=s=>keccak256(Buffer.from(s,'hex'));
const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');
const hs=a.leaves.map(([kind,value])=>kind==='image'?k(value):value);
const data=Buffer.concat([Buffer.from(keccak256(a.domain),'hex'),w(64),w(hs.length),
  ...hs.map(value=>Buffer.from(value,'hex'))]);
console.log(JSON.stringify({root:keccak256(data),leaves:hs}));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
computed = json.loads(subprocess.run(
    ["node", "-e", node], cwd=root, env=env,
    input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P16:BOOTSTRAP:1", "leaves": new_leaves}),
    text=True, capture_output=True, check=True,
).stdout)
assert computed["root"] == P16_ROOT, computed["root"]

machine_size = function(candidate, "_machineSize")
encode_machine = function(candidate, "_encodeMachine")
assert "meta == PRIMITIVE_FLOAT && s.arena.heap.ranks[h] == 1" in machine_size
assert "length >= SPARSE_ARRAY_MIN_LENGTH && !exactFloatArraySizes" in machine_size
assert machine_size.count("_checkpointArrayNonzeroCount(s, h)") == 1
assert "uint256 sparseCount = _checkpointArrayNonzeroCount(s, h);" in machine_size
assert "if (_usePackedFloatArray(meta, s.arena.heap.ranks[h], length, sparseCount))" in machine_size
assert "else if (_useSparsePrimitiveArray(meta, s.arena.heap.ranks[h], length, sparseCount))" in machine_size
assert "z += 47 + 12 * sparseCount;" in machine_size
assert "z += 43 + 8 * length;" in machine_size
assert "if (cell > type(uint32).max) revert LC0StateError(6, handle);" in function(candidate, "_checkpointArrayNonzeroCount")
assert encode_machine.count("_checkpointArrayNonzeroCount(s, h)") == 1
assert "_machineSize(p, s, ec, en, args, false)" in encode_machine
assert "_machineSize(p, s, ec, en, args, true)" in encode_machine
upper_check = encode_machine.index("if (size + CHECKPOINT_HEADER_BYTES > MAX_CHECKPOINT_BYTES)")
exact_call = encode_machine.index("size = _machineSize(p, s, ec, en, args, true);", upper_check)
exact_check = encode_machine.index("if (size + CHECKPOINT_HEADER_BYTES > MAX_CHECKPOINT_BYTES)", exact_call)
allocation = encode_machine.index("out = new bytes(size);", exact_check)
assert upper_check < exact_call < exact_check < allocation
assert "assert(at <= out.length);" in encode_machine
assert 'assembly ("memory-safe") { mstore(out, at) }' in encode_machine
assert "at + CHECKPOINT_HEADER_BYTES > MAX_CHECKPOINT_BYTES" in encode_machine

# Bounded algebra over every eligible float-array length/count proves that the
# upper reservation is exact for packed P16 records and dominates sparse P16
# records; sparse is necessarily selected whenever packed is not. Then exercise
# both sides of the checkpoint cap using the same fixed remainder. These are
# source/algebra controls, not claims that this synthetic near-cap state is
# reachable within the ordinary EVM gas budget.
CHECKPOINT_HEADER_BYTES = 280
MAX_CHECKPOINT_BYTES = 1_048_576
algebra_lengths = [1024, 1025, 2048, 32768, 65535, 65536]
for length in algebra_lengths:
    upper_record = 43 + 4 * length
    for nonzero in range(length + 1):
        packed = 4 * length < 4 + 12 * nonzero
        sparse_eligible = (4 + 12 * nonzero) * 4 <= (8 * length) * 3
        if packed:
            exact_record = 43 + 4 * length
            assert exact_record == upper_record
        else:
            assert sparse_eligible, (length, nonzero)
            exact_record = 47 + 12 * nonzero
            assert exact_record <= upper_record, (length, nonzero)

length = 65536
upper_record = 43 + 4 * length
exact_zero_record = 47
fixed_remainder = MAX_CHECKPOINT_BYTES - CHECKPOINT_HEADER_BYTES - exact_zero_record
upper_envelope = CHECKPOINT_HEADER_BYTES + fixed_remainder + upper_record
exact_zero_envelope = CHECKPOINT_HEADER_BYTES + fixed_remainder + exact_zero_record
exact_one_envelope = CHECKPOINT_HEADER_BYTES + fixed_remainder + (47 + 12)
assert upper_envelope > MAX_CHECKPOINT_BYTES
assert exact_zero_envelope == MAX_CHECKPOINT_BYTES
assert exact_one_envelope == MAX_CHECKPOINT_BYTES + 12
assert not (4 * length < 4 + 12 * 0)
assert not (4 * length < 4 + 12 * 1)
assert (4 + 12 * 0) * 4 <= (8 * length) * 3
assert (4 + 12 * 1) * 4 <= (8 * length) * 3
cap_fallback_algebra = {
    "status": "PASS",
    "eligibleLengthsChecked": algebra_lengths,
    "allNonzeroCountsChecked": sum(length + 1 for length in algebra_lengths),
    "selection": "P16 strict packed iff 4*length < 4+12*nonzero; otherwise canonical sparse",
    "upperRecordBytesAtLength65536": upper_record,
    "sameFixedRemainderBytes": fixed_remainder,
    "zeroNonzeroCase": {
        "exactSparseRecordBytes": exact_zero_record,
        "exactEnvelopeBytes": exact_zero_envelope,
        "upperEnvelopeBytes": upper_envelope,
        "expected": "exact fallback accepts at cap although upper reservation exceeds cap",
    },
    "oneNonzeroCase": {
        "exactSparseRecordBytes": 59,
        "exactEnvelopeBytes": exact_one_envelope,
        "upperEnvelopeBytes": upper_envelope,
        "expected": "exact fallback preserves typed cap refusal when exact P16 bytes exceed cap",
    },
    "ordinaryPackedPath": "upper reservation equals exact packed record; false-mode does not count float cells",
    "executionScope": "bounded generated/source/algebra control only; synthetic near-cap states are not EVM execution claims",
}
assert "4 * length < 4 + 12 * nonzero" in function(baseline, "_usePackedFloatArray")
assert "uint256 private constant SPARSE_ARRAY_MIN_LENGTH = 1024;" in candidate
assert "uint256 private constant PACKED_FLOAT_ARRAY_FLAG = uint256(1) << 30;" in candidate
assert "uint256 private constant MAX_RAW_CLASSES = 71;" in candidate
assert "uint256 private constant MAX_RAW_BYTES = 471911;" in candidate
assert "return 20;" in candidate and "return 21;" in candidate
assert "return 12;" in candidate

report = {
    "result": "PASS",
    "baseline": "accepted P16 source, parent-50541377b",
    "baselineSourceSHA256": sha(baseline.encode()),
    "candidateSourceSHA256": sha(candidate.encode()),
    "onlyChangedFunctions": ["_machineSize", "_encodeMachine"],
    "bootstrapCount": 97,
    "bootstrapRootDomain": "JVMEVM:MC-RANDOM-CLASS-P16:BOOTSTRAP:1",
    "actualP16BootstrapRoot": computed["root"],
    "orderedBootstrapLeaves": computed["leaves"],
    "bootstrapLeavesAndMaterializersByteIdentical": True,
    "p16GlobalNativeBindingMax": 21,
    "stringLocalBinding": 12,
    "rawLimits": [71, 471911],
    "packedFloat": {
        "eligible": "rank1 primitive-float length>=1024",
        "reservationBytes": "43+4*length",
        "encodingNonzeroScans": 1,
        "canonicalPackedRule": "4*length < 4+12*nonzero",
        "safeSparseBound": "not packed implies 47+12*nonzero <= 43+4*length",
        "eagerDecodeUnchanged": True,
        "shrinkAfterBoundsCheck": True,
    },
    "capFallbackAlgebra": cap_fallback_algebra,
    "transportAndAuthenticationSourceByteIdentical": True,
}
(stage / "source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "orderedBootstrapLeaves"}, indent=2))
