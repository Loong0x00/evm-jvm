#!/usr/bin/env python3
"""Fresh P19-based build for the scoped MAX_ARRAYS=2048 candidate.

Build and fixture outputs are append-only under the ignored local build/ directory.
No original JAR or Minecraft input is consulted.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PARENT = HERE.parent / "parent-668583cae"
BASE_SOURCE = PARENT / "artifacts/engine/MCEntryInterpreter.sol"
BASE_ENGINE_JSON = PARENT / "artifacts/engine/MCEntryInterpreter.json"
BASE_COORD_SOURCE = PARENT / "artifacts/coordinator/MCEntryCoordinator.sol"
BASE_COORD_BUILD = PARENT / "artifacts/coordinator/build.js"
BASE_ENGINE_BUILD = PARENT / "artifacts/engine/build.js"
BASE_PINS = PARENT / "artifacts/parent-build-pins.json"
DRIVER_TEMPLATE = HERE / "canonical-driver.go.txt"
STAGE_ENGINE = HERE / "engine"
STAGE_COORDINATOR = HERE / "coordinator"

if len(sys.argv) != 2 or not re.fullmatch(r"[0-9]{2}-[a-z0-9-]+", sys.argv[1]):
    raise SystemExit("usage: build.py RUN-ID (for example 01-local-a)")
run_id = sys.argv[1]
build = ROOT / "build" / f"java-diff-mc-max-arrays-2048-build-{run_id}"
fixtures = ROOT / "build" / f"java-diff-mc-max-arrays-2048-fixtures-{run_id}"
assert not build.exists() and not fixtures.exists(), "outputs are append-only"
build.mkdir(parents=True)
(build / "tmp").mkdir()
node_modules = ROOT / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "install compiler dependencies from the local npm cache first"
env = {
    **os.environ,
    "TMPDIR": str(build / "tmp"),
    "NODE_PATH": str(node_modules),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(label, command, timeout=1200):
    with (build / f"{label}.log").open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=ROOT, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=timeout)


def source_root(source: str, domain: str):
    """Recompute the ordered root from all 97 source-derived image/hash leaves."""
    body = source[source.index("    function _bootstrapRoot("):]
    body = body[:body.index("\n    function ", 1)]
    rhs = {int(i): value.strip() for i, value in
           re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(rhs) == set(range(97)), len(rhs)
    pairs = []
    for index in range(97):
        value = rhs[index]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", value)
        if call:
            start = source.index("    function " + call.group(1) + "(")
            function = source[start:]
            function = function[:function.index("\n    function ", 1)]
            leaves = re.findall(r'hex"([0-9a-f]+)"', function)
            assert len(leaves) == 1, (index, call.group(1), len(leaves))
            pairs.append(["image", leaves[0]])
            continue
        assert re.fullmatch(r"DBOOT_[A-Z_]+", value), (index, value)
        expr = re.search(r"bytes32 private constant " + value + r"\s*=\s*([^;]+);", source).group(1).strip()
        assert expr.startswith('hex"') or expr.startswith('keccak256(hex"'), (index, expr)
        leaves = re.findall(r'hex"([0-9a-f]+)"', expr)
        assert len(leaves) == 1
        pairs.append(["hexhash" if expr.startswith('hex"') else "image", leaves[0]])
    script = r'''const a=JSON.parse(require("fs").readFileSync(0,"utf8"));const {keccak256}=require("js-sha3");const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const leaves=a.pairs.map(([t,v])=>t==="image"?keccak256(Buffer.from(v,"hex")):v);const b=Buffer.concat([Buffer.from(keccak256(a.domain),"hex"),w(64),w(leaves.length),...leaves.map(x=>Buffer.from(x,"hex"))]);console.log(JSON.stringify({root:keccak256(b),leaves}));'''
    proc = subprocess.run(["node", "-e", script], cwd=ROOT, env=env,
                          input=json.dumps({"domain": domain, "pairs": pairs}),
                          text=True, capture_output=True, check=True)
    data = json.loads(proc.stdout)
    assert len(data["leaves"]) == 97
    return data

base_source = BASE_SOURCE.read_bytes()
candidate_source = (STAGE_ENGINE / "MCEntryInterpreter.sol").read_bytes()
old_limit = b"uint256 private constant MAX_ARRAYS = 1024;"
new_limit = b"uint256 private constant MAX_ARRAYS = 2048;"
assert base_source.count(old_limit) == 1
assert candidate_source == base_source.replace(old_limit, new_limit, 1), \
    "candidate must differ from accepted P19 only at MAX_ARRAYS=2048"
base_text = base_source.decode("utf-8")
candidate_text = candidate_source.decode("utf-8")
for line in (
    "uint256 private constant MAX_ARRAY_LENGTH = 65536;",
    "uint256 private constant MAX_ARRAY_ELEMENTS = 262144;",
    "uint256 private constant MAX_OBJECTS = 1024;",
):
    assert base_text.count(line) == candidate_text.count(line) == 1, line
assert "uint256 private constant MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS" in candidate_text
assert (STAGE_ENGINE / "build.js").read_bytes() == BASE_ENGINE_BUILD.read_bytes()

pins0 = json.loads(BASE_PINS.read_text())
assert pins0["basis"] == "668583cae"
assert pins0["bootstrapCount"] == 97
root = source_root(candidate_text, "JVMEVM:MC-RANDOM-CLASS-P19:BOOTSTRAP:1")
assert root["root"] == pins0["bootstrapRoot"] == pins0["expectedBootstrapRoot"]

# Compile only the candidate Solidity source using the accepted pinned builder.
engine_dir = build / "engine"
engine_dir.mkdir()
shutil.copy2(STAGE_ENGINE / "MCEntryInterpreter.sol", engine_dir / "MCEntryInterpreter.sol")
shutil.copy2(STAGE_ENGINE / "build.js", engine_dir / "build.js")
run("engine-build", ["node", engine_dir / "build.js"])
engine_artifact = json.loads((engine_dir / "MCEntryInterpreter.json").read_text())
engine_bytes = len(engine_artifact["deployedBytecode"]) // 2
assert engine_bytes <= pins0["runtimeCap"] == 393216
base_artifact = json.loads(BASE_ENGINE_JSON.read_text())
assert engine_artifact["abi"] == base_artifact["abi"]
assert engine_artifact["storageLayout"] == base_artifact["storageLayout"]

# P19 coordinator changes only its immutable codehash pin to the candidate runtime.
coordinator_dir = build / "coordinator"
coordinator_dir.mkdir()
coordinator_base = BASE_COORD_SOURCE.read_text()
old_keccak = pins0["engine"]["runtimeKeccak256"]
new_keccak = engine_artifact["codeHashes"]["runtimeKeccak256"]
old_literal = f'bytes32 private constant ENGINE_CODEHASH = hex"{old_keccak}";'
new_literal = f'bytes32 private constant ENGINE_CODEHASH = hex"{new_keccak}";'
assert coordinator_base.count(old_literal) == 1
coordinator_candidate = coordinator_base.replace(old_literal, new_literal, 1)
shutil.copy2(BASE_COORD_BUILD, coordinator_dir / "build.js")
(coordinator_dir / "MCEntryCoordinator.sol").write_text(coordinator_candidate)
run("coordinator-build", ["node", coordinator_dir / "build.js"])
coordinator_artifact = json.loads((coordinator_dir / "MCEntryCoordinator.json").read_text())
assert coordinator_artifact["abi"] == json.loads((PARENT / "artifacts/coordinator/MCEntryCoordinator.json").read_text())["abi"]
assert len(coordinator_artifact["deployedBytecode"]) // 2 <= 24576

# Build the reviewed canonical P19 generated-only EVM driver with exact new pins.
driver = DRIVER_TEMPLATE.read_text()
assert DRIVER_TEMPLATE.read_bytes() == (PARENT / "canonical-driver.go.txt").read_bytes()
replacements = {
    f'const immutableEngineSHA256 = "{pins0["engine"]["runtimeSHA256"]}"':
        f'const immutableEngineSHA256 = "{engine_artifact["codeHashes"]["runtimeSHA256"]}"',
    f'const immutableEngineKeccak = "0x{pins0["engine"]["runtimeKeccak256"]}"':
        f'const immutableEngineKeccak = "0x{engine_artifact["codeHashes"]["runtimeKeccak256"]}"',
    f'const immutableCoordinatorKeccak = "0x{pins0["coordinator"]["runtimeKeccak256"]}"':
        f'const immutableCoordinatorKeccak = "0x{coordinator_artifact["codeHashes"]["runtimeKeccak256"]}"',
}
for old, new in replacements.items():
    assert driver.count(old) == 1, old
    driver = driver.replace(old, new, 1)
for label, old_size, new_size in (
    ("engineRun", pins0["engine"]["bytes"], engine_bytes),
    ("run", pins0["engine"]["bytes"], engine_bytes),
    ("coordRun", pins0["coordinator"]["bytes"], len(coordinator_artifact["deployedBytecode"]) // 2),
):
    old = f"len({label}) != {old_size}"
    assert driver.count(old) == 1, (label, old, driver.count(old))
    driver = driver.replace(old, f"len({label}) != {new_size}", 1)
main_go = build / "main.go"
main_go.write_text(driver)
run("driver-gofmt", ["gofmt", "-w", main_go])
run("driver-build", ["go", "build", "-trimpath", "-o", build / "driver", main_go])
run("driver-vet", ["go", "vet", main_go])
assert (build / "driver").is_file()

pins = dict(pins0)
pins.update({
    "profile": "MC-RANDOM-CLASS-P19-MAX-ARRAYS-2048",
    "basis": "accepted 668583cae P19; only MAX_ARRAYS 1024->2048",
    "worker": "parent",
    "buildID": run_id,
    "sourceSHA256": sha(candidate_source),
    "acceptedP19SourceSHA256": sha(base_source),
    "bootstrapRoot": root["root"],
    "maxArrays": 2048,
    "maxHandles": 2048 + pins0["ordinaryObjectsLimit"] + 256 + 1
        if "ordinaryObjectsLimit" in pins0 else 2048 + 1024 + 256 + 1,
    "engine": {"bytes": engine_bytes, **engine_artifact["codeHashes"]},
    "coordinator": {"bytes": len(coordinator_artifact["deployedBytecode"]) // 2,
                    **coordinator_artifact["codeHashes"]},
    "driverSHA256": sha(main_go.read_bytes()),
})
# Keep the opaque machine/root profile untouched and assert all non-target heap caps.
assert pins["runtimeCap"] == 393216
assert pins["maxHandles"] == 3329
(build / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(build / "root-audit.json").write_text(json.dumps({
    "domain": "JVMEVM:MC-RANDOM-CLASS-P19:BOOTSTRAP:1",
    "orderedLeaves": 97,
    "bootstrapRoot": root["root"],
    "leaves": root["leaves"],
}, indent=2) + "\n")
(build / "source-audit.json").write_text(json.dumps({
    "baseline": "parent-668583cae/artifacts/engine/MCEntryInterpreter.sol",
    "baselineSHA256": sha(base_source),
    "candidate": "max-arrays-2048/engine/MCEntryInterpreter.sol",
    "candidateSHA256": sha(candidate_source),
    "onlyChangedSource": "uint256 private constant MAX_ARRAYS = 1024; -> 2048;",
    "exactOneLineDelta": True,
    "MAX_HANDLES": "derived from MAX_ARRAYS + unchanged MAX_OBJECTS + reserved exception handles",
    "MAX_OBJECTS": 1024,
    "MAX_ARRAY_LENGTH": 65536,
    "MAX_ARRAY_ELEMENTS": 262144,
    "abiUnchanged": True,
    "storageLayoutUnchanged": True,
}, indent=2) + "\n")

# Reuse the checked-in, generated-only P19 corpus and its generated Java-8 tail cases.
run("generated-fixture-build", [sys.executable, "-B", HERE / "generate_retained_fixtures.py", fixtures])
print(json.dumps({"build": str(build), "fixtures": str(fixtures),
                  "runtimeBytes": engine_bytes, "runtimeSHA256": engine_artifact["codeHashes"]["runtimeSHA256"],
                  "coordinatorBytes": pins["coordinator"]["bytes"],
                  "bootstrapRoot": root["root"], "maxArrays": pins["maxArrays"],
                  "maxHandles": pins["maxHandles"]}, indent=2))
