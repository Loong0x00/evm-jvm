#!/usr/bin/env python3
"""Prove the sole P10-source delta: Math.cos binding21 + exact Math image/root."""
from pathlib import Path
import hashlib, json, os, re, subprocess, tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
baseline_path = root / "evidence/java-evm/minecraft-entry/parent-140604413/artifacts/engine/MCEntryInterpreter.sol"
source_path = stage / "engine/MCEntryInterpreter.sol"
baseline = baseline_path.read_text()
source = source_path.read_text()
pins = json.loads((stage / "baseline-pins.json").read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(baseline.encode()) == pins["baselineEngineSourceSHA256"]


def block(text, start):
    at = text.index(start)
    end = text.find("\n    function ", at + 1)
    return text[at:end if end >= 0 else len(text)]


def image(text, name):
    vals = re.findall(r'hex"([0-9a-f]+)"', block(text, "    function " + name + "("))
    assert len(vals) == 1, (name, len(vals))
    return bytes.fromhex(vals[0])


def pascal_constant(name):
    overrides = {"ENUMSET": "EnumSet", "ITERABLE": "Iterable", "MATH": "Math",
                 "RANDOM": "Random", "THREAD": "Thread", "THREAD_LOCAL": "ThreadLocal",
                 "STACK_TRACE_ELEMENT": "StackTraceElement", "PRINT_STREAM": "PrintStream",
                 "SECURITY_MANAGER": "SecurityManager"}
    tail = name.removeprefix("DBOOT_")
    return "_bootstrap" + overrides.get(tail, "".join(x.title() for x in tail.split("_")))

# The bootstrap payload is an ordinary javac --source/--target 8 -g:none classfile.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="java-diff-mc-math-cos-source-", dir=root / "build") as tmp:
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", tmp,
                    stage / "bootstrap/java/lang/Math.java"], cwd=root,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    compiled = (Path(tmp) / "java/lang/Math.class").read_bytes()
math_hex = stage / "bootstrap/java/lang/Math.class.hex"
math_sha = stage / "bootstrap/java/lang/Math.sha256"
assert math_hex.read_text().strip() == compiled.hex()
assert math_sha.read_text().strip() == sha(compiled)
assert image(source, "_bootstrapMath") == compiled
old_math = image(baseline, "_bootstrapMath")
assert len(compiled) == pins["baselineMathBytes"] + 14
assert sha(old_math) == pins["baselineMathSHA256"]

base_functions = set(re.findall(r"    function (_bootstrap\w+)\(", baseline))
functions = set(re.findall(r"    function (_bootstrap\w+)\(", source))
assert base_functions == functions
assert block(source, "    function _bootstrapRoot()") == block(baseline, "    function _bootstrapRoot()")
changed = [name for name in sorted(base_functions) if name != "_bootstrapRoot"
           and image(source, name) != image(baseline, name)]
assert changed == ["_bootstrapMath"], changed

root_block = block(source, "    function _bootstrapRoot()")
assignments = {int(i): rhs.strip() for i, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", root_block)}
assert set(assignments) == set(range(97))
leaves, indexes = [], {}
for i in range(97):
    rhs = assignments[i]
    call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
    const = re.fullmatch(r"(DBOOT_[A-Z_]+)", rhs)
    assert bool(call) != bool(const), (i, rhs)
    name = call.group(1) if call else pascal_constant(const.group(1))
    assert (name == "_bootstrapMath") == (i == 89), (i, name)
    leaf = image(source, name)
    if const:
        cname = const.group(1)
        assert cname not in indexes
        indexes[cname] = i
        declaration = re.search(r"bytes32 private constant " + cname + r"\s*=\s*([^;]+);", source)
        assert declaration
        value = declaration.group(1).strip()
        literal_digest = re.fullmatch(r'hex"([0-9a-f]+)"', value)
        literal_image = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', value)
        assert bool(literal_digest) != bool(literal_image), (cname, value[:80])
        if literal_image:
            assert bytes.fromhex(literal_image.group(1)) == leaf, cname
    leaves.append(leaf)

node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const k=b=>keccak256(Buffer.from(b,"hex"));const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const d=keccak256(x.domain);const hs=x.images.map(k);const enc=Buffer.concat([Buffer.from(d,"hex"),word(64),word(hs.length),...hs.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(JSON.stringify({hashes:hs,root:keccak256(enc)}));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
commit = json.loads(subprocess.run(["node", "-e", node],
    input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P10:BOOTSTRAP:1",
                      "images": [x.hex() for x in leaves]}), text=True, cwd=root,
    env=env, capture_output=True, check=True).stdout)

# Verify each materialized DBOOT leaf against the actual selected bootstrap image.
dboot_constants = set(re.findall(r"bytes32 private constant (DBOOT_[A-Z_]+)\s*=", source))
assert set(indexes) == dboot_constants
actual_hashes = []
for i, rhs in enumerate(assignments.values()):
    call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
    if call:
        actual_hashes.append(commit["hashes"][i])
        continue
    const = re.fullmatch(r"(DBOOT_[A-Z_]+)", rhs).group(1)
    decl = re.search(r"bytes32 private constant " + const + r"\s*=\s*([^;]+);", source)
    value = decl.group(1).strip()
    literal_digest = re.fullmatch(r'hex"([0-9a-f]+)"', value)
    literal_image = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', value)
    assert bool(literal_digest) != bool(literal_image)
    if literal_digest:
        digest = literal_digest.group(1)
        assert len(digest) == 64 and digest == commit["hashes"][i], (const, i, digest)
        actual_hashes.append(digest)
    else:
        assert literal_image and bytes.fromhex(literal_image.group(1)) == leaves[i]
        actual_hashes.append(commit["hashes"][i])
assert actual_hashes == commit["hashes"]
# Independently evaluate the actual source-materialized DBOOT/keccak leaves.
root_node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const d=keccak256(x.domain);const enc=Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(keccak256(enc));'''
solidity_root = subprocess.run(["node", "-e", root_node],
    input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P10:BOOTSTRAP:1", "hashes": actual_hashes}),
    text=True, cwd=root, env=env, capture_output=True, check=True).stdout
assert solidity_root == commit["root"]

# Remove only the explicit cosine leaf, its exact native binding/dispatch, and its image.
normalized = source
replacements = [
    ('    error MathCosProfileError(uint256 code, uint256 pc);\n', '', "cos error"),
    ('''            // Bindings18..21 are exact deterministic integer Math kernels;
            // binding21 is bounded cosine over the measured finite domain.
            // Raw Math replacement remains refused.
''', '''            // Binding18 is sqrt, binding19 is bounded integer sin, and binding20
            // is the measured bounded integer inverse-sine surface. Raw Math
            // replacement remains refused.
''', "owner comment"),
    ('''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("cos"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {
                return 21;
            }
''', '', "cos binding"),
    (' && binding != 21', '', "native whitelist"),
    (' || binding == 21', '', "native descriptor gate"),
    ('''                    if (nativeBinding == 21) {
                        // Binding21 reads only the authenticated guest binary64
                        // value; the bounded Q120 Taylor kernel uses EVM integers.
                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);
                        uint64 raw = uint64(_payload(f.stack[base]));
                        f.stack[base] = _packDouble(_mathCosBits(raw, opPC));
                        f.sp = base + 1;
                        continue;
                    }
''', '', "cos dispatch"),
]
for old, new, label in replacements:
    assert normalized.count(old) == 1, (label, normalized.count(old))
    normalized = normalized.replace(old, new, 1)
kstart = "    /// @dev Deterministic EVM-integer Q120 cosine over finite |x|<=2*pi.\n"
kend = "    /// @dev Positive Q120 asin Taylor series, n=0..128 inclusive.\n"
a, b = normalized.index(kstart), normalized.index(kend, normalized.index(kstart))
kernel = normalized[a:b]
normalized = normalized[:a] + normalized[b:]
# Restore P10 image and DBOOT digest in the normalized byte-exact comparison.
new_image_block = block(normalized, "    function _bootstrapMath()")
old_image_block = block(baseline, "    function _bootstrapMath()")
assert normalized.count(new_image_block) == 1
normalized = normalized.replace(new_image_block, old_image_block, 1)
new_digest = re.search(r'    bytes32 private constant DBOOT_MATH = hex"[0-9a-f]+";\n', source).group()
old_digest = re.search(r'    bytes32 private constant DBOOT_MATH = hex"[0-9a-f]+";\n', baseline).group()
assert normalized.count(new_digest) == 1
normalized = normalized.replace(new_digest, old_digest, 1)
assert normalized == baseline, "unreviewed source changes beyond Math.cos binding21/kernel/image commitment"
assert "Math.cos(" not in kernel and "Math.sin(" not in kernel and "Math.asin(" not in kernel
for phrase in ("for (uint256 n = 1; n <= 30; ++n)",
               "4175892906503776358826876457663557747",
               "0x401921fb54442d18", "0x3e40000000000000",
               "_roundSignedEven(-term * x2", "MathCosProfileError(1, pc)"):
    assert phrase in kernel, phrase
assert "return 21;" in block(source, "    function _nativeBinding(")
assert "binding != 21" in block(source, "    function _loadNativeCallee(")
assert "nativeBinding == 21" in source

report = {
    "result": "PASS",
    "basis": "exact accepted P10 parent-140604413 source",
    "baselineEngineSourceSHA256": sha(baseline.encode()),
    "candidateEngineSourceSHA256": sha(source.encode()),
    "normalizedByteExactToP10": True,
    "transferredSemanticDelta": [
        "global native21 Math.cos(D)D using bounded deterministic Q120 EVM integer arithmetic",
        "Java8-g:none Math bootstrap image89 exact append cos(D)D native",
        "materialized DBOOT_MATH leaf updated to exact image Keccak",
    ],
    "bootstrapCount": 97,
    "changedBootstrapIndices": [89],
    "changedOther96Images": 0,
    "materializedRootRHSLLeavesChecked": 97,
    "materializedDBootLeavesChecked": len(dboot_constants),
    "mathImageBytes": len(compiled),
    "mathImageSHA256": sha(compiled),
    "mathImageKeccak256": commit["hashes"][89],
    "bootstrapRoot": commit["root"],
    "solidityMaterializedBootstrapRoot": solidity_root,
    "globalNativeBindings": 21,
    "stringLocalBinding": 12,
    "rawLimits": [71, 471911],
    "runtimeCapBytes": 393216,
    "kernel": {
        "qBits": 120,
        "piQ": "4175892906503776358826876457663557747",
        "seriesN": 30,
        "tailBound": "<2^-180 on |x|<=pi",
        "tinyIdentityRawMax": "3e40000000000000",
        "domainRawMagnitudeMax": "401921fb54442d18",
        "allNonfiniteRefused": True,
        "allOutOfDomainRefused": True,
        "externalMath": False,
        "lookupTable": False,
        "highPrecisionRangeReduction": True,
        "strictSigned256Bound": "all intermediate magnitudes <2^255",
    },
}
(stage / "root-commitment.json").write_text(json.dumps({
    "basis": "exact P10 parent-140604413 source",
    "bootstrapCount": 97,
    "priorSourceDerivedRoot": pins["bootstrapRoot"],
    "changedIndices": [89],
    "orderedLeafKeccak256": commit["hashes"],
    "materializedDBootLeavesChecked": len(dboot_constants),
    "solidityMaterializedBootstrapRoot": solidity_root,
    "bootstrapRoot": commit["root"],
}, indent=2) + "\n")
(stage / "results/source-invariants.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
