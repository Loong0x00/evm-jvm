#!/usr/bin/env python3
"""Exact P26 raw73->raw74 envelope audit and pinned offline build."""
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
PARENT = ROOT / "evidence/java-evm/minecraft-entry/parent-raw73-byte516040"
ART = PARENT / "artifacts"
PROFILE = "MC-RANDOM-CLASS-P26-RAW74-BYTE518516"
BOOTSTRAP_ROOT = "9badb7b2e5fd2990b0285dcad078f36955841cc091e7f2eeb07f8401fbfb694d"
TEMPLATE_SHA256 = "d2af8782e725ea33111d4676e0a156039c0e3718ba85aee4deee45a2515a9af0"
if len(sys.argv) != 2:
    raise SystemExit("usage: build.py build/java-diff-mc-raw74-byte518516-build-TAG")
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-raw74-byte518516-build-")
assert not OUT.exists(), "build outputs are append-only"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    n = text.count(old)
    assert n == 1, (old[:120], n)
    return text.replace(old, new, 1)


base_pins = json.loads((ART / "parent-build-pins.json").read_text())
base_engine_path = ART / "engine/MCEntryInterpreter.sol"
base_coord_path = ART / "coordinator/MCEntryCoordinator.sol"
base_engine = base_engine_path.read_text()
base_coord = base_coord_path.read_text()
base_engine_art = json.loads((ART / "engine/MCEntryInterpreter.json").read_text())
base_coord_art = json.loads((ART / "coordinator/MCEntryCoordinator.json").read_text())
assert base_pins["profile"] == "MC-RANDOM-CLASS-P26-RAW73-BYTE516040"
assert base_pins["bootstrapCount"] == 97 and base_pins["bootstrapRoot"] == BOOTSTRAP_ROOT
assert base_engine_art["sourceHashes"]["MCEntryInterpreter.sol"] == sha(base_engine.encode())
assert base_coord_art["sourceHashes"]["MCEntryCoordinator.sol"] == sha(base_coord.encode())
assert base_engine_art["codeHashes"]["runtimeSHA256"] == base_pins["engine"]["runtimeSHA256"]
assert base_engine_art["codeHashes"]["runtimeKeccak256"] == base_pins["engine"]["runtimeKeccak256"]
assert base_coord_art["codeHashes"]["runtimeSHA256"] == base_pins["coordinator"]["runtimeSHA256"]
assert base_coord_art["codeHashes"]["runtimeKeccak256"] == base_pins["coordinator"]["runtimeKeccak256"]

# The candidate engine must equal this accepted P26 source after only two raw
# constants and the two matching leaves in _configRoot are changed.
expected_engine = base_engine
for old, new in (
    ("uint256 private constant MAX_RAW_CLASSES = 73;", "uint256 private constant MAX_RAW_CLASSES = 74;"),
    ("uint256 private constant MAX_RAW_BYTES = 516040;", "uint256 private constant MAX_RAW_BYTES = 518516;"),
    ("            uint32(73), uint32(516040), uint32(64), uint32(32), uint32(65536),",
     "            uint32(74), uint32(518516), uint32(64), uint32(32), uint32(65536),"),
):
    expected_engine = replace_once(expected_engine, old, new)
candidate_engine = (STAGE / "engine/MCEntryInterpreter.sol").read_text()
assert candidate_engine == expected_engine, "engine has changes outside the raw74 envelope"
assert "MC-RANDOM-CLASS-P26" in candidate_engine and "MC-RANDOM-CLASS-P25" not in candidate_engine
for invariant in (
    "uint256 private constant MAX_CONSTANT_POOL = 4096;",
    "uint256 private constant MAX_ARRAYS = 4096;",
    "uint256 private constant MAX_ARRAY_ELEMENTS = 262144;",
    "uint256 private constant MAX_OBJECTS = 4096;",
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint32 private constant MAX_TRANSFER = 4096;",
    "uint32(74), uint32(518516), uint32(64), uint32(32), uint32(65536),",
    "if (jvm == 0 || jvm > 65536 || internalSteps == 0 || internalSteps > 4096)",
    "uint256 private constant COMMIT_RESERVE = 25_000_000;",
):
    assert invariant in candidate_engine, invariant

# The coordinator changes only its four count-indexed storage arrays, count and
# aggregate/per-class byte guards, plus the compiled engine codehash pin.
normalize_hash = lambda text: re.sub(
    r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',
    r'\g<1>ENGINEHASH\g<2>', text)
expected_coord = normalize_hash(base_coord)
for old, new in (
    ("address[73] private decoders;", "address[74] private decoders;"),
    ("bytes32[73] private classRoots;", "bytes32[74] private classRoots;"),
    ("uint32[73] private classSizes;", "uint32[74] private classSizes;"),
    ("bytes[73] private rawNames;", "bytes[74] private rawNames;"),
    ("n == 0 || n > 73 || fixedRawNames.length != n ||",
     "n == 0 || n > 74 || fixedRawNames.length != n ||"),
    ("if (size == 0 || size > 516040) revert MR0Error(11);",
     "if (size == 0 || size > 518516) revert MR0Error(11);"),
    ("if (uint256(total) + size > 516040) revert MR0Error(12);",
     "if (uint256(total) + size > 518516) revert MR0Error(12);"),
):
    expected_coord = replace_once(expected_coord, old, new)
coord_with_marker = normalize_hash((STAGE / "coordinator/MCEntryCoordinator.sol").read_text())
assert coord_with_marker == expected_coord, "coordinator has changes outside raw count/bytes and codehash"
assert "MC-RANDOM-CLASS-P26" in (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()

# Freeze the accepted local compiler scripts byte-for-byte; no npm install or
# network access is permitted by the stage environment.
for name in ("engine", "coordinator"):
    candidate_build = STAGE / name / "build.js"
    parent_build = ART / name / "build.js"
    assert candidate_build.read_bytes() == parent_build.read_bytes()
    expected_hash = base_pins["sourceHashes"][name + "Build"]
    assert sha(candidate_build.read_bytes()) == expected_hash

# Independently compute all ordered image leaves, not merely a source-name grep.
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
                            input=json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P26:BOOTSTRAP:1", "pairs": pairs}),
                            text=True, capture_output=True, check=True, timeout=120)
    parsed = json.loads(result.stdout)
    return parsed["root"], parsed["leaves"]

ENV = {
    **os.environ,
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "npm_config_offline": "true",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GOTOOLCHAIN": "local",
    "PYTHONDONTWRITEBYTECODE": "1",
}
base_root, base_leaves = bootstrap_root(base_engine)
candidate_root, candidate_leaves = bootstrap_root(candidate_engine)
assert base_root == BOOTSTRAP_ROOT and candidate_root == base_root and candidate_leaves == base_leaves

# Retain the exact frozen MR01 observer except its class-count ceiling 170->171.
diag_path = STAGE / "tools/checkpoint_diagnostic.py"
candidate_diag = diag_path.read_text()
parent_diag = replace_once(candidate_diag, "assert classes <= 171", "assert classes <= 170")
assert sha(parent_diag.encode()) == "b6917dbc742adc6c025c6664942576623bddd9a43e0c28015c304bff8b75f9e8"
expected_diag = replace_once(parent_diag, "assert classes <= 170", "assert classes <= 171")
assert candidate_diag == expected_diag

OUT.mkdir(parents=True)
(OUT / "tmp").mkdir()

def run(label: str, args: list[str], timeout: int = 900) -> None:
    with (OUT / f"{label}.log").open("w") as log:
        subprocess.run(args, cwd=ROOT, env={**ENV, "TMPDIR": str(OUT / "tmp")},
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)

# Build exact scoped Solidity in an isolated fresh output directory.
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

candidate_coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
coord_expected = expected_coord.replace("ENGINEHASH", engine_art["codeHashes"]["runtimeKeccak256"])
assert candidate_coord == coord_expected, "coordinator engine hash pin does not match candidate engine"
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

# Generate the observer from the accepted P26 parent template by explicit edits;
# this prevents profile-wide numeric replacement, including bootstrap slots.
template_path = PARENT / "generated-probe-driver.go.txt"
template = template_path.read_text()
assert sha(template.encode()) == TEMPLATE_SHA256

def driver_source(engine_artifact: dict, coord_artifact: dict) -> str:
    text = template
    edits = (
        ("len(m.Decoders) > 73", "len(m.Decoders) > 74"),
        ("func fixtureNames() [][]byte { return fixtureNamesLimit(73) }",
         "func fixtureNames() [][]byte { return fixtureNamesLimit(74) }"),
        ("reach the coordinator/engine's own raw74 guards. Normal driver paths stay at73.",
         "reach the coordinator/engine's own raw75 guards. Normal driver paths stay at74."),
        ('''case "raw74":
\t\tnames := fixtureNamesLimit(74)
\t\tif len(names) != 74 {
\t\t\tpanic("raw74 engine probe requires74 bindings")
\t\t}
\t\tclasses = rawFixtureClasses(zipPath, names)
\t\twantName, wantCode, wantDetail = "LinkError", 1, 74
\tcase "bytes516041":
\t\tclasses = rawFixtureClasses(zipPath, fixtureNamesLimit(73))
\t\twantName, wantCode, wantDetail = "LinkError", 1, 516041''',
         '''case "raw75":
\t\tnames := fixtureNamesLimit(75)
\t\tif len(names) != 75 {
\t\t\tpanic("raw75 engine probe requires75 bindings")
\t\t}
\t\tclasses = rawFixtureClasses(zipPath, names)
\t\twantName, wantCode, wantDetail = "LinkError", 1, 75
\tcase "bytes518517":
\t\tclasses = rawFixtureClasses(zipPath, fixtureNamesLimit(74))
\t\twantName, wantCode, wantDetail = "LinkError", 1, 518517'''),
        ('''names := fixtureNamesLimit(73)
\tif len(names) != 73 {
\t\tpanic("direct engine start requires73 bindings")''',
         '''names := fixtureNamesLimit(74)
\tif len(names) != 74 {
\t\tpanic("direct engine start requires74 bindings")'''),
        ('''func boundaryRaw74(dir, artPath, zipPath string) {
\tnames := fixtureNamesLimit(74)
\tif len(names) != 74 {
\t\tpanic("raw74 coordinator probe requires74 bindings")
\t}
\te, err := newEnv(dir)
\tmust(err)
\tdefer e.close()
\tinstallEngine(e)
\traw, err := os.ReadFile(zipPath)
\tmust(err)
\tsetupResources(e, raw, names, selectedResourceName(), true)
\tart, ca, init, run := loadArtifact(artPath)
\tbefore := e.root
\t_, _, r := deployCoordinator(e, art, ca, init, run, e.m.Decoders, names, e.m.ResourceRoots, e.m.Sizes,
\t\te.m.SeedDecoder, e.m.SeedName, e.m.SelectedRoot, e.m.SeedSize, nil, owner)
\tif r.Err == nil || errorName(ca, r.Out) != "MR0Error" || len(r.Out) != 36 ||
\t\tnew(big.Int).SetBytes(r.Out[4:]).Uint64() != 2 || e.root != before {
\t\tpanic(fmt.Sprintf("coordinator raw74 refusal: err=%v name=%s data=0x%x rootSame=%t", r.Err, errorName(ca, r.Out), r.Out, e.root == before))
\t}
\twriteFailureReceipt(dir, "coordinator-raw74.json", r, before, e.root)
}''',
         '''func boundaryRaw75(dir, artPath, zipPath string) {
\tnames := fixtureNamesLimit(75)
\tif len(names) != 75 {
\t\tpanic("raw75 coordinator probe requires75 bindings")
\t}
\te, err := newEnv(dir)
\tmust(err)
\tdefer e.close()
\tinstallEngine(e)
\traw, err := os.ReadFile(zipPath)
\tmust(err)
\tsetupResources(e, raw, names, selectedResourceName(), true)
\tart, ca, init, run := loadArtifact(artPath)
\tbefore := e.root
\t_, _, r := deployCoordinator(e, art, ca, init, run, e.m.Decoders, names, e.m.ResourceRoots, e.m.Sizes,
\t\te.m.SeedDecoder, e.m.SeedName, e.m.SelectedRoot, e.m.SeedSize, nil, owner)
\tif r.Err == nil || errorName(ca, r.Out) != "MR0Error" || len(r.Out) != 36 ||
\t\tnew(big.Int).SetBytes(r.Out[4:]).Uint64() != 2 || e.root != before {
\t\tpanic(fmt.Sprintf("coordinator raw75 refusal: err=%v name=%s data=0x%x rootSame=%t", r.Err, errorName(ca, r.Out), r.Out, e.root == before))
\t}
\twriteFailureReceipt(dir, "coordinator-raw75.json", r, before, e.root)
}'''),
        ('''names := fixtureNamesLimit(73)
\tif len(names) != 73 {
\t\tpanic("byte boundary requires73 bindings")''',
         '''names := fixtureNamesLimit(74)
\tif len(names) != 74 {
\t\tpanic("byte boundary requires74 bindings")'''),
        ("expected == 516040", "expected == 518516"),
        ("coordinator-byte-516040.json", "coordinator-byte-518516.json"),
        ('"probe": "coordinator-byte-516040"', '"probe": "coordinator-byte-518516"'),
        ("expected == 516041", "expected == 518517"),
        ("coordinator-byte-516041.json", "coordinator-byte-518517.json"),
        ('case "boundary-raw74":\n\t\tboundaryRaw74(os.Args[2], os.Args[3], os.Args[5])',
         'case "boundary-raw75":\n\t\tboundaryRaw75(os.Args[2], os.Args[3], os.Args[5])'),
        ("total != 516040 && total != 516041", "total != 518516 && total != 518517"),
        ('"engine-byte-516040", 65536, 516040', '"engine-byte-518516", 65536, 518516'),
        ('"engine-direct-raw73", q, 0', '"engine-direct-raw74", q, 0'),
        ("len(engineRun) != 392091", f"len(engineRun) != {len(engine_run)}"),
        ("len(coordRun) != 5394", f"len(coordRun) != {len(coord_run)}"),
        ("len(run) != 392091", f"len(run) != {len(engine_run)}"),
        ("const immutableEngineSHA256 = \"62b79dc12927e0c0863c14388d8537afc7c7c2d777f075efc01e8147b5a450ea\"",
         f"const immutableEngineSHA256 = \"{engine_artifact['codeHashes']['runtimeSHA256']}\""),
        ("const immutableEngineKeccak = \"0x0db1c02c4d79b63f683a3997a6e0ee021bbb4230447f5331303af234406eb975\"",
         f"const immutableEngineKeccak = \"0x{engine_artifact['codeHashes']['runtimeKeccak256']}\""),
        ("const immutableCoordinatorKeccak = \"0x8c31f2c573d595c7953ff6a2f752d54e440f237042bd5f1e601becd83785fb49\"",
         f"const immutableCoordinatorKeccak = \"0x{coord_artifact['codeHashes']['runtimeKeccak256']}\""),
    )
    for old, new in edits:
        text = replace_once(text, old, new)
    return text


driver = driver_source(engine_art, coord_art)
assert "len(m.Decoders) > 74" in driver and "fixtureNamesLimit(74) }" in driver
assert f"len(engineRun) != {len(engine_run)}" in driver and f"len(run) != {len(engine_run)}" in driver
assert f"len(coordRun) != {len(coord_run)}" in driver
assert "MC-RANDOM-CLASS-P26" in driver and "MC-RANDOM-CLASS-P25" not in driver
(OUT / "driver.go").write_text(driver)
run("gofmt", ["gofmt", "-w", str(OUT / "driver.go")])
run("go-build", ["go", "build", "-trimpath", "-o", str(OUT / "driver"), str(OUT / "driver.go")])
run("go-vet", ["go", "vet", str(OUT / "driver.go")])

# Source/build pins and explicit scope audit.
engine_record = {"bytes": len(engine_run), **engine_art["codeHashes"]}
coord_record = {"bytes": len(coord_run), **coord_art["codeHashes"]}
pins = {
    "profile": PROFILE,
    "basis": "accepted P26 parent-raw73-byte516040 artifacts",
    "parentProfile": base_pins["profile"],
    "bootstrapCount": 97,
    "bootstrapRoot": candidate_root,
    "expectedBootstrapRoot": BOOTSTRAP_ROOT,
    "diagnosticClassBound": 171,
    "globalNativeBindings": base_pins["globalNativeBindings"],
    "stringLocalBinding": base_pins["stringLocalBinding"],
    "rawLimits": [74, 518516],
    "maxJvmSteps": 65536,
    "maxInternalSteps": 4096,
    "maxConstantPool": 4096,
    "maxTransfer": 4096,
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
    "address": base_pins["address"],
    "owner": base_pins["owner"],
    "engine": engine_record,
    "coordinator": coord_record,
    "engineSourceSHA256": sha(candidate_engine.encode()),
    "coordinatorSourceSHA256": sha(candidate_coord.encode()),
    "engineBuildSHA256": sha((STAGE / "engine/build.js").read_bytes()),
    "coordinatorBuildSHA256": sha((STAGE / "coordinator/build.js").read_bytes()),
    "driverSHA256": sha(driver.encode()),
    "diagnosticSourceSHA256": sha(expected_diag.encode()),
    "parentEngineSourceSHA256": sha(base_engine.encode()),
    "parentCoordinatorSourceSHA256": sha(base_coord.encode()),
    "parentEngineRuntimeSHA256": base_engine_art["codeHashes"]["runtimeSHA256"],
    "parentCoordinatorRuntimeKeccak256": base_coord_art["codeHashes"]["runtimeKeccak256"],
    "orderedBootstrapLeaves": candidate_leaves,
    "sourceInvariants": {
        "P26LabelsRetained": True,
        "all97BootstrapLeavesEqualAcceptedP26": candidate_leaves == base_leaves,
        "noBootstrapImagesAdded": True,
        "rawEnvelopeOnly": True,
        "allOtherRawHeapCheckpointAndBudgetCapsUnchanged": True,
    },
    "normalizedChanges": {
        "engine": ["MAX_RAW_CLASSES 73->74", "MAX_RAW_BYTES 516040->518516", "two matching _configRoot leaves only"],
        "coordinator": ["four fixed arrays 73->74", "count guard 73->74", "per-class/aggregate bytes 516040->518516", "candidate engine codehash pin"],
        "observer": ["normal raw bound 73->74", "raw75 driver/coordinator/engine refusals", "518516 positive/518517 refusal", "MR01 class bound 170->171"],
    },
}
assert engine_record["bytes"] <= 393216
assert pins["rawLimits"] == [74, 518516] and pins["bootstrapRoot"] == BOOTSTRAP_ROOT
(OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(OUT / "source-audit.json").write_text(json.dumps({
    "profile": PROFILE,
    "acceptedParentArtifactRoot": str(PARENT),
    "acceptedParentEngineSourceSHA256": sha(base_engine.encode()),
    "acceptedParentCoordinatorSourceSHA256": sha(base_coord.encode()),
    "candidateEngineSourceSHA256": pins["engineSourceSHA256"],
    "candidateCoordinatorSourceSHA256": pins["coordinatorSourceSHA256"],
    "engineChangedLines": ["MAX_RAW_CLASSES", "MAX_RAW_BYTES", "_configRoot raw count/bytes"],
    "coordinatorChangedLines": ["four fixed raw arrays", "raw count/byte guards", "engine codehash pin"],
    "bootstrapCount": 97,
    "bootstrapRoot": candidate_root,
    "bootstrapLeavesEqualParent": candidate_leaves == base_leaves,
    "P26LabelsRetained": True,
    "noHistoricalParentEdit": True,
    "noGlobalNumericReplacement": True,
    "raw75IsExplicitRefusalOnly": True,
    "diagnosticOnlyChange": "class bound 170->171",
}, indent=2) + "\n")
print(json.dumps({"profile": PROFILE, "rawLimits": pins["rawLimits"], "bootstrapRoot": candidate_root,
                  "engine": engine_record, "coordinator": coord_record,
                  "driverSHA256": pins["driverSHA256"]}, indent=2))
