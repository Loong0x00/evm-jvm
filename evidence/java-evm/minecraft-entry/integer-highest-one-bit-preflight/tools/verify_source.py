#!/usr/bin/env python3
"""Strict generated-only verifier for Integer.highestOneBit(int)."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-bbecbd532"
prior = stage.parent / "classcount62-byte376794-preflight"
base_stage = stage.parent / "integer-to-string-preflight"

DOMAIN = "MC-INTEGER-HIGHEST-ONE-BIT-P1"
PARENT_DOMAIN = "MC-SYSTEM-SET-OUT-012"
ADDRESS = "4d432d494e542d484947484553542d4249542d31"
OWNER = "4d432d494e542d484947484553542d4249542d32"
IMAGE_SHA256 = "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd"
IMAGE_KECCAK = "1a698ef9f803879a7f45c3613a679295cd1db22528c2c0e986fc4f9a6b845ba9"
ROOT = "57722a32ab679ecdca73bd05c5cb633aa5984568e531a0dcbf2651bc0dac997c"
ENGINE = {"bytes": 377409, "initSHA256": "d154a96084f62f6065fd18f00de6f3013da3c583d21ecaa44b0a5948241ae528", "runtimeSHA256": "1367d8b7bf6e92bd9615673dc073400c043800355bc6d7957c4b5c4ecea79439", "runtimeKeccak256": "824a4b3f47e3dc10b06ba708d2bf36ed750827d5a9d425d0cf3301a59452680a"}
COORDINATOR = {"bytes": 5394, "initSHA256": "69b9e5f55ecc782fd4748837ce3b52eb8baf59544c1d55c86627825db31c3322", "runtimeSHA256": "c69604c9d4a733c88f3f23f0d350fba39ba3dc10b6956c6414cf68900321d234", "runtimeKeccak256": "77d95257b0ccbf818b77a97b1b6014654372f9d488f2c7855dfafb7100f17b7d"}

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "7cbddf64778247d9ce8e0968e3cc88d4f59a473cd48a728d241b7785a80f8c64",
    "artifacts/coordinator/MCEntryCoordinator.sol": "9852b593929f89f56cf8aa1d295e32f0e6cd01bb9bd934183f80257230b3a25b",
    "canonical-driver.go.txt": "0e2677ddb5cc89b6139696180b9843ca5d5cf1c2f6c6aba8b923e480e98f5264",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "checkpoint_diagnostic.py": "076cefca981bb4b45f807aca02bdde93d3fda4b2f9d9c1efd5ada8ccaf7abc30",
    "checkpoint_frames.py": "076cefca981bb4b45f807aca02bdde93d3fda4b2f9d9c1efd5ada8ccaf7abc30",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "pins.json": "19e7539fe1a435fb3f67c71fbea02b35da19656a2b0c4b61179c7555eedea84a",
}
SOURCE_PINS = {
    "bootstrap-source": "9788a98dd953aedd525481c046803e69265668e7e6a92e76a072a0f78aa1a9fd",
    "strip-stackmap": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "retained-fixtures": "9ed9886c6d76fcee1a6ebb60b467788f9bd3c37d7798c0f8fda95e1c34e084ae",
    "focused-fixtures": "a108c28036966da2e0f5605bfb616876f062412275cb3fa3fef1a172ac0de1bb",
    "gate": "280d362c8e04a1b99f17d755fa42f27ca20162de09cdd7075e17725a17446a1b",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def bootstrap_literal(source, name):
    match = re.search(r"function _bootstrap" + re.escape(name) + r"\(\).*?return hex\"([0-9a-f]+)\";", source, re.S)
    assert match, name
    return match.group(1)


def keccak_hex(value):
    node = root / "jvmevm/runtime/node_modules"
    assert node.is_dir(), "refusing shared or network node dependencies"
    return subprocess.check_output([
        "node", "-e", "const {keccak256}=require('js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));", value,
    ], text=True, env={**os.environ, "NODE_PATH": str(node)})


def leaves(source):
    assignments = re.findall(r"h\[(\d+)\] = (keccak256\(_bootstrap([A-Za-z0-9]+)\(\)\)|DBOOT_[A-Z_]+);", source)
    assert len(assignments) == 94 and [int(index) for index, _, _ in assignments] == list(range(94))
    result = []
    for _, expression, name in assignments:
        if name:
            result.append((name, keccak_hex(bootstrap_literal(source, name))))
            continue
        constant = re.search(r"bytes32 private constant " + re.escape(expression) + r" = (.*?);", source)
        assert constant, expression
        rhs = constant.group(1)
        if rhs.startswith('hex"'):
            value = rhs[4:-1]
        else:
            image = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', rhs)
            assert image, (expression, rhs[:96])
            value = keccak_hex(image.group(1))
        result.append((expression, value))
    return result


def root_commitment(domain, hashes):
    node = root / "jvmevm/runtime/node_modules"
    program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
    return json.loads(subprocess.check_output(["node", "-e", program], input=json.dumps({"domain": domain, "hashes": hashes}), text=True, env={**os.environ, "NODE_PATH": str(node)}))


assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
for relative, expected in PARENT_SHA256.items():
    assert digest(parent / relative) == expected, relative
assert digest(base_stage / "bootstrap/java/lang/Integer.java") == SOURCE_PINS["bootstrap-source"]
assert digest(stage / "tools/strip_stackmap.py") == SOURCE_PINS["strip-stackmap"]
assert digest(stage / "tools/generate_retained_fixtures.py") == SOURCE_PINS["retained-fixtures"]
assert digest(stage / "tools/generate_focused_fixtures.py") == SOURCE_PINS["focused-fixtures"]
assert digest(stage / "tools/gate.py") == SOURCE_PINS["gate"]

# The complete canonical Java source is the accepted Integer source plus exactly
# one append-only Java-8 static method. No other source spelling may vary.
base = (base_stage / "bootstrap/java/lang/Integer.java").read_text()
append = '''  public static int highestOneBit(int i) {
    i |= (i >> 1);
    i |= (i >> 2);
    i |= (i >> 4);
    i |= (i >> 8);
    i |= (i >> 16);
    return i - (i >>> 1);
  }
'''
assert base.endswith("}\n")
expected_source = base[:-2] + append + "}\n"
source = (stage / "bootstrap/java/lang/Integer.java").read_text()
assert source == expected_source
assert source.count("highestOneBit") == 1 and "rotateLeft" not in source

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
javap = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
assert javac.is_file() and javap.is_file()
spec = importlib.util.spec_from_file_location("strip_stackmap", stage / "tools/strip_stackmap.py")
strip = importlib.util.module_from_spec(spec); spec.loader.exec_module(strip)
(root / "build").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="integer-highest-one-bit-image-", dir=root / "build") as temporary:
    classes = Path(temporary) / "classes"; classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, stage / "bootstrap/java/lang/Integer.java"], check=True)
    raw = (classes / "java/lang/Integer.class").read_bytes()
    image, removed = strip.strip_stackmap(raw)
    verbose = subprocess.check_output([javap, "-verbose", classes / "java/lang/Integer.class"], text=True)
assert len(raw) == 2100 and hashlib.sha256(raw).hexdigest() == "5aecdfd705734accb46f71c9c242673ee739c8cf0a582b35ae2e1121ee15948f"
assert removed == 61 and len(image) == 2039 and hashlib.sha256(image).hexdigest() == IMAGE_SHA256
assert bytes.fromhex((stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip()) == image
method = verbose.split("public static int highestOneBit(int);", 1)[1].split("public int compareTo(java.lang.Object);", 1)[0]
for token in ("descriptor: (I)I", "flags: ACC_PUBLIC, ACC_STATIC", "ishr", "iushr", "isub", "ireturn"):
    assert token in method, token
assert method.count("ishr") == 5 and method.count("iushr") == 1
assert b"highestOneBit" in image and b"rotateLeft" not in image

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
old_integer = bootstrap_literal(parent_engine, "Integer")
assert hashlib.sha256(bytes.fromhex(old_integer)).hexdigest() == "56b891f66fbab31669688a128b8a888291183461adb3aaf667aba394cd1455a8"
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
expected_engine = exact(expected_engine, '    function _bootstrapInteger() private pure returns (bytes memory) { return hex"' + old_integer + '"; }', '    function _bootstrapInteger() private pure returns (bytes memory) { return hex"' + image.hex() + '"; }')
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
assert engine.count(DOMAIN) == 9 and engine.count(PARENT_DOMAIN) == 0
for fixed in ("MAX_RAW_CLASSES = 62;", "MAX_RAW_BYTES = 376794;", "new bytes32[](94)", "MAX_FRAMES = 128;", "MAX_CHECKPOINT_BYTES = 1048576;", "COMMIT_RESERVE = 25_000_000;", "uint32(62), uint32(376794)", "return 16;", "new uint256[](14)"):
    assert engine.count(fixed) == 1, fixed
assert engine.count("Binding 11 is String-local.") == 1 and engine.count('bytes("substring")') >= 1

parent_leaves = leaves(parent_engine)
current_leaves = leaves(engine)
assert [index for index, (before, after) in enumerate(zip(parent_leaves, current_leaves)) if before[1] != after[1]] == [70]
assert current_leaves[70] == ("Integer", IMAGE_KECCAK)
record = json.loads((stage / "root-commitment.json").read_text())
calculated = root_commitment(DOMAIN, [value for _, value in current_leaves])
assert record == {"schema": 1, "basis": "parent-bbecbd532", "domain": DOMAIN, "order": [name for name, _ in current_leaves], "keccak256": [value for _, value in current_leaves], "integer": {"slot": 70, "bytes": 2039, "sha256": IMAGE_SHA256, "keccak256": IMAGE_KECCAK}, **calculated}
assert record["bootstrapRoot"] == ROOT

pins = json.loads((stage / "build-pins.json").read_text())
assert pins["basis"] == "bbecbd532" and pins["domain"] == DOMAIN and pins["bootstrapCount"] == 94
assert pins["bootstrapRoot"] == ROOT and pins["integer"] == record["integer"]
assert pins["rawLimits"] == [62, 376794] and pins["diagnosticClassBound"] == 156
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["checkpointCap"] == 1048576 and pins["reserve"] == 25_000_000 and pins["externalLocalGas"] == 1_000_000_000
assert pins["runtimeCap"] == 393216 and pins["engine"] == ENGINE and pins["coordinator"] == COORDINATOR
assert pins["address"] == "0x" + ADDRESS and pins["owner"] == "0x" + OWNER
assert pins["bootstrapSHA256"]["Integer"] == IMAGE_SHA256

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN)
expected_coordinator = re.sub(r"address private constant ENGINE = .*?;", 'address private constant ENGINE = address(bytes20(hex"' + ADDRESS + '"));', expected_coordinator, count=1)
expected_coordinator = re.sub(r"bytes32 private constant ENGINE_CODEHASH = hex\"[0-9a-f]{64}\";", 'bytes32 private constant ENGINE_CODEHASH = hex"' + ENGINE["runtimeKeccak256"] + '";', expected_coordinator, count=1)
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_coordinator

parent_pins = json.loads((parent / "pins.json").read_text())
expected_driver = (parent / "canonical-driver.go.txt").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(parent_pins["address"], pins["address"]).replace(parent_pins["owner"], pins["owner"])
for name, value in (("immutableEngineSHA256", ENGINE["runtimeSHA256"]), ("immutableEngineKeccak", "0x" + ENGINE["runtimeKeccak256"]), ("immutableCoordinatorKeccak", "0x" + COORDINATOR["runtimeKeccak256"])):
    expected_driver, count = re.subn(r"(const " + name + r" = \")[^\"]+(\"\n)", r"\g<1>" + value + r"\g<2>", expected_driver)
    assert count == 1, name
for name, value in (("engineRun", ENGINE["bytes"]), ("coordRun", COORDINATOR["bytes"]), ("run", ENGINE["bytes"])):
    expected_driver, count = re.subn(r"(len\(" + name + r"\) != )\d+", r"\g<1>" + str(value), expected_driver)
    assert count == 1, name
assert (stage / "tools/Go.txt").read_text() == expected_driver
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes()

# Generated fixtures contain the exact focus, raw replacement, malformed input,
# and omitted rotateLeft controls; retained direct/reopen controls are copied only
# by stage-name substitution and no original input is permitted.
assert (stage / "tools/generate_retained_fixtures.py").read_text() == (prior / "tools/generate_retained_fixtures.py").read_text().replace("classcount62-byte376794", "integer-highest-one-bit")
focused = (stage / "tools/generate_focused_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for label in ("integer-highest-one-bit", "integer-highest-one-bit-rotate-left-omitted", "raw-integer-highest-one-bit", "malformed-integer-highest-one-bit"):
    assert '"' + label + '"' in focused and '"' + label + '"' in gate
assert "Integer.highestOneBit" in focused and "Integer.rotateLeft" in focused
assert "q_equivalent(\"integer-highest-one-bit\", \"integer-highest-one-bit\")" in gate
assert "whole_gate_seconds <= 1200" in gate and '"profile": "MC-INTEGER-HIGHEST-ONE-BIT-P1"' in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

if sys.argv[1] == "--built":
    assert len(sys.argv) == 3 and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
else:
    assert len(sys.argv) == 2
print(json.dumps({"phase": "built" if sys.argv[1] == "--built" else "prebuild", "domain": DOMAIN, "integer": record["integer"], "bootstrapRoot": ROOT, "runtime": ENGINE["bytes"], "rawLimits": pins["rawLimits"], "diagnosticClassBound": pins["diagnosticClassBound"]}, indent=2))
