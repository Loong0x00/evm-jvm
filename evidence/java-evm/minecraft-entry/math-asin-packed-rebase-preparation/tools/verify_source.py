#!/usr/bin/env python3
"""Strict P6-to-P9 source normalization and actual 97-leaf root verification."""
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
p6_path = root / "evidence/java-evm/minecraft-entry/parent-670d5a8ce/artifacts/engine/MCEntryInterpreter.sol"
p8_math_path = root / "evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/engine/MCEntryInterpreter.sol"
source_path = stage / "engine/MCEntryInterpreter.sol"
p6 = p6_path.read_text()
p8_math = p8_math_path.read_text()
source = source_path.read_text()
P6_SOURCE_SHA256 = "3b8f1662ae5d9a20849fad5ba9854bd6b0d6d51ce971b89f73bcaf0b094e8fa1"
MATH_SHA256 = "678f8cef035281f8db9c55ca436048c4494ace649b82c54eb859f4ecb4ea99ad"
MATH_KECCAK256 = "109b02106c7d644052ff74938768421a9a78caf8d9bfd2378b943cf567c2d192"
OLD_MATH_KECCAK256 = "e354be66a6f5f6eecabb17b461000b63b90bea635f692a0cf0c36b6b5a688748"
P9_DOMAIN = "JVMEVM:MC-RANDOM-CLASS-P9:BOOTSTRAP:1"
P6_DOMAIN = "JVMEVM:MC-RANDOM-CLASS-P6:BOOTSTRAP:1"
CONSTANT_IMAGES = {
    "DBOOT_THREAD": "_bootstrapThread",
    "DBOOT_ENUMSET": "_bootstrapEnumSet",
    "DBOOT_PRINT_STREAM": "_bootstrapPrintStream",
    "DBOOT_ITERABLE": "_bootstrapIterable",
    "DBOOT_THREAD_LOCAL": "_bootstrapThreadLocal",
    "DBOOT_MATH": "_bootstrapMath",
    "DBOOT_STACK_TRACE_ELEMENT": "_bootstrapStackTraceElement",
    "DBOOT_SECURITY_MANAGER": "_bootstrapSecurityManager",
    "DBOOT_RANDOM": "_bootstrapRandom",
}


def function_block(text: str, name: str) -> str:
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def image(text: str, name: str) -> bytes:
    values = re.findall(r'hex"([0-9a-f]+)"', function_block(text, name))
    assert len(values) == 1, (name, len(values))
    return bytes.fromhex(values[0])


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, (label, count)
    return text.replace(old, new, 1)


def node_json(script: str, payload: dict) -> dict:
    env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
    result = subprocess.run(["node", "-e", script], input=json.dumps(payload), text=True,
                          cwd=root, env=env, capture_output=True, check=True)
    return json.loads(result.stdout)


assert hashlib.sha256(p6.encode()).hexdigest() == P6_SOURCE_SHA256
assert source.count("JVMEVM:MC-RANDOM-CLASS-P9:") == 9
assert "JVMEVM:MC-RANDOM-CLASS-P6:" not in source

# Rebase isolation changes only the versioned domain/address literals in the
# coordinator and raw transport template; all authorization and read/commit
# logic is byte-identical to accepted P6 before build-time codehash substitution.
p6_coord_path = root / "evidence/java-evm/minecraft-entry/parent-670d5a8ce/artifacts/coordinator/MCEntryCoordinator.sol"
p6_driver_path = root / "evidence/java-evm/minecraft-entry/parent-670d5a8ce/canonical-driver.go.txt"
coord = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
p6_coord = p6_coord_path.read_text()
coord_normalized = coord.replace("MC-RANDOM-CLASS-P9", "MC-RANDOM-CLASS-P6").replace(
    'hex"4d432d52414e444f4d2d434c4153532d5039000e"',
    'hex"4d432d52414e444f4d2d434c4153532d5031000e"',
)
assert coord_normalized == p6_coord

driver = (stage / "tools/Go.txt").read_text()
p6_driver = p6_driver_path.read_text()
driver_normalized = driver.replace("MC-RANDOM-CLASS-P9", "MC-RANDOM-CLASS-P6").replace(
    "0x4d432d52414e444f4d2d434c4153532d5039000f",
    "0x4d432d52414e444f4d2d434c4153532d5031000f",
).replace(
    "0x4d432d52414e444f4d2d434c4153532d5039000e",
    "0x4d432d52414e444f4d2d434c4153532d5031000e",
)
assert driver_normalized == p6_driver

# Recompile the exact Java 8 Math source, not an archived byte string.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="java-diff-mc-math-asin-p9-source-", dir=root / "build") as tmp:
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", tmp,
                    stage / "bootstrap/java/lang/Math.java"], cwd=root, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    generated = (Path(tmp) / "java/lang/Math.class").read_bytes()
assert (stage / "bootstrap/java/lang/Math.class.hex").read_text().strip() == generated.hex()
assert (stage / "bootstrap/java/lang/Math.sha256").read_text().strip() == hashlib.sha256(generated).hexdigest()
assert len(generated) == 304 and hashlib.sha256(generated).hexdigest() == MATH_SHA256
assert image(source, "_bootstrapMath") == generated
assert image(p8_math, "_bootstrapMath") == generated

# Normalize the candidate back to accepted P6, with no tolerance for any other
# source byte: domain and only the measured binding20 + exact Math89 changes.
normalized = source.replace("JVMEVM:MC-RANDOM-CLASS-P9:", "JVMEVM:MC-RANDOM-CLASS-P6:")
normalized = replace_once(normalized, "    error MathAsinProfileError(uint256 code, uint256 pc);\n", "", "asin error")
normalized = replace_once(
    normalized,
    f'    bytes32 private constant DBOOT_MATH = hex"{MATH_KECCAK256}";',
    f'    bytes32 private constant DBOOT_MATH = hex"{OLD_MATH_KECCAK256}";',
    "Math leaf",
)
normalized = replace_once(
    normalized,
    "            // Binding18 is sqrt, binding19 is bounded integer sin, and binding20\n"
    "            // is the measured bounded integer inverse-sine surface. Raw Math\n"
    "            // replacement remains refused.\n",
    "            // Binding18 preserves the measured deterministic sqrt surface;\n"
    "            // binding19 is only the measured signed-zero Math.sin leaf. Raw Math\n"
    "            // replacement is refused during preparation.\n",
    "Math binding comment",
)
normalized = replace_once(
    normalized,
    '            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("asin"))\n'
    '                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {\n'
    '                return 20;\n'
    '            }\n',
    "",
    "Math binding20 mapping",
)
normalized = replace_once(
    normalized,
    "                && binding != 18 && binding != 19 && binding != 20 && s.argumentKinds.length != 1)",
    "                && binding != 18 && binding != 19 && s.argumentKinds.length != 1)",
    "native whitelist",
)
normalized = replace_once(
    normalized,
    "            || ((binding == 18 || binding == 19 || binding == 20) && (s.argumentKinds.length != 1",
    "            || ((binding == 18 || binding == 19) && (s.argumentKinds.length != 1",
    "descriptor validation",
)
dispatch = (
    "                    if (nativeBinding == 20) {\n"
    "                        // Consume only the authenticated guest's binary64 bits;\n"
    "                        // the bounded Q120 kernel uses EVM integer operations.\n"
    "                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);\n"
    "                        uint64 raw = uint64(_payload(f.stack[base]));\n"
    "                        f.stack[base] = _packDouble(_mathAsinBits(raw, opPC));\n"
    "                        f.sp = base + 1;\n"
    "                        continue;\n"
    "                    }\n"
)
normalized = replace_once(normalized, dispatch, "", "native-20 dispatch")
kernel_start = "    /// @dev Bounded Q120 inverse sine over the exact guest binary64 encoding.\n"
kernel_end = "    /// @dev Signed nearest-even integer division; callers prove |numerator| < 2^255.\n"
start = normalized.index(kernel_start)
end = normalized.index(kernel_end, start)
normalized = normalized[:start] + normalized[end:]
normalized = replace_once(normalized, function_block(normalized, "_bootstrapMath"),
                         function_block(p6, "_bootstrapMath"), "Math image")
assert normalized == p6, "P9 candidate does not normalize byte-exactly to accepted P6"

# The source-diff proof above also proves preservation of the entire packed MR01
# and sparse codec. Keep explicit sentinels so a future accidental source change
# fails with a useful message before any generated execution starts.
for invariant in (
    "uint256 private constant PACKED_FLOAT_ARRAY_FLAG = uint256(1) << 30;",
    "uint256 private constant ARRAY_WIRE_FLAGS = SPARSE_ARRAY_FLAG | PACKED_FLOAT_ARRAY_FLAG;",
    "function _usePackedFloatArray(",
    "if (!_usePackedFloatArray(meta, rank, count, nonzero))",
    "return 18;", "return 19;", "return 20;", "return 12;",
    "MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;",
    "MathAsinProfileError(1, pc)",
):
    assert invariant in source, invariant
assert source.count("nativeBinding == 20") == 1
assert source.count("binding == 20") == 1

# Reconstruct every actual root RHS to exact bytes and check each materialized
# literal hash against those bytes before deriving Solidity's P9 bootstrap root.
root_block = function_block(source, "_bootstrapRoot")
assignments = {int(i): rhs.strip() for i, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", root_block)}
assert set(assignments) == set(range(97)), len(assignments)
assert set(re.findall(r"    function (_bootstrap\w+)\(", source)) == set(
    re.findall(r"    function (_bootstrap\w+)\(", p6))
images = []
materialized_indices = {}
for i in range(97):
    rhs = assignments[i]
    call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
    const = re.fullmatch(r"(DBOOT_[A-Z_]+)", rhs)
    assert bool(call) != bool(const), (i, rhs)
    if call:
        name = call.group(1)
        leaf = image(source, name)
    else:
        constant = const.group(1)
        assert constant in CONSTANT_IMAGES, (i, constant)
        materialized_indices[constant] = i
        name = CONSTANT_IMAGES[constant]
        leaf = image(source, name)
        expression = re.search(
            r"bytes32 private constant " + constant + r"\s*=\s*([^;]+);", source
        ).group(1).strip()
        literal_hash = re.fullmatch(r'hex"([0-9a-f]+)"', expression)
        literal_image = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', expression)
        assert bool(literal_hash) != bool(literal_image), (constant, expression[:80])
        if literal_image:
            assert bytes.fromhex(literal_image.group(1)) == leaf, (i, constant, "image bytes")
    if i != 89:
        assert leaf == image(p6, name), (i, name, "non-Math image changed")
    images.append(leaf)
assert materialized_indices["DBOOT_MATH"] == 89
assert set(materialized_indices) == set(CONSTANT_IMAGES)

root_report = node_json(
    r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const k=b=>keccak256(Buffer.from(b,"hex"));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const d=keccak256(x.domain);const hs=x.images.map(k);const enc=Buffer.concat([Buffer.from(d,"hex"),w(64),w(hs.length),...hs.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(JSON.stringify({domain:d,hashes:hs,root:keccak256(enc)}));''',
    {"domain": P9_DOMAIN, "images": [b.hex() for b in images]},
)
for constant, i in materialized_indices.items():
    expression = re.search(
        r"bytes32 private constant " + constant + r"\s*=\s*([^;]+);", source
    ).group(1).strip()
    literal_hash = re.fullmatch(r'hex"([0-9a-f]+)"', expression)
    if literal_hash:
        assert literal_hash.group(1) == root_report["hashes"][i], (constant, i)
assert images[89] == generated and root_report["hashes"][89] == MATH_KECCAK256
assert source.count("h[89] = DBOOT_MATH;") == 1

report = {
    "result": "PASS",
    "basis": "exact accepted P6 packed-float engine source",
    "baselineEngineSourceSHA256": P6_SOURCE_SHA256,
    "candidateEngineSourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "normalizedByteExactToP6": normalized == p6,
    "transferredSemanticDelta": ["global native20 Math.asin(D)D bounded Q120 integer kernel", "exact Java8 Math bootstrap image89"],
    "bootstrapCount": 97,
    "materializedRootRHSLLeavesChecked": 97,
    "materializedDBootLeavesChecked": len(materialized_indices),
    "changedBootstrapIndices": [89],
    "changedOther96Images": 0,
    "mathImageBytes": len(generated),
    "mathImageSHA256": hashlib.sha256(generated).hexdigest(),
    "mathImageKeccak256": root_report["hashes"][89],
    "actualSolidityP9BootstrapRoot": root_report["root"],
    "actualSolidityOrderedLeafKeccak256": root_report["hashes"],
    "globalNativeBindings": 20,
    "retainedP6Bindings": list(range(1, 20)),
    "stringLocalBinding": 12,
    "rawLimits": [71, 471911],
    "packedFloatFlag": "0x40000000",
    "packedFloatSelector": "_usePackedFloatArray",
    "runtimeCapBytes": 393216,
}
(stage / "results").mkdir(exist_ok=True)
(stage / "results/source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
(stage / "root-commitment.json").write_text(json.dumps({
    "domain": P9_DOMAIN,
    "bootstrapCount": 97,
    "basisEngineSourceSHA256": P6_SOURCE_SHA256,
    "changedIndices": [89],
    "bootstrapRoot": root_report["root"],
    "actualSolidityBootstrapRoot": root_report["root"],
    "orderedLeafKeccak256": root_report["hashes"],
}, indent=2) + "\n")
print(json.dumps(report, indent=2))
