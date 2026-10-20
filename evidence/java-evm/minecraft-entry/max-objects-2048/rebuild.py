#!/usr/bin/env python3
"""Build scoped P21 from the accepted P20 artifact; prove the one-quota delta."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/parent-max-arrays-2048"
OUT = Path(sys.argv[1]).resolve()
out = OUT
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-max-objects-2048-build-") and not OUT.exists()

prior = json.loads((BASE / "artifacts/parent-build-pins.json").read_text())
base = (BASE / "artifacts/engine/MCEntryInterpreter.sol").read_text()
source = (HERE / "engine/MCEntryInterpreter.sol").read_text()
base_obj = "uint256 private constant MAX_OBJECTS = 1024;"
new_obj = "uint256 private constant MAX_OBJECTS = 2048;"
assert base.count(base_obj) == 1 and source.count(new_obj) == 1
assert source.count("MC-RANDOM-CLASS-P21") == 9
normalized = source.replace("MC-RANDOM-CLASS-P21", "MC-RANDOM-CLASS-P20")
normalized = normalized.replace(new_obj, base_obj, 1)
assert normalized == base, "P20-normalized candidate must differ only in MAX_OBJECTS"
assert "MAX_ARRAYS = 2048" in source and "MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS" in source
assert "MAX_EXCEPTION_OBJECTS = 256" in source
assert "h[9] = keccak256(_bootstrapOutOfMemoryError());" in source
assert (HERE / "engine/build.js").read_bytes() == (BASE / "artifacts/engine/build.js").read_bytes()


def root_and_leaves(text, domain):
    body = text[text.index("    function _bootstrapRoot("):]
    body = body[:body.index("\n    function ", 1)]
    rhs = {int(i): v.strip() for i, v in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", body)}
    assert set(rhs) == set(range(97)), len(rhs)
    pairs = []
    for i in range(97):
        expr = rhs[i]
        m = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", expr)
        if m:
            f = text[text.index("    function " + m.group(1) + "("):]
            f = f[:f.index("\n    function ", 1)]
            values = re.findall(r'hex"([0-9a-f]+)"', f)
            assert len(values) == 1
            pairs.append(["image", values[0]])
        else:
            assert re.fullmatch(r"DBOOT_[A-Z_]+", expr), expr
            value = re.search(r"bytes32 private constant " + expr + r"\s*=\s*([^;]+);", text).group(1).strip()
            h = re.findall(r'hex"([0-9a-f]+)"', value)
            assert len(h) == 1
            pairs.append(["image" if value.startswith("keccak256(") else "hexhash", h[0]])
    env = dict(os.environ, GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local")
    p = subprocess.run(["go", "run", HERE / "source_root.go"], cwd=ROOT, env=env,
                       input=json.dumps({"domain": domain, "pairs": pairs}), text=True,
                       capture_output=True, check=True, timeout=120)
    result = json.loads(p.stdout)
    return result["root"], result["leaves"], pairs


old_root, old_hashes, _ = root_and_leaves(base, "JVMEVM:MC-RANDOM-CLASS-P20:BOOTSTRAP:1")
assert old_root == prior["bootstrapRoot"] == "845e0c87e52b163b246228ebf4400237953dfac4aa70d5b3fd4217c1dca7dee4"
assert old_hashes == prior["orderedBootstrapLeaves"]
new_root, new_hashes, ordered = root_and_leaves(source, "JVMEVM:MC-RANDOM-CLASS-P21:BOOTSTRAP:1")
assert old_hashes == new_hashes and len(ordered) == 97 and new_root != old_root
source_audit = {
    "acceptedP20Root": old_root, "actualIndependentP21Root": new_root,
    "orderedLeaves": 97, "orderedLeafHashes": new_hashes,
    "sourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "normalizedP20SourceSHA256": hashlib.sha256(normalized.encode()).hexdigest(),
    "onlyNormalizedSemanticChange": "MAX_OBJECTS1024->2048; MAX_HANDLES derived4353",
    "limits": {"MAX_ARRAYS": 2048, "MAX_OBJECTS": 2048, "MAX_HANDLES": 4353,
               "MAX_HANDLES_FORMULA": "MAX_ARRAYS + MAX_OBJECTS + MAX_EXCEPTION_OBJECTS + 1"},
    "canonicalOOMBootstrapLeafIndex": 9,
    "canonicalOOMBootstrapImageFunction": "_bootstrapOutOfMemoryError",
    "canonicalOOMClass": "java/lang/OutOfMemoryError",
    "domainTransition": "MC-RANDOM-CLASS-P20 -> MC-RANDOM-CLASS-P21",
}
audit_path = HERE / "artifacts/source-audit.json"
audit_bytes = json.dumps(source_audit, indent=2) + "\n"
if audit_path.exists():
    assert audit_path.read_text() == audit_bytes, "source audit is append-only; changed source needs a new stage"
else:
    audit_path.write_text(audit_bytes)

if not (ROOT / "jvmevm/runtime/node_modules/solc").is_dir():
    raise SystemExit("pinned solc 0.8.30 is not installed; build requires cached runtime dependencies")
out.mkdir(); (out / "tmp").mkdir()
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"),
           PYTHONDONTWRITEBYTECODE="1", GOPROXY="off", GOSUMDB="off")

def run(label, args):
    with (out / (label + ".log")).open("w") as f:
        subprocess.run(list(map(str, args)), cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT,
                       check=True, timeout=900)

engine = out / "engine"; engine.mkdir()
(engine / "MCEntryInterpreter.sol").write_text(source)
shutil.copy2(HERE / "engine/build.js", engine / "build.js")
run("engine-build", ["node", engine / "build.js"])
ea = json.loads((engine / "MCEntryInterpreter.json").read_text())
er = {"bytes": len(ea["deployedBytecode"]) // 2, **ea["codeHashes"]}
assert er["bytes"] <= 393216

coord = out / "coordinator"
shutil.copytree(BASE / "artifacts/coordinator", coord)
coord_source = coord / "MCEntryCoordinator.sol"
ct = coord_source.read_text()
assert ct.count("MC-RANDOM-CLASS-P20") == 4
ct = ct.replace("MC-RANDOM-CLASS-P20", "MC-RANDOM-CLASS-P21")
assert ct.count(prior["engine"]["runtimeKeccak256"]) == 1
ct = ct.replace(prior["engine"]["runtimeKeccak256"], er["runtimeKeccak256"], 1)
coord_source.write_text(ct)
run("coordinator-build", ["node", coord / "build.js"])
ca = json.loads((coord / "MCEntryCoordinator.json").read_text())
cr = {"bytes": len(ca["deployedBytecode"]) // 2, **ca["codeHashes"]}

old_domain, new_domain = "MC-RANDOM-CLASS-P20", "MC-RANDOM-CLASS-P21"
driver_source = (BASE / "canonical-driver.go.txt").read_text()
assert driver_source.count(old_domain) >= 9
driver_source = driver_source.replace(old_domain, new_domain)
for name, val in (("immutableEngineSHA256", er["runtimeSHA256"]),
                  ("immutableEngineKeccak", "0x" + er["runtimeKeccak256"]),
                  ("immutableCoordinatorKeccak", "0x" + cr["runtimeKeccak256"])):
    driver_source, n = re.subn(r'(const ' + name + r' = ")[^"]+("\n)',
                               r'\g<1>' + val + r'\g<2>', driver_source)
    assert n == 1, name
for name, size in (("engineRun", er["bytes"]), ("coordRun", cr["bytes"]), ("run", er["bytes"])):
    driver_source, n = re.subn(r'(len\(' + name + r'\) != )\d+', r'\g<1>' + str(size), driver_source)
    assert n == 1, name
assert "const ordinaryGas = uint64(1_000_000_000)" in driver_source
(out / "main.go").write_text(driver_source)
for label, args in (("gofmt", ["gofmt", "-w", out / "main.go"]),
                    ("go-build", ["go", "build", "-trimpath", "-o", out / "driver", out / "main.go"]),
                    ("go-vet", ["go", "vet", out / "main.go"])):
    run(label, args)

pins = {
    **prior,
    "profile": "MC-RANDOM-CLASS-P21-MAX-OBJECTS-2048", "basis": "parent-max-arrays-2048",
    "bootstrapCount": 97, "bootstrapRoot": new_root, "expectedBootstrapRoot": new_root,
    "address": "0x4d432d52414e444f4d2d434c4153532d50310042",
    "owner": "0x4d432d52414e444f4d2d434c4153532d50310043", "engine": er, "coordinator": cr,
    "maxArrays": 2048, "maxObjects": 2048, "maxHandles": 4353,
    "canonicalOOMBootstrapLeafIndex": 9, "canonicalOOMClass": "java/lang/OutOfMemoryError",
    "sourceInvariants": {"normalizedDelta": "MAX_OBJECTS1024->2048 only",
                          "p20Root": old_root, "orderedLeaves": 97,
                          "leafHashesUnchanged": old_hashes == new_hashes},
    "domain": new_domain,
}
(out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
(out / "root-audit.json").write_text(json.dumps({
    "acceptedP20Root": old_root, "actualIndependentP21Root": new_root,
    "orderedLeaves": 97, "orderedLeafHashes": new_hashes,
    "sourceSHA256": hashlib.sha256(source.encode()).hexdigest(),
    "onlyNormalizedSemanticChange": "MAX_OBJECTS1024->2048; MAX_HANDLES derived4353",
    "domainTransition": "MC-RANDOM-CLASS-P20 -> MC-RANDOM-CLASS-P21",
}, indent=2) + "\n")
(HERE / "canonical-driver.go.txt").write_text(driver_source)
shutil.copy2(coord_source, HERE / "coordinator/MCEntryCoordinator.sol")
print(json.dumps({"engine": er, "coordinator": cr, "bootstrapRoot": new_root,
                  "maxObjects": 2048, "maxArrays": 2048, "maxHandles": 4353}, indent=2))
