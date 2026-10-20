#!/usr/bin/env python3
"""Pinned offline build and exact normalized-delta check for raw73/516040."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parents[3]
PARENT = STAGE.parent / "parent-raw72-q65536"
if len(sys.argv) != 2:
    raise SystemExit("usage: build.py build/java-diff-mc-raw73-byte516040-build-TAG")
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-raw73-byte516040-build-")
assert not OUT.exists(), "build output is append-only"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (old, count)
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    assert actual == count, (old, actual, count)
    return text.replace(old, new)


parent_engine_path = PARENT / "artifacts/engine/MCEntryInterpreter.sol"
parent_coord_path = PARENT / "artifacts/coordinator/MCEntryCoordinator.sol"
parent_engine = parent_engine_path.read_text()
engine = (STAGE / "engine/MCEntryInterpreter.sol").read_text()
expected_engine = parent_engine
for old, new in (
    ("uint256 private constant MAX_RAW_CLASSES = 72;", "uint256 private constant MAX_RAW_CLASSES = 73;"),
    ("uint256 private constant MAX_RAW_BYTES = 513384;", "uint256 private constant MAX_RAW_BYTES = 516040;"),
    ("            uint32(72), uint32(513384), uint32(64), uint32(32), uint32(65536),",
     "            uint32(73), uint32(516040), uint32(64), uint32(32), uint32(65536),"),
):
    expected_engine = replace_once(expected_engine, old, new)
assert engine == expected_engine, "engine source differs outside the two raw constants and two raw config leaves"
assert "JVMEVM:MC-RANDOM-CLASS-P25" in engine
for invariant in (
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint256 private constant COMMIT_RESERVE = 25_000_000;",
    "uint32 private constant MAX_TRANSFER = 4096;",
    "uint256 private constant MAX_CONSTANT_POOL = 4096;",
    "uint256 private constant MAX_ARRAYS = 4096;",
    "uint256 private constant MAX_ARRAY_ELEMENTS = 262144;",
    "uint256 private constant MAX_OBJECTS = 4096;",
    "uint256 private constant MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS\n        + MAX_EXCEPTION_OBJECTS + 1; // one reserved emergency OOM",
    "if (jvm == 0 || jvm > 65536 || internalSteps == 0 || internalSteps > 4096)",
):
    assert invariant in engine, invariant

parent_coord = parent_coord_path.read_text()
coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
normalize_hash = lambda text: re.sub(
    r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',
    r'\g<1>ENGINEHASH\g<2>', text)
expected_coord = normalize_hash(parent_coord)
for old, new in (
    ("address[72] private decoders;", "address[73] private decoders;"),
    ("bytes32[72] private classRoots;", "bytes32[73] private classRoots;"),
    ("uint32[72] private classSizes;", "uint32[73] private classSizes;"),
    ("bytes[72] private rawNames;", "bytes[73] private rawNames;"),
    ("n == 0 || n > 72 || fixedRawNames.length != n ||", "n == 0 || n > 73 || fixedRawNames.length != n ||"),
    ("if (size == 0 || size > 513384) revert MR0Error(11);",
     "if (size == 0 || size > 516040) revert MR0Error(11);"),
    ("if (uint256(total) + size > 513384) revert MR0Error(12);",
     "if (uint256(total) + size > 516040) revert MR0Error(12);"),
):
    expected_coord = replace_once(expected_coord, old, new)
assert normalize_hash(coord) == expected_coord, "coordinator source differs outside raw count/byte envelope and engine hash pin"
assert (STAGE / "engine/build.js").read_bytes() == (PARENT / "artifacts/engine/build.js").read_bytes()
assert (STAGE / "coordinator/build.js").read_bytes() == (PARENT / "artifacts/coordinator/build.js").read_bytes()
base_diagnostic = (STAGE.parent / "raw72-q65536/tools/checkpoint_diagnostic.py").read_text()
diagnostic = (STAGE / "tools/checkpoint_diagnostic.py").read_text()
assert diagnostic == replace_once(base_diagnostic, "assert classes <= 169", "assert classes <= 170")

# Independently parse all 97 image leaves and compute the actual P25 ordered root.
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
            fn = text[text.index("    function " + call.group(1) + "("):]
            fn = fn[:fn.index("\n    function ", 1)]
            values = re.findall(r'hex"([0-9a-f]+)"', fn)
            assert len(values) == 1, (i, call.group(1), len(values))
            pairs.append(("image", values[0]))
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", expr), (i, expr)
            rhs_match = re.search(r"bytes32 private constant " + expr + r"\s*=\s*([^;]+);", text)
            assert rhs_match, (i, expr)
            rhs = rhs_match.group(1).strip()
            values = re.findall(r'hex"([0-9a-f]+)"', rhs)
            assert len(values) == 1, (i, expr, rhs)
            pairs.append(("image" if rhs.startswith("keccak256(") else "hexhash", values[0]))
    js = r'''const fs=require('fs'),{keccak256:k}=require('js-sha3');const x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');let hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(JSON.stringify({root:k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(97),...hs.map(v=>Buffer.from(v,'hex'))])),leaves:hs}));'''
    env = {**os.environ, "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"), "npm_config_offline": "true"}
    result = subprocess.run(["node", "-e", js], cwd=ROOT, env=env,
                            input=json.dumps({"domain": domain, "pairs": pairs}),
                            text=True, capture_output=True, check=True)
    parsed = json.loads(result.stdout)
    return parsed["root"], parsed["leaves"]

parent_pins = json.loads((PARENT / "artifacts/parent-build-pins.json").read_text())
root_domain = "JVMEVM:MC-RANDOM-CLASS-P25:BOOTSTRAP:1"
parent_root, parent_leaves = bootstrap_root(parent_engine, root_domain)
actual_root, actual_leaves = bootstrap_root(engine, root_domain)
assert parent_root == parent_pins["bootstrapRoot"] == "60d5d3b5d4ecaf68427aa6bba3dcb3084e04b64f09b5d155d2f651746aeb875e"
assert actual_root == parent_root and actual_leaves == parent_leaves and len(actual_leaves) == 97

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
    "npm_config_offline": "true",
}


def run(label: str, args: list[str], timeout: int = 900) -> None:
    with (OUT / f"{label}.log").open("w") as log:
        subprocess.run(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)

# Compile only the scoped candidate Solidity from the frozen pinned scripts.
run("engine-build", ["node", str(STAGE / "engine/build.js")])
engine_art = json.loads((STAGE / "engine/MCEntryInterpreter.json").read_text())
engine_runtime = bytes.fromhex(engine_art["deployedBytecode"])
assert len(engine_runtime) <= 393216
parent_engine_art = json.loads((PARENT / "artifacts/engine/MCEntryInterpreter.json").read_text())
assert engine_art["abi"] == parent_engine_art["abi"]
assert engine_art["storageLayout"] == parent_engine_art["storageLayout"]
engine_hash = engine_art["codeHashes"]["runtimeKeccak256"]
assert f'ENGINE_CODEHASH = hex"{engine_hash}";' in coord
run("coordinator-build", ["node", str(STAGE / "coordinator/build.js")])
coord_art = json.loads((STAGE / "coordinator/MCEntryCoordinator.json").read_text())
coord_runtime = bytes.fromhex(coord_art["deployedBytecode"])
assert len(coord_runtime) <= 24576
coord_hash = coord_art["codeHashes"]["runtimeKeccak256"]

# Require the observer to equal the accepted P25 generated-only source after only
# explicit raw-boundary, generated-probe and artifact-pin substitutions.
base_driver = (PARENT / "generated-probe-driver.go.txt").read_text()
expected_driver = base_driver
edits = (
    ("len(m.Decoders) > 72", "len(m.Decoders) > 73"),
    ("func fixtureNames() [][]byte { return fixtureNamesLimit(72) }",
     "func fixtureNames() [][]byte { return fixtureNamesLimit(73) }"),
    ("// reach the coordinator/engine's own raw73 guards. Normal driver paths stay at72.",
     "// reach the coordinator/engine's own raw74 guards. Normal driver paths stay at73."),
    ('''case "raw73":
		names := fixtureNamesLimit(73)
		if len(names) != 73 {
			panic("raw73 engine probe requires73 bindings")
		}
		classes = rawFixtureClasses(zipPath, names)
		wantName, wantCode, wantDetail = "LinkError", 1, 73
	case "bytes513385":
		classes = rawFixtureClasses(zipPath, fixtureNamesLimit(72))
		wantName, wantCode, wantDetail = "LinkError", 1, 513385''',
     '''case "raw74":
		names := fixtureNamesLimit(74)
		if len(names) != 74 {
			panic("raw74 engine probe requires74 bindings")
		}
		classes = rawFixtureClasses(zipPath, names)
		wantName, wantCode, wantDetail = "LinkError", 1, 74
	case "bytes516041":
		classes = rawFixtureClasses(zipPath, fixtureNamesLimit(73))
		wantName, wantCode, wantDetail = "LinkError", 1, 516041'''),
    ('''names := fixtureNamesLimit(72)
	if len(names) != 72 {
		panic("direct engine start requires72 bindings")''',
     '''names := fixtureNamesLimit(73)
	if len(names) != 73 {
		panic("direct engine start requires73 bindings")'''),
    ('''if total != expectedTotal {
		panic(fmt.Sprintf("engine direct positive input is %d, want%d", total, expectedTotal))
	}''',
     '''if expectedTotal != 0 && total != expectedTotal {
		panic(fmt.Sprintf("engine direct positive input is %d, want%d", total, expectedTotal))
	}'''),
    ('''func boundaryRaw73(dir, artPath, zipPath string) {
	names := fixtureNamesLimit(73)
	if len(names) != 73 {
		panic("raw73 coordinator probe requires73 bindings")''',
     '''func boundaryRaw74(dir, artPath, zipPath string) {
	names := fixtureNamesLimit(74)
	if len(names) != 74 {
		panic("raw74 coordinator probe requires74 bindings")'''),
    ("coordinator raw73 refusal", "coordinator raw74 refusal"),
    ("coordinator-raw73.json", "coordinator-raw74.json"),
    ('''names := fixtureNamesLimit(72)
	if len(names) != 72 {
		panic("byte boundary requires72 bindings")''',
     '''names := fixtureNamesLimit(73)
	if len(names) != 73 {
		panic("byte boundary requires73 bindings")'''),
    ("expected == 513384", "expected == 516040"),
    ("coordinator-byte-513384.json", "coordinator-byte-516040.json"),
    ("\"probe\": \"coordinator-byte-513384\"", "\"probe\": \"coordinator-byte-516040\""),
    ("expected == 513385", "expected == 516041"),
    ("coordinator-byte-513385.json", "coordinator-byte-516041.json"),
    ('''case "boundary-raw73":
		boundaryRaw73(os.Args[2], os.Args[3], os.Args[5])''',
     '''case "boundary-raw74":
		boundaryRaw74(os.Args[2], os.Args[3], os.Args[5])'''),
    ("total != 513384 && total != 513385", "total != 516040 && total != 516041"),
    ("engine-byte-513384", "engine-byte-516040"),
    ("65536, 513384", "65536, 516040"),
    ("engine-direct-raw72", "engine-direct-raw73"),
    ("q, 9778", "q, 0"),
)
for old, new in edits:
    expected_driver = replace_once(expected_driver, old, new)
# Artifact-derived literals are the only additional observer edits.
expected_driver = replace_once(expected_driver,
    'const immutableEngineSHA256 = "f03a52e408a516d95595959cdca2b159aae6c9fd6e47c919c29e5fed4d69bf23"',
    f'const immutableEngineSHA256 = "{engine_art["codeHashes"]["runtimeSHA256"]}"')
expected_driver = replace_once(expected_driver,
    'const immutableEngineKeccak = "0x299ca21bb63628b6ca044289e8b4eb30469327ad12ba01620e905a3888e0fa3a"',
    f'const immutableEngineKeccak = "0x{engine_hash}"')
expected_driver = replace_once(expected_driver,
    'const immutableCoordinatorKeccak = "0xb7aa0b4ce3a5cde372d61a7362c758b8dd48af0da9ff6a251cb15ec4c7d30371"',
    f'const immutableCoordinatorKeccak = "0x{coord_hash}"')
expected_driver = replace_count(expected_driver, "len(engineRun) != 392091", f"len(engineRun) != {len(engine_runtime)}", 1)
expected_driver = replace_once(expected_driver, "len(run) != 392091", f"len(run) != {len(engine_runtime)}")
expected_driver = replace_once(expected_driver, "len(coordRun) != 5394", f"len(coordRun) != {len(coord_runtime)}")
driver = (STAGE / "driver.go").read_text()
if driver != expected_driver:
    import difflib
    (OUT / "observer-normalization.diff").write_text("".join(difflib.unified_diff(
        expected_driver.splitlines(True), driver.splitlines(True),
        fromfile="expected-accepted-P25-normalization", tofile="candidate-driver")))
    raise AssertionError("observer has edits outside the raw73 envelope, diagnostics and compiled-code pins")
assert "const ordinaryGas = uint64(1_000_000_000)" in driver
assert "return 30 * time.Second" in driver
assert "len(m.Decoders) > 73" in driver and "fixtureNamesLimit(73)" in driver
assert "len(classes) > 4096" not in driver
assert "MC-RANDOM-CLASS-P25" in driver
assert "len(classes) > 74" not in driver

# Build an immutable copy of the observer and verify it without modifying source.
(OUT / "main.go").write_text(driver)
run("gofmt", ["gofmt", "-w", str(OUT / "main.go")])
run("go-build", ["go", "build", "-trimpath", "-o", str(OUT / "driver"), str(OUT / "main.go")])
run("go-vet", ["go", "vet", str(OUT / "main.go")])

prior_root = parent_pins["bootstrapRoot"]
assert prior_root == actual_root
pins = {
    "profile": "MC-RANDOM-CLASS-P25-RAW73-BYTE516040-LOCAL",
    "basis": parent_pins["basis"],
    "domain": "MC-RANDOM-CLASS-P25",
    "address": parent_pins["address"],
    "owner": parent_pins["owner"],
    "bootstrapCount": 97,
    "bootstrapRoot": actual_root,
    "orderedBootstrapLeaves": actual_leaves,
    "diagnosticClassBound": 170,
    "rawLimits": [73, 516040],
    "maxJvmSteps": 65536,
    "maxInternalSteps": 4096,
    "maxTransfer": 4096,
    "maxClassBytes": 262144,
    "maxArrays": 4096,
    "maxObjects": 4096,
    "maxHandles": 8449,
    "maxCheckpointBytes": 1048576,
    "commitReserve": 25000000,
    "callWatchdogMs": 30000,
    "ordinaryGas": 1000000000,
    "runtimeCap": 393216,
    "engine": {"bytes": len(engine_runtime), **engine_art["codeHashes"]},
    "coordinator": {"bytes": len(coord_runtime), **coord_art["codeHashes"]},
    "driverSHA256": sha(driver.encode()),
    "sourceHashes": {
        "engine": sha(engine.encode()), "coordinator": sha(coord.encode()),
        "engineBuild": sha((STAGE / "engine/build.js").read_bytes()),
        "coordinatorBuild": sha((STAGE / "coordinator/build.js").read_bytes()),
        "diagnostic": sha(diagnostic.encode()),
    },
    "normalizedChanges": {
        "engine": ["MAX_RAW_CLASSES 72->73", "MAX_RAW_BYTES 513384->516040",
                   "_configRoot raw-count and raw-bytes leaves only"],
        "coordinator": ["four fixed arrays 72->73", "count guard 72->73",
                        "per-class and aggregate bytes 513384->516040", "engine codehash pin"],
        "observer": ["normal raw bound 72->73", "raw74 driver/coordinator/engine refusal probes",
                     "byte witness 516040 positive / 516041 refusal", "MR01 class bound 169->170"],
    },
    "sourceInvariants": {
        "bootstrapLeavesEqualAcceptedP25": actual_leaves == parent_leaves,
        "historicalP25LabelsRetained": True,
        "noBootstrapImagesAdded": True,
        "maxJvm65536Unchanged": True,
        "internalBudget4096Unchanged": True,
        "allOtherRawAndHeapCapsUnchanged": True,
    },
}
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(OUT / "source-audit.json").write_text(json.dumps({
    "basis": "accepted P25 parent-raw72-q65536 artifacts, not source reconstructed from a worker tree",
    "acceptedP25EngineSourceSHA256": sha(parent_engine.encode()),
    "candidateEngineSourceSHA256": sha(engine.encode()),
    "acceptedP25CoordinatorSourceSHA256": sha(parent_coord.encode()),
    "candidateCoordinatorSourceSHA256": sha(coord.encode()),
    "normalizedEngineExact": True,
    "normalizedCoordinatorExactExceptEngineCodehash": True,
    "bootstrapLeafCount": len(actual_leaves),
    "acceptedP25BootstrapRoot": parent_root,
    "candidateBootstrapRoot": actual_root,
    "bootstrapLeavesByteIdentical": actual_leaves == parent_leaves,
    "engineCodehashPinnedByCoordinator": coord_hash == engine_hash,
    "observerNormalizedAgainstAcceptedP25GeneratedDriver": True,
    "allRuntimeAndProfileCapsRetained": True,
}, indent=2) + "\n")
print(json.dumps({"engine": pins["engine"], "coordinator": pins["coordinator"],
                  "bootstrapRoot": actual_root, "bootstrapLeaves": len(actual_leaves),
                  "rawLimits": pins["rawLimits"], "maxJvmSteps": pins["maxJvmSteps"],
                  "driver": str(OUT / "driver")}, indent=2))
