#!/usr/bin/env python3
"""Verify the sole bounded Math.sin engine delta and source-derived 97-leaf root."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
previous = stage.parent / "math-sin-signed-zero-preparation"
baseline_path = previous / "engine/MCEntryInterpreter.sol"
source_path = stage / "engine/MCEntryInterpreter.sol"
source = source_path.read_text()
baseline = baseline_path.read_text()
baseline_pins = json.loads((stage / "baseline-pins.json").read_text())
assert hashlib.sha256(baseline.encode()).hexdigest() == baseline_pins["baselineEngineSourceSHA256"]


def block(text, start):
    at = text.index(start)
    end = text.find("\n    function ", at + 1)
    return text[at:end if end >= 0 else len(text)]


def image(text, name):
    body = block(text, "    function " + name + "(")
    values = re.findall(r'hex"([0-9a-f]+)"', body)
    assert len(values) == 1, (name, len(values))
    return bytes.fromhex(values[0])


def pascal_constant(name):
    overrides = {"ENUMSET": "EnumSet", "ITERABLE": "Iterable", "MATH": "Math",
                 "RANDOM": "Random", "THREAD": "Thread", "THREAD_LOCAL": "ThreadLocal",
                 "STACK_TRACE_ELEMENT": "StackTraceElement", "PRINT_STREAM": "PrintStream",
                 "SECURITY_MANAGER": "SecurityManager"}
    tail = name.removeprefix("DBOOT_")
    return "_bootstrap" + overrides.get(tail, "".join(part.title() for part in tail.split("_")))

# Recompile the unchanged Java-8 Math leaf: this stage changes no bootstrap image.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="java-diff-mc-math-sin-bounded-source-", dir=root / "build") as temp:
    generated_dir = Path(temp)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", generated_dir,
                    stage / "bootstrap/java/lang/Math.java"], cwd=root, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    generated = (generated_dir / "java/lang/Math.class").read_bytes()
math_hex = stage / "bootstrap/java/lang/Math.class.hex"
math_sha_path = stage / "bootstrap/java/lang/Math.sha256"
assert math_hex.read_text().strip() == generated.hex()
math_sha = hashlib.sha256(generated).hexdigest()
assert math_sha_path.read_text().strip() == math_sha
assert generated == image(baseline, "_bootstrapMath") == image(source, "_bootstrapMath")

# Every embedded bootstrap image and the Solidity root expression are unchanged.
base_functions = set(re.findall(r"    function (_bootstrap\w+)\(", baseline))
new_functions = set(re.findall(r"    function (_bootstrap\w+)\(", source))
assert base_functions == new_functions
assert block(source, "    function _bootstrapRoot()") == block(baseline, "    function _bootstrapRoot()")
assert all(image(source, fn) == image(baseline, fn) for fn in base_functions if fn != "_bootstrapRoot")

# Derive every ordered leaf from the Solidity root expression and exact embedded bytes.
root_block = block(source, "    function _bootstrapRoot()")
assignments = {int(i): rhs.strip() for i, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", root_block)}
assert set(assignments) == set(range(97))
leaves = []
for index in range(97):
    rhs = assignments[index]
    call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
    constant = re.fullmatch(r"(DBOOT_[A-Z_]+)", rhs)
    name = call.group(1) if call else pascal_constant(constant.group(1))
    leaf = image(source, name)
    if constant:
        declaration = re.search(r"bytes32 private constant " + constant.group(1) + r"\s*=\s*([^;]+);", source)
        assert declaration
        value = declaration.group(1).strip()
        if value.startswith('keccak256(hex"'):
            assert bytes.fromhex(value[len('keccak256(hex"'):-2]) == leaf
    leaves.append(leaf)

node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const k=b=>keccak256(Buffer.from(b,"hex"));const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const d=keccak256(x.domain);const hs=x.images.map(k);const enc=Buffer.concat([Buffer.from(d,"hex"),word(64),word(hs.length),...hs.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(JSON.stringify({domain:d,hashes:hs,root:keccak256(enc)}));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
commitment = json.loads(subprocess.run(["node", "-e", node], input=json.dumps({
    "domain": "JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1", "images": [x.hex() for x in leaves]
}), text=True, cwd=root, env=env, capture_output=True, check=True).stdout)
assert commitment["root"] == "e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac"

# Normalize exactly two allowed source deltas: binding19's signed-zero dispatch
# becomes bounded Q120 integer sine, and its four private arithmetic helpers.
normalized = source
new_dispatch = '''                    if (nativeBinding == 19) {
                        // Binding19 is a deterministic integer-only, explicitly
                        // range-bounded binary64 sine. It consumes only the exact
                        // guest double bits and never calls host math or a table.
                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);
                        uint64 raw = uint64(_payload(f.stack[base]));
                        f.stack[base] = _packDouble(_mathSinBits(raw, opPC));
                        f.sp = base + 1;
                        continue;
                    }
'''
old_dispatch = '''                    if (nativeBinding == 19) {
                        // This is not a partial trigonometry implementation. Only
                        // the two IEEE binary64 zero encodings are measured and
                        // supported; preserve their original sign bit exactly.
                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);
                        uint64 raw = uint64(_payload(f.stack[base]));
                        if ((raw & 0x7fffffffffffffff) != 0) {
                            revert MathSinProfileError(1, opPC);
                        }
                        f.stack[base] = _packDouble(raw);
                        f.sp = base + 1;
                        continue;
                    }
'''
assert normalized.count(new_dispatch) == 1
normalized = normalized.replace(new_dispatch, old_dispatch, 1)
helper_start = "    /// @dev Pure EVM uint/int implementation of bounded binary64 sin.\n"
helper_end = "    /// @dev Fixed restoring integer sqrt for a radicand below 2^106.\n"
a, b = normalized.index(helper_start), normalized.index(helper_end, normalized.index(helper_start))
normalized = normalized[:a] + normalized[b:]
assert normalized == baseline, "unreviewed source changes beyond binding19 bounded sine helpers"

kernel = source[source.index(helper_start):source.index(helper_end, source.index(helper_start))]
assert "Math.sin(" not in kernel and "Math.sqrt(" not in kernel and "blockhash(" not in kernel
assert "0x401921fb54442d18" in kernel and "0x3e30000000000000" in kernel
assert "for (uint256 n = 1; n <= 30; ++n)" in kernel
assert "4175892906503776358826876457663557747" in kernel
assert "_roundSignedEven(x * x" in kernel and "_q120ToDoubleBits(total)" in kernel
assert "MathSinProfileError(1, pc)" in kernel
for proof_phrase in ("q=floor(|n|/d)", "2r>d", "E1<1, E2..E4<1.2",
                     "summed recurrence error is <21 units", "phase + recurrence + tail error is <23 Q units",
                     "within one ulp", "including subnormals"):
    assert proof_phrase in kernel, proof_phrase
round_div = block(source, "    function _roundSignedEven(")
assert "twice > denominator" in round_div
assert "twice == denominator && (quotient & 1) != 0" in round_div
round_binary64 = block(source, "    function _roundRightEven256(")
assert "remainder > half" in round_binary64
assert "remainder == half && (quotient & 1) != 0" in round_binary64
assert "return 19;" in block(source, "    function _nativeBinding(")

report = {
    "result": "PASS", "basis": "math-sin-signed-zero-preparation",
    "baselineEngineSourceSHA256": hashlib.sha256(baseline.encode()).hexdigest(),
    "candidateEngineSourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "onlySemanticDelta": ["global native binding19 exact bounded Q120 integer Math.sin(D)D"],
    "bootstrapCount": 97, "changedBootstrapIndices": [],
    "mathImageBytes": len(generated), "mathImageSHA256": math_sha,
    "mathImageKeccak256": commitment["hashes"][89],
    "bootstrapImagesByteIdentical": True, "orderedRoot": commitment["root"],
    "previousSourceDerivedRoot": commitment["root"],
    "previousDeclaredP1PinRoot": "7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887",
    "orderedLeafKeccak256": commitment["hashes"],
    "globalNativeBindings": 19, "stringLocalBinding": 12,
    "rawLimits": [71, 471911], "diagnosticClassBound": 168,
    "kernel": {"qBits": 120, "piQ": "4175892906503776358826876457663557747",
               "iterations": 30, "inputMagnitudeMaxRaw": "401921fb54442d18",
               "smallIdentityMaxRaw": "3e30000000000000", "externalMath": False,
               "lookupTable": False, "sourceRangeAndIntermediateBoundsDocumented": True},
}
(stage / "root-commitment.json").write_text(json.dumps({
    "basis": report["basis"], "bootstrapCount": 97,
    "priorSourceDerivedRoot": commitment["root"],
    "priorHistoricalP1PinRoot": report["previousDeclaredP1PinRoot"],
    "historicalP1PinMatchesSourceDerivedRoot": False,
    "changedIndices": [], "orderedLeafKeccak256": commitment["hashes"],
    "bootstrapRoot": commitment["root"],
}, indent=2) + "\n")
(stage / "results/source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
