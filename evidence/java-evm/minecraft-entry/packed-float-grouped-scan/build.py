#!/usr/bin/env python3
"""Fresh same-P18 generated-only build for the grouped float validation scan."""
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
TARGET = "evidence/java-evm/minecraft-entry/parent-e23eea569/artifacts/engine/MCEntryInterpreter.sol"
PARENT = ROOT / "evidence/java-evm/minecraft-entry/parent-e23eea569"
PINS = json.loads((PARENT / "artifacts/parent-build-pins.json").read_text())

if len(sys.argv) != 2:
    raise SystemExit("usage: build.py RUN-ID (e.g. 01-local-a)")
run_id = sys.argv[1]
if not re.fullmatch(r"[0-9]{2}-[a-z0-9-]+", run_id):
    raise SystemExit("RUN-ID must be [0-9]{2}-[a-z0-9-]+")

BUILD = ROOT / "build" / ("java-diff-mc-packed-float-bulk-u32-build-" + run_id)
FIXTURES = ROOT / "build" / ("java-diff-mc-packed-float-bulk-u32-fixtures-" + run_id)
assert not BUILD.exists() and not FIXTURES.exists(), "build outputs are append-only"
BUILD.mkdir(parents=True)
(BUILD / "tmp").mkdir()
NODE_MODULES = ROOT / "jvmevm/runtime/node_modules"
assert NODE_MODULES.is_dir(), "compiler dependencies must come from the local npm cache"
ENV = {
    **os.environ,
    "TMPDIR": str(BUILD / "tmp"),
    "NODE_PATH": str(NODE_MODULES),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}


def run(label, command, timeout=1200):
    log = BUILD / (label + ".log")
    with log.open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=ROOT, env=ENV,
                       stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function_bodies(source):
    starts = list(re.finditer(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(", source))
    found = {}
    for match in starts:
        opening = source.find("{", match.end())
        depth = 0
        quote = None
        line_comment = block_comment = escape = False
        i = opening
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
                if escape: escape = False
                elif ch == "\\": escape = True
                elif ch == quote: quote = None
            elif ch == "/" and nxt == "/":
                line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                block_comment = True
                i += 1
            elif ch in ('"', "'"):
                quote = ch
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    found.setdefault(match.group(1), []).append(source[match.start():i + 1])
                    break
            i += 1
        assert depth == 0, match.group(1)
    return found


def bootstrap_pairs(source):
    start = source.index("    function _bootstrapRoot(")
    body = source[start:]
    body = body[:body.index("\n    function ", 1)]
    rows = {int(i): rhs.strip() for i, rhs in
            re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(rows) == set(range(97)), (len(rows), sorted(rows))
    pairs = []
    for i in range(97):
        rhs = rows[i]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
        if call:
            start = source.index("    function " + call.group(1) + "(")
            fn = source[start:]
            fn = fn[:fn.index("\n    function ", 1)]
            data = re.findall(r'hex"([0-9a-f]+)"', fn)
            assert len(data) == 1, (i, call.group(1), len(data))
            pairs.append(["image", data[0]])
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", rhs), (i, rhs)
            expr = re.search(r"bytes32 private constant " + re.escape(rhs) + r"\s*=\s*([^;]+);", source).group(1).strip()
            data = re.findall(r'hex"([0-9a-f]+)"', expr)
            assert len(data) == 1, (i, rhs)
            pairs.append(["image" if expr.startswith("keccak256(") else "hexhash", data[0]])
    return pairs


# Reconstruct the exact accepted P18 source from the assigned starting commit,
# not a newer artifact, and prove only the requested helper function changed.
baseline_source = subprocess.run(
    ["git", "show", "f867e6279:" + TARGET], cwd=ROOT,
    env=ENV, text=True, capture_output=True, check=True,
).stdout
candidate_source = (ROOT / TARGET).read_text()
base_functions = function_bodies(baseline_source)
candidate_functions = function_bodies(candidate_source)
assert base_functions.keys() == candidate_functions.keys()
changed = sorted(name for name in base_functions
                 if base_functions[name] != candidate_functions[name])
assert changed == ["_checkpointArrayNonzeroCount"], changed
for name in base_functions:
    if name != "_checkpointArrayNonzeroCount":
        assert base_functions[name] == candidate_functions[name], name

# Independently recompute all 97 ordered bootstrap leaves and the P18 root for
# both byte sources. This code uses only the pinned local js-sha3 package.
base_pairs = bootstrap_pairs(baseline_source)
candidate_pairs = bootstrap_pairs(candidate_source)
assert base_pairs == candidate_pairs
node = r'''const a=JSON.parse(require("fs").readFileSync(0,"utf8"));const {keccak256}=require("js-sha3");const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const leaves=a.pairs.map(([t,v])=>t==="image"?keccak256(Buffer.from(v,"hex")):v);const encoded=Buffer.concat([Buffer.from(keccak256(a.domain),"hex"),w(64),w(leaves.length),...leaves.map(x=>Buffer.from(x,"hex"))]);console.log(JSON.stringify({root:keccak256(encoded),leaves}));'''
root_data = json.loads(subprocess.run(
    ["node", "-e", node], cwd=ROOT, env=ENV,
    input=json.dumps({"pairs": candidate_pairs,
                      "domain": "JVMEVM:MC-RANDOM-CLASS-P18:BOOTSTRAP:1"}),
    text=True, capture_output=True, check=True,
).stdout)
assert root_data["root"] == PINS["bootstrapRoot"]
assert len(root_data["leaves"]) == PINS["bootstrapCount"] == 97

# Compile exact pre-scan and grouped-scan engines independently.
for label, source in (("baseline", baseline_source), ("candidate", candidate_source)):
    directory = BUILD / label / "engine"
    directory.mkdir(parents=True)
    (directory / "MCEntryInterpreter.sol").write_text(source)
    shutil.copy2(PARENT / "artifacts/engine/build.js", directory / "build.js")
    run(label + "-engine-build", ["node", directory / "build.js"])

base_engine_artifact = json.loads((BUILD / "baseline/engine/MCEntryInterpreter.json").read_text())
candidate_engine_artifact = json.loads((BUILD / "candidate/engine/MCEntryInterpreter.json").read_text())
base_engine_bytes = len(base_engine_artifact["deployedBytecode"]) // 2
candidate_engine_bytes = len(candidate_engine_artifact["deployedBytecode"]) // 2
base_engine = {"bytes": base_engine_bytes, **base_engine_artifact["codeHashes"]}
candidate_engine = {"bytes": candidate_engine_bytes, **candidate_engine_artifact["codeHashes"]}
assert base_engine == PINS["engine"], (base_engine, PINS["engine"])
assert candidate_engine_bytes <= PINS["runtimeCap"] == 393216, candidate_engine
assert candidate_engine_artifact["abi"] == base_engine_artifact["abi"]
assert candidate_engine_artifact["storageLayout"] == base_engine_artifact["storageLayout"]

# Compile the pinned P18 coordinator baseline and a candidate with only its
# immutable engine-codehash pin changed.
base_coord_source = (PARENT / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
base_coord_build = PARENT / "artifacts/coordinator/build.js"
for label, source, engine in (("baseline", base_coord_source, base_engine),
                              ("candidate", None, candidate_engine)):
    if label == "candidate":
        old = 'hex"' + base_engine["runtimeKeccak256"] + '"'
        assert base_coord_source.count(old) == 1
        source = base_coord_source.replace(old, 'hex"' + engine["runtimeKeccak256"] + '"', 1)
    directory = BUILD / label / "coordinator"
    directory.mkdir(parents=True)
    (directory / "MCEntryCoordinator.sol").write_text(source)
    shutil.copy2(base_coord_build, directory / "build.js")
    run(label + "-coordinator-build", ["node", directory / "build.js"])

base_coord_artifact = json.loads((BUILD / "baseline/coordinator/MCEntryCoordinator.json").read_text())
candidate_coord_artifact = json.loads((BUILD / "candidate/coordinator/MCEntryCoordinator.json").read_text())
base_coord = {"bytes": len(base_coord_artifact["deployedBytecode"]) // 2,
              **base_coord_artifact["codeHashes"]}
candidate_coord = {"bytes": len(candidate_coord_artifact["deployedBytecode"]) // 2,
                   **candidate_coord_artifact["codeHashes"]}
assert base_coord == PINS["coordinator"], (base_coord, PINS["coordinator"])
assert base_coord_artifact["abi"] == candidate_coord_artifact["abi"]

# Build immutable-code-pinned generated-test drivers from the reviewed P18
# canonical driver. The baseline driver remains byte-identical to its artifact.
driver_source = (PARENT / "canonical-driver.go.txt").read_text()
assert PINS["engine"]["runtimeSHA256"] in driver_source
assert "0x" + PINS["engine"]["runtimeKeccak256"] in driver_source
assert "0x" + PINS["coordinator"]["runtimeKeccak256"] in driver_source

for label, engine, coordinator in (("baseline", base_engine, base_coord),
                                   ("candidate", candidate_engine, candidate_coord)):
    text = driver_source
    if label == "candidate":
        swaps = [
            (PINS["engine"]["runtimeSHA256"], engine["runtimeSHA256"]),
            ("0x" + PINS["engine"]["runtimeKeccak256"], "0x" + engine["runtimeKeccak256"]),
            ("0x" + PINS["coordinator"]["runtimeKeccak256"], "0x" + coordinator["runtimeKeccak256"]),
            ("len(engineRun) != %d" % PINS["engine"]["bytes"],
             "len(engineRun) != %d" % engine["bytes"]),
            ("len(run) != %d" % PINS["engine"]["bytes"],
             "len(run) != %d" % engine["bytes"]),
            ("len(coordRun) != %d" % PINS["coordinator"]["bytes"],
             "len(coordRun) != %d" % coordinator["bytes"]),
        ]
        for old, new in swaps:
            assert text.count(old) == 1, (old, text.count(old))
            text = text.replace(old, new, 1)
    source_path = BUILD / (label + "-driver.go")
    source_path.write_text(text)
    run(label + "-driver-gofmt", ["gofmt", "-w", source_path])
    run(label + "-driver-build", ["go", "build", "-trimpath", "-o",
                                  BUILD / (label + "-driver"), source_path])
    run(label + "-driver-vet", ["go", "vet", source_path])

shutil.copy2(BUILD / "candidate-driver", BUILD / "driver")
shutil.copy2(BUILD / "candidate-driver.go", BUILD / "main.go")
shutil.copytree(BUILD / "candidate/engine", BUILD / "engine")
shutil.copytree(BUILD / "candidate/coordinator", BUILD / "coordinator")

# Synthetic fixture classes are generated-only Java 8 inputs. The canonical
# tail generator copies the checked-in generated corpus and patches only tail
# fixture sipush lengths; no JAR/class/resource input is opened.
fixture_generator = PARENT / "generate_tail_fixtures.py"
run("generated-fixture-build", [sys.executable, "-B", fixture_generator, FIXTURES])

pins = dict(PINS)
pins.update({
    "profile": "MC-RANDOM-CLASS-P18-PACKED-FLOAT-GROUPED-SCAN",
    "basis": "f867e6279 same-domain P18; only _checkpointArrayNonzeroCount changed",
    "worker": "local-grouped-scan",
    "engine": candidate_engine,
    "coordinator": candidate_coord,
    "baselineEngine": base_engine,
    "baselineCoordinator": base_coord,
    "bootstrapRoot": root_data["root"],
    "expectedBootstrapRoot": PINS["bootstrapRoot"],
    "sourceSHA256": sha(candidate_source.encode()),
    "baselineSourceSHA256": sha(baseline_source.encode()),
    "changedFunctions": changed,
    "orderedBootstrapLeaves": root_data["leaves"],
    "buildID": run_id,
    "generatedFixtureSource": "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures",
})
(BUILD / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(BUILD / "source-audit.json").write_text(json.dumps({
    "result": "PASS",
    "baselineCommit": "f867e6279",
    "baselineSourceSHA256": pins["baselineSourceSHA256"],
    "candidateSourceSHA256": pins["sourceSHA256"],
    "changedFunctions": changed,
    "bootstrapRootDomain": "JVMEVM:MC-RANDOM-CLASS-P18:BOOTSTRAP:1",
    "bootstrapRoot": root_data["root"],
    "orderedBootstrapLeaves": root_data["leaves"],
}, indent=2) + "\n")
(BUILD / "build-result.json").write_text(json.dumps({
    "result": "PASS",
    "generatedOnly": True,
    "engineABIUnchanged": candidate_engine_artifact["abi"] == base_engine_artifact["abi"],
    "engineStorageLayoutUnchanged": candidate_engine_artifact["storageLayout"] == base_engine_artifact["storageLayout"],
    "coordinatorABIUnchanged": candidate_coord_artifact["abi"] == base_coord_artifact["abi"],
    "changedFunctions": changed,
    "baselineEngine": base_engine,
    "candidateEngine": candidate_engine,
    "baselineCoordinator": base_coord,
    "candidateCoordinator": candidate_coord,
    "runtimeCap": PINS["runtimeCap"],
    "bootstrapRoot": root_data["root"],
    "orderedBootstrapLeaves": len(root_data["leaves"]),
    "fixtures": str(FIXTURES.relative_to(ROOT)),
    "limitations": "Only synthetic generated fixtures. No original JAR/classes/resources/worlds, original replay, EULA, logger, Done or standard-chain claim.",
}, indent=2) + "\n")
print(json.dumps({
    "build": str(BUILD.relative_to(ROOT)),
    "fixtures": str(FIXTURES.relative_to(ROOT)),
    "baselineEngine": base_engine,
    "candidateEngine": candidate_engine,
    "bootstrapRoot": root_data["root"],
    "orderedBootstrapLeaves": len(root_data["leaves"]),
    "changedFunctions": changed,
}, indent=2))
