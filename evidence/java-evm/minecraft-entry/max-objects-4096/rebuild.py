#!/usr/bin/env python3
"""Build the one-constant P23 MAX_OBJECTS candidate and audit it offline."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/parent-max-arrays-4096/artifacts"
NODE_MODULES = ROOT / "jvmevm/runtime/node_modules"
OLD = "uint256 private constant MAX_OBJECTS = 2048;"
NEW = "uint256 private constant MAX_OBJECTS = 4096;"
P23_ROOT = "3488aad418a50e641220126a44a1b5dd9ce190505611a0f20f50e8814311a33c"
ENGINE_ADDRESS = "0x4d432d52414e444f4d2d434c4153532d50310048"
OWNER_ADDRESS = "0x4d432d52414e444f4d2d434c4153532d50310049"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(label, args, cwd, env, timeout=900):
    with (OUT / (label + ".log")).open("w") as stream:
        subprocess.run(list(map(str, args)), cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=timeout)


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
    payload = json.dumps({"domain": "JVMEVM:MC-RANDOM-CLASS-P23:BOOTSTRAP:1", "pairs": pairs})
    node = r'''const fs=require("fs"),{keccak256:k}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8"));
const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const hs=x.pairs.map(([t,v])=>t==="image"?k(Buffer.from(v,"hex")):v);
const root=k(Buffer.concat([Buffer.from(k(x.domain),"hex"),w(64),w(97),...hs.map(v=>Buffer.from(v,"hex"))]));
console.log(JSON.stringify({root,leaves:hs}));'''
    env = {**os.environ, "NODE_PATH": str(NODE_MODULES), "npm_config_offline": "true"}
    result = subprocess.run(["node", "-e", node], cwd=ROOT, env=env, input=payload,
                            text=True, capture_output=True, check=True)
    value = json.loads(result.stdout)
    return value["root"], value["leaves"]


def main() -> None:
    global OUT
    assert len(sys.argv) == 2, "usage: rebuild.py UNIQUE_BUILD_DIR"
    OUT = Path(sys.argv[1]).resolve()
    assert OUT.parent == ROOT / "build"
    assert OUT.name.startswith("java-diff-mc-max-objects-4096-build-") and not OUT.exists()
    assert NODE_MODULES.is_dir() and shutil.which("node")
    OUT.mkdir(); (OUT / "tmp").mkdir()
    env = {**os.environ, "TMPDIR": str(OUT / "tmp"), "NODE_PATH": str(NODE_MODULES),
           "PYTHONDONTWRITEBYTECODE": "1", "GOPROXY": "off", "GOSUMDB": "off",
           "GOTOOLCHAIN": "local", "npm_config_offline": "true"}

    base_path = BASE / "engine/MCEntryInterpreter.sol"
    base_source = base_path.read_text()
    source_path = HERE / "engine/MCEntryInterpreter.sol"
    source = source_path.read_text()
    assert base_source.count(OLD) == 1 and base_source.count(NEW) == 0
    assert source == base_source.replace(OLD, NEW, 1), "candidate differs beyond MAX_OBJECTS"
    assert (HERE / "engine/build.js").read_bytes() == (BASE / "engine/build.js").read_bytes()
    assert "MAX_ARRAYS = 4096" in source and "MAX_EXCEPTION_OBJECTS = 256" in source
    assert "MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS\n        + MAX_EXCEPTION_OBJECTS + 1" in source
    assert 4096 + 4096 + 256 + 1 == 8449
    assert source.count("MC-RANDOM-CLASS-P23") == base_source.count("MC-RANDOM-CLASS-P23")

    base_root, base_leaves = bootstrap_root(base_source)
    candidate_root, candidate_leaves = bootstrap_root(source)
    assert base_root == candidate_root == P23_ROOT
    assert len(base_leaves) == len(candidate_leaves) == 97 and base_leaves == candidate_leaves

    # Compile the exact accepted base and one-constant candidate from clean temp
    # directories with the already-provisioned, pinned offline compiler.
    with tempfile.TemporaryDirectory(prefix="mc-max-objects-4096-audit-") as temp:
        tmp = Path(temp)
        baseline_dir, candidate_dir = tmp / "baseline", tmp / "candidate"
        baseline_dir.mkdir(); candidate_dir.mkdir()
        for directory, text in ((baseline_dir, base_source), (candidate_dir, source)):
            (directory / "MCEntryInterpreter.sol").write_text(text)
            shutil.copy2(BASE / "engine/build.js", directory / "build.js")
        for directory in (baseline_dir, candidate_dir):
            subprocess.run(["node", str(directory / "build.js")], cwd=ROOT, env=env,
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=900)
        baseline = json.loads((baseline_dir / "MCEntryInterpreter.json").read_text())
        freshly_compiled = json.loads((candidate_dir / "MCEntryInterpreter.json").read_text())

    engine = OUT / "engine"; engine.mkdir()
    shutil.copy2(source_path, engine / "MCEntryInterpreter.sol")
    shutil.copy2(HERE / "engine/build.js", engine / "build.js")
    run("engine-build", ["node", engine / "build.js"], ROOT, env)
    candidate = json.loads((engine / "MCEntryInterpreter.json").read_text())
    assert candidate["bytecode"] == freshly_compiled["bytecode"]
    assert candidate["deployedBytecode"] == freshly_compiled["deployedBytecode"]
    assert candidate["abi"] == baseline["abi"] == freshly_compiled["abi"]
    assert candidate["storageLayout"] == baseline["storageLayout"] == freshly_compiled["storageLayout"]
    runtime_bytes = len(candidate["deployedBytecode"]) // 2
    assert runtime_bytes <= 393216
    assert candidate["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"
    er = {"bytes": runtime_bytes, **candidate["codeHashes"]}

    # Coordinator remains P23 and changes only its immutable engine code hash.
    coord = OUT / "coordinator"; coord.mkdir()
    base_coord = BASE / "coordinator/MCEntryCoordinator.sol"
    coordinator_source = base_coord.read_text()
    prior_pins = json.loads((BASE / "parent-build-pins.json").read_text())
    old_hash = prior_pins["engine"]["runtimeKeccak256"]
    assert coordinator_source.count(old_hash) == 1
    coordinator_source = coordinator_source.replace(old_hash, er["runtimeKeccak256"], 1)
    (coord / "MCEntryCoordinator.sol").write_text(coordinator_source)
    shutil.copy2(BASE / "coordinator/build.js", coord / "build.js")
    run("coordinator-build", ["node", coord / "build.js"], ROOT, env)
    ca = json.loads((coord / "MCEntryCoordinator.json").read_text())
    cr = {"bytes": len(ca["deployedBytecode"]) // 2, **ca["codeHashes"]}
    assert ca["abi"] == json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())["abi"]
    assert ca["storageLayout"] == json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())["storageLayout"]

    # Use only the accepted P23 canonical driver as harness source; pin it to
    # this fresh candidate and compile with Go modules/network disabled.
    driver = (BASE.parent / "canonical-driver.go.txt").read_text()
    for name, value in (("immutableEngineSHA256", er["runtimeSHA256"]),
                        ("immutableEngineKeccak", "0x" + er["runtimeKeccak256"]),
                        ("immutableCoordinatorKeccak", "0x" + cr["runtimeKeccak256"])):
        driver, n = re.subn(r'(const ' + name + r' = ")[^"]+("\n)',
                            lambda m: m.group(1) + value + m.group(2), driver)
        assert n == 1, name
    for name, size in (("engineRun", er["bytes"]), ("coordRun", cr["bytes"]), ("run", er["bytes"])):
        driver, n = re.subn(r'(len\(' + name + r'\) != )\d+',
                            lambda m: m.group(1) + str(size), driver)
        assert n == 1, name
    resume_one = 'case "resume-one-q1":\n\t\tdoResumeBudget(os.Args[2], os.Args[3], true, 1)\n'
    assert driver.count(resume_one) == 1
    driver = driver.replace(
        resume_one,
        resume_one + 'case "resume-one-q":\n'
        '\t\tif len(os.Args) != 8 { panic("resume-one-q requires SMALLER") }\n'
        '\t\tsmaller, err := strconv.ParseUint(os.Args[7], 10, 64)\n'
        '\t\tmust(err)\n'
        '\t\tdoResumeBudget(os.Args[2], os.Args[3], true, smaller)\n',
        1,
    )
    assert 'const ordinaryGas = uint64(1_000_000_000)' in driver
    assert 'MC-RANDOM-CLASS-P23' in driver
    (OUT / "main.go").write_text(driver)
    for label, args in (("gofmt", ["gofmt", "-w", OUT / "main.go"]),
                        ("go-build", ["go", "build", "-trimpath", "-o", OUT / "driver", OUT / "main.go"]),
                        ("go-vet", ["go", "vet", OUT / "main.go"])):
        run(label, args, ROOT, env)

    abi_hash = sha(json.dumps(candidate["abi"], sort_keys=True, separators=(",", ":")).encode())
    layout_hash = sha(json.dumps(candidate["storageLayout"], sort_keys=True, separators=(",", ":")).encode())
    pins = {
        **prior_pins,
        "profile": "MC-RANDOM-CLASS-P23-MAX-OBJECTS-4096-WORKER-CANDIDATE",
        "domain": "MC-RANDOM-CLASS-P23", "bootstrapCount": 97,
        "bootstrapRoot": candidate_root, "expectedBootstrapRoot": P23_ROOT,
        "address": ENGINE_ADDRESS, "owner": OWNER_ADDRESS,
        "engine": er, "coordinator": cr,
        "maxArrays": 4096, "maxObjects": 4096, "maxHandles": 8449,
        "runtimeCap": 393216, "sourceSHA256": sha(source.encode()),
        "driverSHA256": sha((OUT / "main.go").read_bytes()),
        "driverHarnessExtension": "resume-one-q accepts a bounded smaller resume quantum; EVM budget remains 1B",
        "baseSourceSHA256": sha(base_source.encode()),
        "coordinatorSourceSHA256": sha(coordinator_source.encode()),
        "abiIdenticalToP23": candidate["abi"] == baseline["abi"],
        "storageLayoutIdenticalToP23": candidate["storageLayout"] == baseline["storageLayout"],
        "abiSHA256": abi_hash, "storageLayoutSHA256": layout_hash,
        "bootstrapLeavesIdenticalToP23": base_leaves == candidate_leaves,
        "sourceInvariants": {"normalizedDelta": "MAX_OBJECTS2048->4096 only",
                              "acceptedP23Root": P23_ROOT, "orderedLeaves": 97,
                              "leafHashesUnchanged": base_leaves == candidate_leaves},
        "sourceDelta": "MAX_OBJECTS 2048 -> 4096 only",
    }
    (OUT / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    source_audit = {
        "schema": 1, "status": "scoped worker build/source audit; parent independent review pending",
        "base": "parent-max-arrays-4096/artifacts/engine/MCEntryInterpreter.sol",
        "baseSourceSHA256": pins["baseSourceSHA256"], "candidateSourceSHA256": pins["sourceSHA256"],
        "sourceDelta": pins["sourceDelta"], "maxArrays": 4096, "maxObjects": 4096,
        "derivedMaxHandles": 8449, "derivedFormula": "MAX_ARRAYS + MAX_OBJECTS + MAX_EXCEPTION_OBJECTS + 1",
        "runtimeBytes": runtime_bytes, "runtimeCapBytes": 393216,
        "runtimeSHA256": er["runtimeSHA256"], "runtimeKeccak256": er["runtimeKeccak256"],
        "compiler": candidate["compiler"], "bootstrapDomain": "MC-RANDOM-CLASS-P23",
        "bootstrapRoot97": candidate_root, "orderedBootstrapLeaves": 97,
        "orderedBootstrapLeavesIdentical": base_leaves == candidate_leaves,
        "abiIdenticalToP23": pins["abiIdenticalToP23"], "abiSHA256": abi_hash,
        "storageLayoutIdenticalToP23": pins["storageLayoutIdenticalToP23"],
        "storageLayoutSHA256": layout_hash,
        "candidateArtifactMatchesFreshCompile": True,
    }
    audit_path = HERE / "artifacts/source-audit.json"
    audit_text = json.dumps(source_audit, indent=2) + "\n"
    if audit_path.exists():
        assert audit_path.read_text() == audit_text, "source audit is append-only; use a new run filename"
    else:
        audit_path.write_text(audit_text)
    candidate_coord_path = HERE / "artifacts/MCEntryCoordinator-P23-candidate.sol"
    if candidate_coord_path.exists():
        assert candidate_coord_path.read_text() == coordinator_source
    else:
        candidate_coord_path.write_text(coordinator_source)
    print(json.dumps({**source_audit, "buildDirectory": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
