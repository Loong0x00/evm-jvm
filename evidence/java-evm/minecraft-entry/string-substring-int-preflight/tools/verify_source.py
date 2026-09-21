#!/usr/bin/env python3
"""Verify the one-leaf String.substring(int) bootstrap update.

This generated-only verifier recompiles only the staged Java-8 String source,
recomputes all 94 ordered bootstrap leaves from Solidity, and never opens an
original/JAR/resource/world or contacts the network.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

stage = Path(__file__).resolve().parents[1]
root = stage.parents[3]
scratch = Path(sys.argv[1]).resolve()
assert root / "build" in scratch.parents and not scratch.exists()
scratch.mkdir()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent = (stage.parent / "parent-8ac912dd6/artifacts/engine/MCEntryInterpreter.sol").read_text()
parent_record = json.loads((stage / "parent-root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert record["domain"] == "MC-SUBSTRING-INT-00001"
assert record["bootstrapCount"] == 94 == len(record["order"]) == len(record["keccak256"])
assert parent_record["bootstrapCount"] == 94 and parent_record["order"] == record["order"]
assert "MAX_RAW_CLASSES = 50" in engine and "MAX_RAW_BYTES = 324338" in engine
assert "inputCount + 88" in engine and "new ClassInfo[](count)" in engine
assert "MAX_FRAMES = 128" in engine and "MC-SUBSTRING-INT-00001" in engine
# Global native bindings remain precisely 1..14. substring is only the next
# String-local binding and can never alter global-native validation.
for binding in range(1, 15):
    assert f"return {binding};" in engine
assert engine.count("return 14;") == 1
assert 'bytes("split")' in engine and 'return 10;' in engine
assert 'bytes("substring")' in engine and 'return 11;' in engine
assert 'bytes("(I)Ljava/lang/String;")' in engine
assert "function _substringString(" in engine
assert "if (begin == 0) return (receiverHandle, false);" in engine
assert "revert StringProfileError(1, pc);" in engine
assert "arena.nextHandle > MAX_HANDLES - 2" in engine
assert "_ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);" in engine

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
classes = scratch / "classes"; classes.mkdir()
source = stage / "bootstrap/java/lang/String.java"
subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source], check=True)
actual = (classes / "java/lang/String.class").read_bytes()
source_hex = (stage / "bootstrap/java/lang/String.class.hex").read_text().strip()
assert actual.hex() == source_hex

def fn_hex(source, name):
    m = re.search(r"function _bootstrap" + re.escape(name) + r"\([^)]*\)[^{]*\{(.*?)(?=\n    function |\Z)", source, re.S)
    assert m, name
    literals = re.findall(r'hex"([0-9a-f]+)"', m.group(1))
    assert len(literals) == 1, (name, len(literals))
    return literals[0]

def keccak(hex_text):
    code = "const {keccak256}=require('./jvmevm/runtime/node_modules/js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));"
    return subprocess.check_output(["node", "-e", code, hex_text], cwd=root, text=True)

image = record["changedLeaves"]["String"]
assert image["slot"] == 26 and image["bytes"] == len(actual)
assert image["sha256"] == hashlib.sha256(actual).hexdigest()
assert image["keccak256"] == keccak(actual.hex())
assert fn_hex(engine, "String") == actual.hex()

def root_hashes(source):
    block = re.search(r"function _bootstrapRoot\(\).*?\{(.*?)return keccak256\(abi\.encode\(DBOOT, h\)\);", source, re.S).group(1)
    values = []
    for slot, _ in enumerate(record["order"]):
        expr = re.search(r"h\[" + str(slot) + r"\] = ([^;]+);", block).group(1)
        normal = re.fullmatch(r"keccak256\(_bootstrap([A-Za-z0-9]+)\(\)\)", expr)
        if normal:
            values.append(keccak(fn_hex(source, normal.group(1))))
        else:
            constant = re.search(r"bytes32 private constant " + re.escape(expr) + r" = (.*?);", source).group(1)
            literal = re.search(r'hex"([0-9a-f]+)"', constant).group(1)
            values.append(keccak(literal) if constant.startswith("keccak256") else literal)
    return values

actual_parent = root_hashes(parent)
actual = root_hashes(engine)
assert actual_parent == parent_record["keccak256"]
assert actual == record["keccak256"]
assert [i for i, (a, b) in enumerate(zip(actual_parent, actual)) if a != b] == [26]
dboot = keccak(b"JVMEVM:MC-SUBSTRING-INT-00001:BOOTSTRAP:1".hex())
payload = bytes.fromhex(dboot) + (64).to_bytes(32, "big") + len(actual).to_bytes(32, "big") + b"".join(bytes.fromhex(v) for v in actual)
assert dboot == record["dboot"] and keccak(payload.hex()) == record["bootstrapRoot"]
summary = {"bootstrapCount": 94, "changedSlots": {"String": 26}, "changedImageSHA256": {"String": image["sha256"]}, "bootstrapRoot": record["bootstrapRoot"], "checks": "source-java8-string-image-runtime-derived-ordered-root"}
(scratch / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
