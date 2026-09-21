#!/usr/bin/env python3
"""Source/image/root verifier for the generated-only guest-stack-trace stage.

It performs no original-artifact, network, Minecraft, or world operation.  Node
is used only for Keccak (the same pinned local dependency used by engine build).
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

stage = Path(__file__).resolve().parents[1]
root = stage.parents[3]
scratch = Path(sys.argv[1]).resolve()
assert root / "build" in scratch.parents and not scratch.exists()
scratch.mkdir()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent = (stage.parent / "parent-afc1785d4/artifacts/engine/MCEntryInterpreter.sol").read_text()
parent_record = json.loads((stage / "parent-root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert record["domain"] == "MC-THROW-STACK-TRC01"
assert record["bootstrapCount"] == 94 == len(record["order"]) == len(record["keccak256"])
assert parent_record["bootstrapCount"] == 94 and parent_record["order"] == record["order"]
assert "MAX_RAW_CLASSES = 50" in engine
assert "MAX_RAW_BYTES = 324338" in engine
assert "inputCount + 88" in engine and "new ClassInfo[](count)" in engine
assert "MAX_FRAMES = 128" in engine and "MC-THROW-STACK-TRC01" in engine
assert "return 14;" in engine
assert "bytes(\"getStackTrace\")" in engine
assert "bytes(\"()[Ljava/lang/StackTraceElement;\")" in engine
assert "_snapshotGuestStackTrace(" in engine
assert "frames[count - 1 - i]" in engine
assert "_classNameUnits(classes[active.classIndex])" in engine
assert "_guestFrameMethodNameUnits(" in engine
assert "bytes(\"java/lang/StackTraceElement\")" in engine
assert "_bootstrapThread()" in engine and "bytes(\"getStackTrace\")" in engine
assert "DBOOT_STACK_TRACE_ELEMENT" in engine
# The only new global binding is 14; bindings 1..13 retain their historical
# spellings. String-local binding10 is deliberately a separate dispatch path.
for binding in range(1, 14):
    assert f"return {binding};" in engine
assert engine.count("return 14;") == 1

# Rebuild the two Java-8 images and prove both the committed source hex and the
# embedded Solidity literal are exactly those bytes.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
classes = scratch / "classes"; classes.mkdir()
sources = sorted((stage / "bootstrap").rglob("*.java"))
subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, *map(str, sources)], check=True)
changed = {"Throwable": 5, "StackTraceElement": 90}

def fn_hex(source, name):
    m = re.search(r"function _bootstrap" + re.escape(name) + r"\([^)]*\)[^{]*\{(.*?)(?=\n    function |\Z)", source, re.S)
    assert m, name
    literals = re.findall(r'hex"([0-9a-f]+)"', m.group(1))
    assert len(literals) == 1, (name, len(literals))
    return literals[0]

def keccak(hex_text):
    code = "const {keccak256}=require('./jvmevm/runtime/node_modules/js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));"
    return subprocess.check_output(["node", "-e", code, hex_text], cwd=root, text=True)

for name, slot in changed.items():
    actual = (classes / "java/lang" / (name + ".class")).read_bytes()
    source_hex = (stage / "bootstrap/java/lang" / (name + ".class.hex")).read_text().strip()
    assert actual.hex() == source_hex == fn_hex(engine, name)
    image = record["changedLeaves"][name]
    assert image["slot"] == slot and image["bytes"] == len(actual)
    assert image["sha256"] == hashlib.sha256(actual).hexdigest()
    assert image["keccak256"] == keccak(actual.hex()) == record["keccak256"][slot]

# Compute each literal-or-constant leaf exactly as _bootstrapRoot does.  This
# makes unchanged leaves dynamic rather than copying a whole-root assertion.
def root_hashes(source):
    block = re.search(r"function _bootstrapRoot\(\).*?\{(.*?)return keccak256\(abi\.encode\(DBOOT, h\)\);", source, re.S).group(1)
    values = []
    for slot, name in enumerate(record["order"]):
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
assert [i for i, (a, b) in enumerate(zip(actual_parent, actual)) if a != b] == [5, 90]

# Match Solidity's abi.encode(bytes32, bytes32[]) layout: DBOOT, offset=64,
# array length, then fixed-width leaf hashes.
dboot = keccak(b"JVMEVM:MC-THROW-STACK-TRC01:BOOTSTRAP:1".hex())
payload = bytes.fromhex(dboot) + (64).to_bytes(32, "big") + len(actual).to_bytes(32, "big") + b"".join(bytes.fromhex(v) for v in actual)
assert dboot == record["dboot"] and keccak(payload.hex()) == record["bootstrapRoot"]

summary = {
    "bootstrapCount": 94, "changedSlots": changed,
    "changedImageSHA256": {n: record["changedLeaves"][n]["sha256"] for n in changed},
    "bootstrapRoot": record["bootstrapRoot"], "checks": "source-java8-images-runtime-derived-ordered-root",
}
(scratch / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
