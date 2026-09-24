#!/usr/bin/env python3
"""Audit the exact packed-u32 source delta and all 97 same-domain bootstrap leaves."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
if len(sys.argv) != 2:
    raise SystemExit("usage: verify_source.py AUDIT-ID")
audit_id = sys.argv[1]
assert re.fullmatch(r"[0-9]{2}-[a-z0-9-]+", audit_id)
base_path = root / "evidence/java-evm/minecraft-entry/parent-485ccd8d4/artifacts/engine/MCEntryInterpreter.sol"
candidate_path = stage / "engine/MCEntryInterpreter.sol"
base = base_path.read_text()
candidate = candidate_path.read_text()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def function_bodies(source):
    starts = list(re.finditer(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(", source))
    out = {}
    for match in starts:
        open_brace = source.find("{", match.end())
        assert open_brace >= 0
        depth = 0
        quote = None
        line_comment = False
        block_comment = False
        escape = False
        i = open_brace
        while i < len(source):
            ch = source[i]
            nxt = source[i + 1] if i + 1 < len(source) else ""
            if line_comment:
                if ch == "\n": line_comment = False
            elif block_comment:
                if ch == "*" and nxt == "/":
                    block_comment = False
                    i += 1
            elif quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    quote = None
            elif ch == "/" and nxt == "/":
                line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                block_comment = True
                i += 1
            elif ch in ('"', "'"):
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    name = match.group(1)
                    out.setdefault(name, []).append(source[match.start():i + 1])
                    break
            i += 1
        assert depth == 0, match.group(1)
    return out

base_functions = function_bodies(base)
candidate_functions = function_bodies(candidate)
assert base_functions.keys() == candidate_functions.keys()
changed = sorted(name for name in base_functions
                 if base_functions[name] != candidate_functions[name])
assert changed == ["_decodeMachine", "_encodeMachine"], changed
for name in base_functions:
    if name not in ("_encodeMachine", "_decodeMachine"):
        assert base_functions[name] == candidate_functions[name], name
normalized = candidate
for name in changed:
    assert len(base_functions[name]) == len(candidate_functions[name]) == 1
    normalized = normalized.replace(candidate_functions[name][0], base_functions[name][0], 1)
assert normalized == base, "source changes outside the two allowed function bodies"

# Encoding stays on the prior exact-size/cap/fallback path. Packed choice is
# preceded by the one existing validator and does not add a validation pass.
encode = candidate_functions["_encodeMachine"][0]
assert "uint256 sparseCount = _checkpointArrayNonzeroCount(s, h);" in encode
assert re.search(r"uint256 sparseCount = _checkpointArrayNonzeroCount\(s, h\);\s*if \(_usePackedFloatArray", encode)
assert "uint256 grouped = count & ~uint256(7);" in encode
assert 'mstore(add(add(out, 32), at), word)' in encode
assert "for (uint256 j = grouped; j < count; ++j)" in encode
assert "at = _put(out, at, cells[j], 4);" in encode
assert "_usePackedFloatArray(meta, a.heap.ranks[h], count, sparseCount)" in encode

# Decode retains exact bounds validation before any grouped load; only full
# 32-byte groups use mload and short tails use bounds-checked _get.
decode = candidate_functions["_decodeMachine"][0]
packed_pos = decode.index("if (packedFloatArray)")
require_pos = decode.index("_requireCellBytes(data, at, count, 4, base);", packed_pos)
load_pos = decode.index("word := mload(add(add(data, 32), at))", packed_pos)
assert require_pos < load_pos
assert "uint256 grouped = count & ~uint256(7);" in decode[packed_pos:]
assert "(uint256 cell, uint256 qn) = _get(data, at, 4, base); at = qn;" in decode[packed_pos:]
assert "if (cell != 0) ++nonzero;" in decode[packed_pos:]
assert "if (!_usePackedFloatArray(meta, rank, count, nonzero))" in decode[packed_pos:]
assert "a.heap.arrayHeap[h] = new uint64[](count);" in decode[:packed_pos]


def root_pairs(source):
    pos = source.index("    function _bootstrapRoot(")
    body = source[pos:]
    body = body[:body.index("\n    function ", 1)]
    assignments = {
        int(index): rhs.strip()
        for index, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)
    }
    assert set(assignments) == set(range(97)), (len(assignments), sorted(assignments)[:5])
    pairs = []
    for index in range(97):
        rhs = assignments[index]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
        if call:
            start = source.index("    function " + call.group(1) + "(")
            rest = source[start:]
            fn = rest[:rest.index("\n    function ", 1)]
            bytecodes = re.findall(r'hex"([0-9a-f]+)"', fn)
            assert len(bytecodes) == 1, (index, call.group(1), len(bytecodes))
            pairs.append(["image", bytecodes[0]])
            continue
        assert re.fullmatch(r"DBOOT_[A-Z_]+", rhs), (index, rhs)
        constant = re.search(
            r"bytes32 private constant " + re.escape(rhs) + r"\s*=\s*([^;]+);", source
        )
        assert constant, (index, rhs)
        expr = constant.group(1).strip()
        bytecodes = re.findall(r'hex"([0-9a-f]+)"', expr)
        assert len(bytecodes) == 1, (index, rhs, len(bytecodes))
        pairs.append(["image" if expr.startswith("keccak256(") else "hexhash", bytecodes[0]])
    return pairs

base_pairs = root_pairs(base)
candidate_pairs = root_pairs(candidate)
assert base_pairs == candidate_pairs, "one or more ordered bootstrap leaves changed"
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const a=JSON.parse(fs.readFileSync(0,"utf8"));
const k=s=>keccak256(Buffer.from(s,"hex"));
const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const leaves=a.pairs.map(([t,v])=>t==="image"?k(v):v);
const d=Buffer.from(keccak256(a.domain),"hex");
const encoded=Buffer.concat([d,w(64),w(leaves.length),...leaves.map(x=>Buffer.from(x,"hex"))]);
console.log(JSON.stringify({root:keccak256(encoded),leaves}));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
proc = subprocess.run(["node", "-e", node], input=json.dumps({
    "pairs": candidate_pairs,
    "domain": "JVMEVM:MC-RANDOM-CLASS-P17:BOOTSTRAP:1",
}), text=True, cwd=root, env=env, capture_output=True, check=True)
root_data = json.loads(proc.stdout)
expected_root = "aae001d9449928180fe6daf66cc3a7bffa4686a7823f69bb994cd882fa89ec0d"
assert root_data["root"] == expected_root
assert len(root_data["leaves"]) == 97

result = {
    "result": "PASS",
    "baseSource": str(base_path.relative_to(root)),
    "candidateSource": str(candidate_path.relative_to(root)),
    "baseSourceSHA256": sha(base),
    "candidateSourceSHA256": sha(candidate),
    "changedFunctions": changed,
    "orderedBootstrapLeaves": 97,
    "orderedBootstrapLeafKeccak256": root_data["leaves"],
    "bootstrapRootDomain": "JVMEVM:MC-RANDOM-CLASS-P17:BOOTSTRAP:1",
    "p17Root": expected_root,
    "candidateRoot": root_data["root"],
    "unchangedBootstrapLeafDefinitions": True,
    "packedEncoder": "8 big-endian u32 cells per in-bounds 32-byte store; exact checked _put tail",
    "packedDecoder": "checked 32-byte grouped loads into eager dense uint64[]; checked _get tail",
}
out = stage / "results" / ("source-audit-" + audit_id + ".json")
out.parent.mkdir(parents=True, exist_ok=True)
assert not out.exists(), "source audit records are append-only"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in (
    "result", "baseSourceSHA256", "candidateSourceSHA256", "changedFunctions",
    "orderedBootstrapLeaves", "candidateRoot", "packedEncoder", "packedDecoder"
)}, indent=2))
