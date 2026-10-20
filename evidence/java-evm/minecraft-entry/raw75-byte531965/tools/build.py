#!/usr/bin/env python3
"""Audit the isolated P27 raw74->raw75 envelope and build it offline."""
from __future__ import annotations

import copy
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
PARENT = ROOT / "evidence/java-evm/minecraft-entry/parent-raw74-byte518516"
ART = PARENT / "artifacts"
PROFILE = "MC-RANDOM-CLASS-P27-RAW75-BYTE531965"
BOOTSTRAP_ROOT = "70b6401e629c75ad213efb8b6bf484cb3f364dc9a281031c4651069bd3776ec4"
DRIVER_TEMPLATE_SHA256 = "f80881acb6cfc3701c8cd3d151ba0de40eb1c57933a01a5ff98e88822dcc5476"
if len(sys.argv) != 2:
    raise SystemExit("usage: build.py build/java-diff-mc-raw75-byte531965-build-TAG")
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-raw75-byte531965-build-")
assert not OUT.exists(), "build outputs are append-only"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (old[:160], count)
    return text.replace(old, new, 1)


parent_pins = json.loads((ART / "parent-build-pins.json").read_text())
base_engine_path = ART / "engine/MCEntryInterpreter.sol"
base_coord_path = ART / "coordinator/MCEntryCoordinator.sol"
base_engine = base_engine_path.read_text()
base_coord = base_coord_path.read_text()
base_engine_art = json.loads((ART / "engine/MCEntryInterpreter.json").read_text())
base_coord_art = json.loads((ART / "coordinator/MCEntryCoordinator.json").read_text())
assert parent_pins["profile"] == "MC-RANDOM-CLASS-P27-RAW74-BYTE518516"
assert parent_pins["rawLimits"] == [74, 518516]
assert parent_pins["bootstrapCount"] == 97 and parent_pins["bootstrapRoot"] == BOOTSTRAP_ROOT
assert parent_pins["checkpointCap"] == 1048576 and parent_pins["reserve"] == 25000000
assert parent_pins["maxJvmSteps"] == 65536 and parent_pins["maxInternalSteps"] == 4096
assert parent_pins["runtimeCap"] == 393216 and parent_pins["callWatchdogMs"] == 30000
assert parent_pins["engine"]["runtimeSHA256"] == base_engine_art["codeHashes"]["runtimeSHA256"]
assert parent_pins["engine"]["runtimeKeccak256"] == base_engine_art["codeHashes"]["runtimeKeccak256"]
assert parent_pins["coordinator"]["runtimeSHA256"] == base_coord_art["codeHashes"]["runtimeSHA256"]
assert parent_pins["coordinator"]["runtimeKeccak256"] == base_coord_art["codeHashes"]["runtimeKeccak256"]
assert base_engine_art["sourceHashes"]["MCEntryInterpreter.sol"] == sha(base_engine.encode())
assert base_coord_art["sourceHashes"]["MCEntryCoordinator.sol"] == sha(base_coord.encode())

# The engine source is byte-for-byte P27 except its raw count/byte constants and
# the two corresponding configuration leaves. No bootstrap slot is edited.
expected_engine = base_engine
for old, new in (
    ("uint256 private constant MAX_RAW_CLASSES = 74;", "uint256 private constant MAX_RAW_CLASSES = 75;"),
    ("uint256 private constant MAX_RAW_BYTES = 518516;", "uint256 private constant MAX_RAW_BYTES = 531965;"),
    ("            uint32(74), uint32(518516), uint32(64), uint32(32), uint32(65536),",
     "            uint32(75), uint32(531965), uint32(64), uint32(32), uint32(65536),"),
):
    expected_engine = replace_once(expected_engine, old, new)
candidate_engine = (STAGE / "engine/MCEntryInterpreter.sol").read_text()
assert candidate_engine == expected_engine, "engine differs outside the two raw limits and two config leaves"
for invariant in (
    "uint256 private constant MAX_CONSTANT_POOL = 4096;",
    "uint256 private constant MAX_ARRAYS = 4096;",
    "uint256 private constant MAX_ARRAY_ELEMENTS = 262144;",
    "uint256 private constant MAX_OBJECTS = 4096;",
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint32 private constant MAX_TRANSFER = 4096;",
    "uint32(75), uint32(531965), uint32(64), uint32(32), uint32(65536),",
    "if (jvm == 0 || jvm > 65536 || internalSteps == 0 || internalSteps > 4096)",
    "uint256 private constant COMMIT_RESERVE = 25_000_000;",
    "uint256 private constant MAX_FRAMES = 128;",
):
    assert invariant in candidate_engine, invariant

# Only the four coordinator arrays, count guard, two byte guards and the
# compiled candidate engine-codehash pin may differ.
def normalize_engine_hash(text: str) -> str:
    normalized, n = re.subn(
        r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',
        r'\g<1>ENGINEHASH\g<2>', text)
    assert n == 1, n
    return normalized

expected_coord = normalize_engine_hash(base_coord)
for old, new in (
    ("address[74] private decoders;", "address[75] private decoders;"),
    ("bytes32[74] private classRoots;", "bytes32[75] private classRoots;"),
    ("uint32[74] private classSizes;", "uint32[75] private classSizes;"),
    ("bytes[74] private rawNames;", "bytes[75] private rawNames;"),
    ("n == 0 || n > 74 || fixedRawNames.length != n ||", "n == 0 || n > 75 || fixedRawNames.length != n ||"),
    ("if (size == 0 || size > 518516) revert MR0Error(11);", "if (size == 0 || size > 531965) revert MR0Error(11);"),
    ("if (uint256(total) + size > 518516) revert MR0Error(12);", "if (uint256(total) + size > 531965) revert MR0Error(12);"),
):
    expected_coord = replace_once(expected_coord, old, new)
candidate_coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
assert normalize_engine_hash(candidate_coord) == expected_coord, "coordinator differs outside the raw envelope and engine pin"

# Build tools are the accepted P27 compiler drivers, copied byte-for-byte.
for name in ("engine", "coordinator"):
    candidate_build = STAGE / name / "build.js"
    parent_build = ART / name / "build.js"
    assert candidate_build.read_bytes() == parent_build.read_bytes()
    assert sha(candidate_build.read_bytes()) == parent_pins["sourceHashes"][name + "Build"]

# Decode all 97 ordered leaves and recompute the P27 bootstrap commitment from
# actual embedded images/hashes. This proves the new raw slot did not add one.
ENV = {
    **os.environ,
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "npm_config_offline": "true",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GOTOOLCHAIN": "local",
    "PYTHONDONTWRITEBYTECODE": "1",
}

def bootstrap_root(text: str) -> tuple[str, list[str]]:
    body = text[text.index("    function _bootstrapRoot("):]
    body = body[:body.index("\n    function ", 1)]
    assignments = {int(i): value.strip() for i, value in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(assignments) == set(range(97))
    pairs: list[tuple[str, str]] = []
    for index in range(97):
        expr = assignments[index]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", expr)
        if call:
            fn = text[text.index("    function " + call.group(1) + "("):]
            fn = fn[:fn.index("\n    function ", 1)]
            values = re.findall(r'hex"([0-9a-f]+)"', fn)
            assert len(values) == 1, (index, call.group(1), len(values))
            pairs.append(("image", values[0]))
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", expr), (index, expr)
            rhs = re.search(r"bytes32 private constant " + expr + r"\s*=\s*([^;]+);", text)
            assert rhs, expr
            values = re.findall(r'hex"([0-9a-f]+)"', rhs.group(1))
            assert len(values) == 1, (index, expr)
            pairs.append(("image" if rhs.group(1).strip().startswith("keccak256(") else "hexhash", values[0]))
    js = r'''const fs=require('fs'),{keccak256:k}=require('js-sha3');const x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');let hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(JSON.stringify({root:k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(97),...hs.map(v=>Buffer.from(v,'hex'))])),leaves:hs}));'''
    result = subprocess.run(["node", "-e", js], cwd=ROOT, env=ENV,
                            input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P27:BOOTSTRAP:1", "pairs": pairs}),
                            text=True, capture_output=True, check=True, timeout=120)
    parsed = json.loads(result.stdout)
    return parsed["root"], parsed["leaves"]

base_root, base_leaves = bootstrap_root(base_engine)
candidate_root, candidate_leaves = bootstrap_root(candidate_engine)
assert base_root == BOOTSTRAP_ROOT and candidate_root == base_root
assert candidate_leaves == base_leaves == parent_pins["orderedBootstrapLeaves"]

# Observer class bound is the only diagnostic decoder edit: 171->172.
diag_path = STAGE / "tools/checkpoint_diagnostic.py"
candidate_diag = diag_path.read_text()
base_diag = replace_once(candidate_diag, "assert classes <= 172", "assert classes <= 171")
assert sha(base_diag.encode()) == parent_pins["diagnosticSourceSHA256"]
expected_diag = replace_once(base_diag, "assert classes <= 171", "assert classes <= 172")
assert candidate_diag == expected_diag

# Generate only from the accepted P27 raw74 parent probe template. Exact,
# uniquely matched edits change the observer's raw bounds/probes and artifact
# pins; the profile/domain and bootstrap code remain untouched.
template_path = PARENT / "generated-probe-driver.go.txt"
template = template_path.read_text()
assert sha(template.encode()) == DRIVER_TEMPLATE_SHA256

def driver_source(engine_artifact: dict, coord_artifact: dict) -> str:
    text = template
    edits = (
        ("len(m.Decoders) > 74", "len(m.Decoders) > 75"),
        ("func fixtureNames() [][]byte { return fixtureNamesLimit(74) }",
         "func fixtureNames() [][]byte { return fixtureNamesLimit(75) }"),
        ("// reach the coordinator/engine's own raw75 guards. Normal driver paths stay at74.",
         "// reach the coordinator/engine's own raw76 guards. Normal driver paths stay at75."),
        ('''case "raw75":
		names := fixtureNamesLimit(75)
		if len(names) != 75 {
			panic("raw75 engine probe requires75 bindings")
		}
		classes = rawFixtureClasses(zipPath, names)
		wantName, wantCode, wantDetail = "LinkError", 1, 75
	case "bytes518517":
		classes = rawFixtureClasses(zipPath, fixtureNamesLimit(74))
		wantName, wantCode, wantDetail = "LinkError", 1, 518517''',
         '''case "raw76":
		names := fixtureNamesLimit(76)
		if len(names) != 76 {
			panic("raw76 engine probe requires76 bindings")
		}
		classes = rawFixtureClasses(zipPath, names)
		wantName, wantCode, wantDetail = "LinkError", 1, 76
	case "bytes531966":
		classes = rawFixtureClasses(zipPath, fixtureNamesLimit(75))
		wantName, wantCode, wantDetail = "LinkError", 1, 531966'''),
        ('''names := fixtureNamesLimit(74)
	if len(names) != 74 {
		panic("direct engine start requires74 bindings")''',
         '''names := fixtureNamesLimit(75)
	if len(names) != 75 {
		panic("direct engine start requires75 bindings")'''),
        ('''func boundaryRaw75(dir, artPath, zipPath string) {
	names := fixtureNamesLimit(75)
	if len(names) != 75 {
		panic("raw75 coordinator probe requires75 bindings")''',
         '''func boundaryRaw76(dir, artPath, zipPath string) {
	names := fixtureNamesLimit(76)
	if len(names) != 76 {
		panic("raw76 coordinator probe requires76 bindings")'''),
        ("coordinator raw75 refusal", "coordinator raw76 refusal"),
        ("coordinator-raw75.json", "coordinator-raw76.json"),
        ('''names := fixtureNamesLimit(74)
	if len(names) != 74 {
		panic("byte boundary requires74 bindings")''',
         '''names := fixtureNamesLimit(75)
	if len(names) != 75 {
		panic("byte boundary requires75 bindings")'''),
        ("if expected == 518516 && r.Err == nil {", "if expected == 531965 && r.Err == nil {"),
        ("coordinator-byte-518516.json", "coordinator-byte-531965.json"),
        ('"probe": "coordinator-byte-518516"', '"probe": "coordinator-byte-531965"'),
        ("if expected == 518517 && r.Err != nil", "if expected == 531966 && r.Err != nil"),
        ("coordinator-byte-518517.json", "coordinator-byte-531966.json"),
        ("case \"boundary-raw75\":\n\t\tboundaryRaw75(os.Args[2], os.Args[3], os.Args[5])",
         "case \"boundary-raw76\":\n\t\tboundaryRaw76(os.Args[2], os.Args[3], os.Args[5])"),
        ("total != 518516 && total != 518517", "total != 531965 && total != 531966"),
        ('"engine-byte-518516", 65536, 518516', '"engine-byte-531965", 65536, 531965'),
        ('"engine-direct-raw74", q, 0', '"engine-direct-raw75", q, 0'),
        ("len(engineRun) != 392091", f"len(engineRun) != {len(bytes.fromhex(engine_artifact['deployedBytecode']))}"),
        ("len(coordRun) != 5394", f"len(coordRun) != {len(bytes.fromhex(coord_artifact['deployedBytecode']))}"),
        ("len(run) != 392091", f"len(run) != {len(bytes.fromhex(engine_artifact['deployedBytecode']))}"),
        ("const immutableEngineSHA256 = \"b314950ec433baa68b8562d01733f27cc3dccdf3666973206b29802978cd203e\"",
         f"const immutableEngineSHA256 = \"{engine_artifact['codeHashes']['runtimeSHA256']}\""),
        ("const immutableEngineKeccak = \"0x9428e84d38861ae14aa217fe4d451e05f9f307091334df8f90e23badb9662403\"",
         f"const immutableEngineKeccak = \"0x{engine_artifact['codeHashes']['runtimeKeccak256']}\""),
        ("const immutableCoordinatorKeccak = \"0xa71b3c48a4ecaf1b7b64ef6edf752abe9664b4257107cc91f4408b20d7114192\"",
         f"const immutableCoordinatorKeccak = \"0x{coord_artifact['codeHashes']['runtimeKeccak256']}\""),
    )
    for old, new in edits:
        text = replace_once(text, old, new)
    return text

OUT.mkdir(parents=True)
(OUT / "tmp").mkdir()

def run(label: str, args: list[str], timeout: int = 900) -> None:
    with (OUT / f"{label}.log").open("w") as log:
        subprocess.run(args, cwd=ROOT, env={**ENV, "TMPDIR": str(OUT / "tmp")},
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)

# Compile the exact candidate engine in a fresh directory, with no package
# installation and no network resolver.
engine_dir = OUT / "engine"
engine_dir.mkdir()
shutil.copyfile(STAGE / "engine/build.js", engine_dir / "build.js")
(engine_dir / "MCEntryInterpreter.sol").write_text(candidate_engine)
run("engine-build", ["node", str(engine_dir / "build.js")])
engine_art = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_run = bytes.fromhex(engine_art["deployedBytecode"])
assert len(engine_run) <= 393216, len(engine_run)
assert engine_art["sourceHashes"]["MCEntryInterpreter.sol"] == sha(candidate_engine.encode())
assert engine_art["abi"] == base_engine_art["abi"]
assert engine_art["storageLayout"] == base_engine_art["storageLayout"]

candidate_coord_expected = expected_coord.replace("ENGINEHASH", engine_art["codeHashes"]["runtimeKeccak256"])
assert candidate_coord == candidate_coord_expected, "coordinator codehash pin does not match candidate engine"
coord_dir = OUT / "coordinator"
coord_dir.mkdir()
shutil.copyfile(STAGE / "coordinator/build.js", coord_dir / "build.js")
(coord_dir / "MCEntryCoordinator.sol").write_text(candidate_coord)
run("coordinator-build", ["node", str(coord_dir / "build.js")])
coord_art = json.loads((coord_dir / "MCEntryCoordinator.json").read_text())
coord_run = bytes.fromhex(coord_art["deployedBytecode"])
assert len(coord_run) <= 24576, len(coord_run)
assert coord_art["abi"] == base_coord_art["abi"]
assert coord_art["sourceHashes"]["MCEntryCoordinator.sol"] == sha(candidate_coord.encode())

# Assert the exact compiler storage-layout delta for the enlarged fixed arrays.
def expected_coord_layout(layout: dict) -> dict:
    out = copy.deepcopy(layout)
    slot_updates = {
        "classRoots": "81", "classSizes": "156", "rawNames": "166",
        "seedDecoder": "241", "seedName": "242", "seedRoot": "243", "seedSize": "244",
    }
    array_labels = {"decoders", "classRoots", "classSizes", "rawNames"}
    for row in out["storage"]:
        if row["label"] in array_labels:
            row["type"] = row["type"].replace(")74_storage", ")75_storage")
        if row["label"] in slot_updates:
            row["slot"] = slot_updates[row["label"]]
    for old_key, new_key, label, nbytes in (
        ("t_array(t_address)74_storage", "t_array(t_address)75_storage", "address[75]", "2400"),
        ("t_array(t_bytes32)74_storage", "t_array(t_bytes32)75_storage", "bytes32[75]", "2400"),
        ("t_array(t_uint32)74_storage", "t_array(t_uint32)75_storage", "uint32[75]", "320"),
        ("t_array(t_bytes_storage)74_storage", "t_array(t_bytes_storage)75_storage", "bytes[75]", "2400"),
    ):
        value = out["types"].pop(old_key)
        value["label"] = label
        value["numberOfBytes"] = nbytes
        out["types"][new_key] = value
    return out

expected_layout = expected_coord_layout(base_coord_art["storageLayout"])
assert coord_art["storageLayout"] == expected_layout, "unexpected coordinator storage-layout delta"

driver = driver_source(engine_art, coord_art)
assert "len(m.Decoders) > 75" in driver and "fixtureNamesLimit(75) }" in driver
assert f"len(engineRun) != {len(engine_run)}" in driver and f"len(run) != {len(engine_run)}" in driver
assert f"len(coordRun) != {len(coord_run)}" in driver
assert "MC-RANDOM-CLASS-P27" in driver and "raw76" in driver
(OUT / "driver.go").write_text(driver)
run("gofmt", ["gofmt", "-w", str(OUT / "driver.go")])
run("go-build", ["go", "build", "-trimpath", "-o", str(OUT / "driver"), str(OUT / "driver.go")])
run("go-vet", ["go", "vet", str(OUT / "driver.go")])

engine_record = {"bytes": len(engine_run), **engine_art["codeHashes"]}
coord_record = {"bytes": len(coord_run), **coord_art["codeHashes"]}
pins = {
    "profile": PROFILE,
    "basis": "accepted P27 parent-raw74-byte518516 artifacts",
    "parentProfile": parent_pins["profile"],
    "bootstrapCount": 97,
    "bootstrapRoot": candidate_root,
    "expectedBootstrapRoot": BOOTSTRAP_ROOT,
    "diagnosticClassBound": 172,
    "globalNativeBindings": parent_pins["globalNativeBindings"],
    "stringLocalBinding": parent_pins["stringLocalBinding"],
    "rawLimits": [75, 531965],
    "maxJvmSteps": 65536,
    "maxInternalSteps": 4096,
    "maxConstantPool": 4096,
    "maxTransfer": 4096,
    "maxClassBytes": 262144,
    "maxArrays": 4096,
    "maxArrayElements": 262144,
    "maxObjects": 4096,
    "maxHandles": 8449,
    "maxCheckpointBytes": 1048576,
    "reserve": 25000000,
    "callWatchdogMs": 30000,
    "ordinaryGas": 1000000000,
    "runtimeCap": 393216,
    "maxFrames": 128,
    "exceptionKinds": 14,
    "address": parent_pins["address"],
    "owner": parent_pins["owner"],
    "engine": engine_record,
    "coordinator": coord_record,
    "engineSourceSHA256": sha(candidate_engine.encode()),
    "coordinatorSourceSHA256": sha(candidate_coord.encode()),
    "engineBuildSHA256": sha((STAGE / "engine/build.js").read_bytes()),
    "coordinatorBuildSHA256": sha((STAGE / "coordinator/build.js").read_bytes()),
    "driverTemplateSHA256": DRIVER_TEMPLATE_SHA256,
    "driverSHA256": sha(driver.encode()),
    "diagnosticSourceSHA256": sha(candidate_diag.encode()),
    "parentEngineSourceSHA256": sha(base_engine.encode()),
    "parentCoordinatorSourceSHA256": sha(base_coord.encode()),
    "parentEngineRuntimeSHA256": base_engine_art["codeHashes"]["runtimeSHA256"],
    "parentCoordinatorRuntimeKeccak256": base_coord_art["codeHashes"]["runtimeKeccak256"],
    "orderedBootstrapLeaves": candidate_leaves,
    "storageLayoutSHA256": sha(json.dumps(coord_art["storageLayout"], sort_keys=True, separators=(",", ":")).encode()),
    "sourceInvariants": {
        "P27LabelsRetained": True,
        "all97BootstrapLeavesEqualAcceptedP27": candidate_leaves == base_leaves,
        "noBootstrapImagesAdded": True,
        "rawEnvelopeOnly": True,
        "allOtherRawHeapCheckpointAndBudgetCapsUnchanged": True,
        "engineABIAndStorageLayoutUnchanged": True,
        "coordinatorABIUnchanged": True,
        "coordinatorLayoutOnlyFixedArrayGrowth": True,
    },
}
assert engine_record["bytes"] <= 393216
assert pins["rawLimits"] == [75, 531965] and pins["bootstrapRoot"] == BOOTSTRAP_ROOT
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(OUT / "source-audit.json").write_text(json.dumps({
    "profile": PROFILE,
    "acceptedParentArtifactRoot": str(PARENT),
    "acceptedParentEngineSourceSHA256": sha(base_engine.encode()),
    "acceptedParentCoordinatorSourceSHA256": sha(base_coord.encode()),
    "candidateEngineSourceSHA256": pins["engineSourceSHA256"],
    "candidateCoordinatorSourceSHA256": pins["coordinatorSourceSHA256"],
    "engineChangedLines": ["MAX_RAW_CLASSES 74->75", "MAX_RAW_BYTES 518516->531965", "two matching _configRoot leaves only"],
    "coordinatorChangedLines": ["four fixed raw arrays 74->75", "raw count guard 74->75", "per-class/aggregate bytes 518516->531965", "candidate engine codehash pin"],
    "observerChangedLines": ["normal raw bound 74->75", "raw76 driver/coordinator/engine refusals", "531965 positive/531966 refusal", "MR01 class bound 171->172"],
    "bootstrapCount": 97,
    "bootstrapRoot": candidate_root,
    "bootstrapLeavesEqualParent": candidate_leaves == base_leaves,
    "P27LabelsRetained": True,
    "noHistoricalParentEdit": True,
    "noGlobalNumericReplacement": True,
    "raw76IsExplicitRefusalOnly": True,
    "diagnosticOnlyChange": "class bound 171->172",
    "engineABIUnchanged": engine_art["abi"] == base_engine_art["abi"],
    "engineStorageLayoutUnchanged": engine_art["storageLayout"] == base_engine_art["storageLayout"],
    "coordinatorABIUnchanged": coord_art["abi"] == base_coord_art["abi"],
    "coordinatorStorageLayoutExactExpectedDelta": coord_art["storageLayout"] == expected_layout,
    "coordinatorStorageLayout": coord_art["storageLayout"],
}, indent=2) + "\n")
print(json.dumps({"profile": PROFILE, "rawLimits": pins["rawLimits"], "bootstrapRoot": candidate_root,
                  "engine": engine_record, "coordinator": coord_record,
                  "driverSHA256": pins["driverSHA256"]}, indent=2))
