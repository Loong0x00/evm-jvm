#!/usr/bin/env python3
"""Rebuild the one-constant MAX_ARRAYS candidate and independently pin source/ABI/layout."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ENGINE = HERE / "engine"
BASE = ROOT / "evidence/java-evm/minecraft-entry/parent-max-objects-2048/artifacts/engine"
ARTIFACTS = HERE / "artifacts"
NODE_MODULES = ROOT / "jvmevm/runtime/node_modules"
EXPECTED_P22_ROOT = "663211851e33185b08b0616167ddc3c37ae6789c161de4cd19515e4192f8c1a9"
OLD = "uint256 private constant MAX_ARRAYS = 2048;"
NEW = "uint256 private constant MAX_ARRAYS = 4096;"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bootstrap_root(source: str) -> tuple[str, list[str]]:
    body = source[source.index("    function _bootstrapRoot("):]
    body = body[:body.index("\n    function ", 1)]
    rhs = {int(i): value.strip() for i, value in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(rhs) == set(range(97)), (len(rhs), sorted(set(range(97)) - set(rhs)))
    pairs = []
    for i in range(97):
        expression = rhs[i]
        image = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", expression)
        if image:
            name = image.group(1)
            fn = source[source.index("    function " + name + "("):]
            fn = fn[:fn.index("\n    function ", 1)]
            values = re.findall(r'hex"([0-9a-f]+)"', fn)
            assert len(values) == 1, (i, name, len(values))
            pairs.append(("image", values[0]))
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", expression), (i, expression)
            declaration = re.search(r"bytes32 private constant " + expression + r"\s*=\s*([^;]+);", source)
            assert declaration, (i, expression)
            value = declaration.group(1).strip()
            values = re.findall(r'hex"([0-9a-f]+)"', value)
            assert len(values) == 1, (i, expression, len(values))
            pairs.append(("image" if value.startswith("keccak256(") else "hexhash", values[0]))
    payload = json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P22:BOOTSTRAP:1", "pairs": pairs})
    node = r'''const fs=require("fs"),{keccak256:k}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8"));
const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const hs=x.pairs.map(([t,v])=>t==="image"?k(Buffer.from(v,"hex")):v);
console.log(k(Buffer.concat([Buffer.from(k(x.domain),"hex"),w(64),w(97),...hs.map(v=>Buffer.from(v,"hex"))])));'''
    env = {**os.environ, "NODE_PATH": str(NODE_MODULES), "npm_config_offline": "true"}
    result = subprocess.run(["node", "-e", node], cwd=ROOT, env=env, input=payload,
                            text=True, capture_output=True, check=True)
    root = result.stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{64}", root)
    return root, [sha(bytes.fromhex(value)) if kind == "image" else value for kind, value in pairs]


def main() -> None:
    assert NODE_MODULES.is_dir()
    assert shutil.which("node")
    assert OLD in (BASE / "MCEntryInterpreter.sol").read_text()
    base_source = (BASE / "MCEntryInterpreter.sol").read_text()
    source_path = ENGINE / "MCEntryInterpreter.sol"
    source = source_path.read_text()
    assert base_source.count(OLD) == 1 and base_source.count(NEW) == 0
    assert source.count(NEW) == 1 and source.count(OLD) == 0
    assert source == base_source.replace(OLD, NEW, 1), "candidate differs beyond MAX_ARRAYS"
    assert (ENGINE / "build.js").read_bytes() == (BASE / "build.js").read_bytes()
    assert "MC-RANDOM-CLASS-P22" in source and "MC-RANDOM-CLASS-P23" not in source

    root, leaf_fingerprints = bootstrap_root(source)
    base_root, base_leaf_fingerprints = bootstrap_root(base_source)
    assert len(leaf_fingerprints) == len(base_leaf_fingerprints) == 97
    assert leaf_fingerprints == base_leaf_fingerprints
    assert root == base_root == EXPECTED_P22_ROOT, (root, base_root)

    artifact_path = ENGINE / "MCEntryInterpreter.json"
    assert artifact_path.is_file(), "run node engine/build.js first"
    candidate = json.loads(artifact_path.read_text())
    runtime_bytes = len(candidate["deployedBytecode"]) // 2
    assert runtime_bytes == 392090 and runtime_bytes <= 393216
    assert candidate["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"
    assert candidate["sourceHashes"]["MCEntryInterpreter.sol"] == sha(source.encode())
    assert candidate["codeHashes"]["runtimeSHA256"] == sha(bytes.fromhex(candidate["deployedBytecode"]))
    assert candidate["codeHashes"]["initSHA256"] == sha(bytes.fromhex(candidate["bytecode"]))

    # Compile the accepted predecessor from its preserved source with the same
    # pinned compiler, then compare the complete ABI and storage layout.
    with tempfile.TemporaryDirectory(prefix="mc-max-arrays-4096-baseline-") as temp:
        baseline_dir = Path(temp)
        shutil.copy2(BASE / "MCEntryInterpreter.sol", baseline_dir / "MCEntryInterpreter.sol")
        shutil.copy2(BASE / "build.js", baseline_dir / "build.js")
        env = {**os.environ, "NODE_PATH": str(NODE_MODULES), "npm_config_offline": "true"}
        subprocess.run(["node", str(baseline_dir / "build.js")], cwd=ROOT, env=env,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        baseline = json.loads((baseline_dir / "MCEntryInterpreter.json").read_text())
        assert candidate["abi"] == baseline["abi"]
        assert candidate["storageLayout"] == baseline["storageLayout"]
        abi_hash = sha(json.dumps(candidate["abi"], sort_keys=True, separators=(",", ":")).encode())
        layout_hash = sha(json.dumps(candidate["storageLayout"], sort_keys=True, separators=(",", ":")).encode())
        baseline_runtime = len(baseline["deployedBytecode"]) // 2
        assert baseline_runtime == runtime_bytes
        baseline_runtime_hash = baseline["codeHashes"]["runtimeSHA256"]

    ARTIFACTS.mkdir(exist_ok=True)
    report = {
        "schema": 1,
        "status": "worker candidate build/source audit; not parent acceptance",
        "semanticDelta": "MAX_ARRAYS 2048 -> 4096 only",
        "unchangedLimits": {"MAX_OBJECTS": 2048, "MAX_HANDLES": "derived", "otherLimits": True},
        "derivedMAX_HANDLES": 4096 + 2048 + 256 + 1,
        "runtimeBytes": runtime_bytes,
        "runtimeCapBytes": 393216,
        "runtimeSHA256": candidate["codeHashes"]["runtimeSHA256"],
        "runtimeKeccak256": candidate["codeHashes"]["runtimeKeccak256"],
        "baselineRuntimeSHA256": baseline_runtime_hash,
        "compiler": candidate["compiler"],
        "bootstrapRootDomain": "MC-RANDOM-CLASS-P22 (not relabeled in worker candidate)",
        "bootstrapRoot97": root,
        "orderedBootstrapLeaves": 97,
        "bootstrapLeavesIdenticalToP22": True,
        "abiIdenticalToP22": True,
        "abiSHA256": abi_hash,
        "storageLayoutIdenticalToP22": True,
        "storageLayoutSHA256": layout_hash,
        "sourceSHA256": sha(source.encode()),
        "baseSourceSHA256": sha(base_source.encode()),
    }
    (ARTIFACTS / "source-build-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
