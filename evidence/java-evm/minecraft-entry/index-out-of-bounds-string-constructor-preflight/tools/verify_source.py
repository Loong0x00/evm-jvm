#!/usr/bin/env python3
"""Strict generated-only verifier for IndexOutOfBoundsException(String)."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-aaea6e3ee"

PARENT_DOMAIN = "MC-INTEGER-TO-STRING-P2"
DOMAIN = "MC-IOOB-STRCTOR-0001"
PARENT_ENGINE = "4d432d494e542d544f535452494e472d30303033"
ENGINE = "4d432d494f4f422d53545243544f522d30303031"
PARENT_OWNER = "4d432d494e542d544f535452494e472d30303034"
OWNER = "4d432d494f4f422d53545243544f522d30303032"
RUNTIME_SHA256 = "a0305062fca2636aca4ae17927cf84b5b7d25532f1c560fc096a4f82d5c85507"
INDEX_SHA256 = "f62b62e31b9b00e3ffb84929e809095c7affde45b9046f4aee81d530e01ee8f6"

PARENT_FILES = {
    "pins.json": "fab0ae1d51c19370d31ed5e521df71867e2660ab6c4c500c8e12fbfa20147d47",
    "artifacts/engine/MCEntryInterpreter.sol": "cd403faec33fd51e2eaa80c2560a9973913cf008748d4a41b2998523b032b198",
    "artifacts/coordinator/MCEntryCoordinator.sol": "47de8a822f95ee9361cc79a902e6b3034386760e4a9c9244a808cf77c7c94f16",
    "canonical-driver.go.txt": "317d1d242c386ec371c1371705f7f0c23519cde1fee0a662b9284aa9ef95f469",
    "checkpoint_diagnostic.py": "be1651f1dfaa34ccdc4f2947e2669797cf7ea7ea6c72a1612b075b8ad1d0ef6d",
    "checkpoint_frames.py": "be1651f1dfaa34ccdc4f2947e2669797cf7ea7ea6c72a1612b075b8ad1d0ef6d",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(text, old, new):
    assert text.count(old) == 1, (old[:96], text.count(old))
    return text.replace(old, new)


def bootstrap_hex(text, name):
    match = re.search(r"function _bootstrap" + re.escape(name) + r"\(\).*?return hex\"([0-9a-f]+)\";", text, re.S)
    assert match, name
    return match.group(1)


def function_literal(text, name):
    pattern = r"    function _bootstrap" + re.escape(name) + r"\(\) private pure returns \(bytes memory\) \{\n        return hex\"[0-9a-f]+\";\n    \}"
    match = re.search(pattern, text)
    assert match, name
    return match.group(0)


def root_record(domain, engine, order):
    node = root / "jvmevm/runtime/node_modules"
    assert node.is_dir(), "refusing shared or network node dependencies"
    hashes = []
    for name in order:
        hashes.append(subprocess.check_output([
            "node", "-e", "const {keccak256}=require('js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));",
            bootstrap_hex(engine, name),
        ], text=True, env={**os.environ, "NODE_PATH": str(node)}))
    program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
    computed = json.loads(subprocess.check_output(
        ["node", "-e", program], input=json.dumps({"domain": domain, "hashes": hashes}), text=True,
        env={**os.environ, "NODE_PATH": str(node)},
    ))
    return {"domain": domain, **computed, "bootstrapCount": len(order), "order": order, "keccak256": hashes,
            "unchangedLeavesRuntimeDerived": True}


assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "aaea6e3ee", "parentEvidence": "parent-aaea6e3ee", "sha256": inputs,
}

sources = {
    "RuntimeException": """package java.lang;
public class RuntimeException extends Exception {
  public RuntimeException() { super(); }
  public RuntimeException(String message) { super(message); }
}
""",
    "IndexOutOfBoundsException": """package java.lang;
public class IndexOutOfBoundsException extends RuntimeException {
  public IndexOutOfBoundsException() { super(); }
  public IndexOutOfBoundsException(String message) { super(message); }
}
""",
}
for name, expected in sources.items():
    assert (stage / "bootstrap/java/lang" / (name + ".java")).read_text() == expected
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="ioob-string-constructor-image-", dir=root / "build") as temporary:
    classes = Path(temporary) / "classes"; classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                    *(stage / "bootstrap/java/lang" / (name + ".java") for name in sources)], check=True)
    generated = {name: (classes / "java/lang" / (name + ".class")).read_bytes() for name in sources}
images = {name: bytes.fromhex((stage / "bootstrap/java/lang" / (name + ".class.hex")).read_text().strip()) for name in sources}
assert images == generated
assert (len(images["RuntimeException"]), hashlib.sha256(images["RuntimeException"]).hexdigest()) == (210, RUNTIME_SHA256)
assert (len(images["IndexOutOfBoundsException"]), hashlib.sha256(images["IndexOutOfBoundsException"]).hexdigest()) == (226, INDEX_SHA256)
# The sole new chain is RuntimeException(String)->Exception(String), then
# IndexOutOfBoundsException(String)->RuntimeException(String). No Throwable
# cause overload is embedded and both original no-arg constructors remain.
assert images["RuntimeException"].count(b"()V") == 1 and images["RuntimeException"].count(b"(Ljava/lang/String;)V") == 1
assert images["IndexOutOfBoundsException"].count(b"()V") == 1 and images["IndexOutOfBoundsException"].count(b"(Ljava/lang/String;)V") == 1
assert b"java/lang/Exception" in images["RuntimeException"] and b"java/lang/RuntimeException" in images["IndexOutOfBoundsException"]
assert b"Ljava/lang/Throwable;" not in images["RuntimeException"] + images["IndexOutOfBoundsException"]

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
for name in ("RuntimeException", "IndexOutOfBoundsException"):
    old = function_literal(expected_engine, name)
    new = "    function _bootstrap%s() private pure returns (bytes memory) {\n        return hex\"%s\";\n    }" % (name, images[name].hex())
    expected_engine = replace_exact(expected_engine, old, new)
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
assert engine.count(PARENT_DOMAIN) == 0 and engine.count(DOMAIN) == 9
assert bootstrap_hex(parent_engine, "Exception") == bootstrap_hex(engine, "Exception")
assert bootstrap_hex(parent_engine, "Throwable") == bootstrap_hex(engine, "Throwable")
assert engine.count("h[16] = keccak256(_bootstrapRuntimeException());") == 1
assert engine.count("h[22] = keccak256(_bootstrapIndexOutOfBoundsException());") == 1
assert engine.count("new bytes32[](94)") == 1 and engine.count("return keccak256(abi.encode(DBOOT, h));") == 1
for fixed in (
    "MAX_RAW_CLASSES = 50;", "MAX_RAW_BYTES = 324338;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(50), uint32(324338)",
):
    assert engine.count(fixed) == 1, fixed

parent_root = json.loads((stage / "parent-root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert parent_root == root_record(PARENT_DOMAIN, parent_engine, parent_root["order"])
assert record == {**root_record(DOMAIN, engine, parent_root["order"]), "parentRootEvidence": "parent-aaea6e3ee (recomputed from its exact runtime-derived engine)", "runtimeException": {"slot": 16, "bytes": 210, "sha256": RUNTIME_SHA256}, "indexOutOfBoundsException": {"slot": 22, "bytes": 226, "sha256": INDEX_SHA256}}
changed = [i for i, (before, after) in enumerate(zip(parent_root["keccak256"], record["keccak256"])) if before != after]
assert changed == [16, 22]

parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN and parent_pins["bootstrapCount"] == 94
assert parent_pins["rawLimits"] == [50, 324338] and parent_pins["diagnosticClassBound"] == 144
assert parent_pins["engine"]["bytes"] == 367235 and parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10 and parent_pins["exceptionKinds"] == 14
pre_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
pre_driver = (parent / "canonical-driver.go.txt").read_text().replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER)

if sys.argv[1] == "--prebuild":
    assert len(sys.argv) == 2
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == pre_coordinator
    assert (stage / "tools/Go.txt").read_text() == pre_driver
    phase = "prebuild"
else:
    assert len(sys.argv) == 3 and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
    pins = json.loads(Path(sys.argv[2]).read_text())
    bootstrap = dict(parent_pins["bootstrapSHA256"])
    bootstrap.update({"RuntimeException": RUNTIME_SHA256, "IndexOutOfBoundsException": INDEX_SHA256})
    expected = {
        **{key: value for key, value in parent_pins.items() if key != "worker"},
        "basis": "aaea6e3ee", "parentEvidence": "parent-aaea6e3ee", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 367235, "bootstrapCount": 94,
        "bootstrapSHA256": bootstrap, "diagnosticClassBound": 144,
        "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
    assert pins["coordinator"]["bytes"] == parent_pins["coordinator"]["bytes"] == 5394
    coordinator = replace_exact(pre_coordinator, parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coordinator
    driver = pre_driver
    for before, after in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        driver = replace_exact(driver, before, after)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        driver, count = re.subn(pattern, replacement, driver)
        assert count == 1
    assert (stage / "tools/Go.txt").read_text() == driver
    phase = "built"

fixtures = (stage / "tools/generate_fixtures.py").read_text()
gate = (stage / "tools/gate.py").read_text()
for label in (
    "index-out-of-bounds-string-empty", "index-out-of-bounds-string-ascii",
    "index-out-of-bounds-string-null", "index-out-of-bounds-string-uncaught",
    "index-out-of-bounds-string-uninitialized", "runtime-exception-throwable-omitted",
    "runtime-exception-message-throwable-omitted",
):
    assert '"' + label + '"' in fixtures and '"' + label + '"' in gate
assert "q_equivalent(label, label, index_out_of_bounds_string_initialized)" in gate
assert "whole_gate_seconds <= 1200" in gate and "canonical-receipts" in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "phase": phase, "basis": "aaea6e3ee", "domain": DOMAIN,
    "bootstrapImages": 94, "bootstrapRoot": record["bootstrapRoot"],
    "runtimeException": record["runtimeException"], "indexOutOfBoundsException": record["indexOutOfBoundsException"],
    "rawLimits": [50, 324338], "diagnosticClassBound": 144,
    "runtimeBaseline": 367235, "runtimeCap": 393216,
}, indent=2))
