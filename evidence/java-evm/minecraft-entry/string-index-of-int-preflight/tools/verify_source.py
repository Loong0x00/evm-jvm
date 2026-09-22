#!/usr/bin/env python3
"""Verify the exact String.indexOf(int) image-only delta from raw68/394767."""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount68-byte394767-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "engine/MCEntryInterpreter.sol": "beb29e5a29ea3499bd30fbd091082fb70e74b7cf2a35623d7e6f18c0714b1afc",
    "coordinator/MCEntryCoordinator.sol": "70a9f78455d430816cd3b5dc38a2591d98dbc3d2c304bcc371696525c5fb7146",
    "tools/Go.txt": "1979842275fa444a44ff64b0c4859b0f765823d68fe5af21f8ee31b90b8cfc53",
    "root-commitment.json": "97991182d609e62a4989bf11c1bbedbd4c1f1bbdb490be3666a39d7777b20535",
    "build-pins.json": "1ea7a2f89474ed4c6d1a5073c346e1cdd15b9e801d4718cacdbab0d6582fdacd",
    "tools/checkpoint_diagnostic.py": "83c9f0e0910b73fba041b10678f0cf068b04735641940214f7fec142c23d7150",
    "tools/checkpoint_frames.py": "83c9f0e0910b73fba041b10678f0cf068b04735641940214f7fec142c23d7150",
    "tools/strip_stackmap.py": "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be",
    "tools/verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "bootstrap/java/util/Map.java": "8df987e8775bb1c31656bc49e336d5ad3ea6534a398feaa8a396fc81268c620d",
    "bootstrap/java/util/Map$Entry.class.hex": "7b642c3d23dca9a49a44a6fbbee8c3f6d3ae78f5427863e5bd098c2a949521b9",
    "bootstrap/java/util/Map$Entry.sha256": "155b108d5a541239f369b371408830b5cb0dc9e28529c8ba6d924d3faaa90f07",
}
PARENT_STRING_SHA256 = "04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231"
STRING_SHA256 = "42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec"
STRING_KECCAK = "260c4d3836b0b6b5d7ceacb7eed84135b60f2a14a831220ecdb5906accb741d0"
ROOT = "2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d"
ENGINE = {
    "bytes": 377043,
    "initSHA256": "f6d2f0e9c51196812a57fe206383e1f352e2cb4f752fd9bf50e6175f0ef4109e",
    "runtimeSHA256": "6e92a803536a519c6228c5fd6e9db4209860d8f2de6f966408cd02024f227984",
    "runtimeKeccak256": "1f01c5601c945c9bd69019e6717172c1e3024976fa8019d87e7b682597c4b069",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "bbe5f21c89a69c45bac668e975eacafa3b6463446bf8d8edc1da0043fedc7a3a",
    "runtimeSHA256": "73cf4e9288ab41967e4f49ff88575ef8e82f5b508580410683f8f1003960f956",
    "runtimeKeccak256": "50a2221f3a7131b43527c893fdc5a24bea586fc7a9e06409a2c6f2ff9f329810",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function_image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    body = text[start:end if end >= 0 else len(text)]
    values = re.findall(r'hex"([0-9a-f]+)"', body)
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def read_u2(data, at):
    return int.from_bytes(data[at:at + 2], "big"), at + 2


def read_u4(data, at):
    return int.from_bytes(data[at:at + 4], "big"), at + 4


def skip_attributes(data, at, count):
    attrs = []
    for _ in range(count):
        name, at = read_u2(data, at)
        size, at = read_u4(data, at)
        assert at + size <= len(data)
        attrs.append((name, data[at:at + size]))
        at += size
    return attrs, at


def methods(data):
    assert data[:8] == b"\xca\xfe\xba\xbe\x00\x00\x00\x34"
    cp_count, at = read_u2(data, 8)
    cp = [None] * cp_count
    index = 1
    while index < cp_count:
        tag = data[at]; at += 1
        if tag == 1:
            n, at = read_u2(data, at)
            cp[index] = (tag, data[at:at + n].decode("utf-8"))
            at += n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; index += 1
        elif tag in (7, 8, 16): at += 2
        elif tag in (9, 10, 11, 12, 18): at += 4
        elif tag == 15: at += 3
        else: raise AssertionError(("bad constant tag", tag, index))
        index += 1
    _, at = read_u2(data, at)  # access
    _, at = read_u2(data, at)  # this
    _, at = read_u2(data, at)  # super
    interfaces, at = read_u2(data, at); at += interfaces * 2
    fields, at = read_u2(data, at)
    for _ in range(fields):
        at += 6
        count, at = read_u2(data, at)
        _, at = skip_attributes(data, at, count)
    count, at = read_u2(data, at)
    out = {}
    for _ in range(count):
        access, at = read_u2(data, at)
        name, at = read_u2(data, at)
        descriptor, at = read_u2(data, at)
        attrs_count, at = read_u2(data, at)
        attrs, at = skip_attributes(data, at, attrs_count)
        key = (cp[name][1], cp[descriptor][1])
        assert key not in out
        out[key] = (access, [(cp[attr_name][1], payload) for attr_name, payload in attrs])
    assert at <= len(data)
    return out


def code_attribute(attrs):
    code = [payload for name, payload in attrs if name == "Code"]
    assert len(code) == 1
    payload = code[0]
    max_stack = int.from_bytes(payload[:2], "big")
    max_locals = int.from_bytes(payload[2:4], "big")
    length = int.from_bytes(payload[4:8], "big")
    assert 8 + length <= len(payload)
    return max_stack, max_locals, payload[8:8 + length]


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
parent_pins = json.loads((parent / "build-pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
assert parent_pins["bootstrapCount"] == 95
assert parent_pins["rawLimits"] == [68, 394767]
assert parent_pins["diagnosticClassBound"] == 163
assert parent_pins["bootstrapSHA256"]["String"] == PARENT_STRING_SHA256
assert parent_pins["integer"] == {"slot": 70, "bytes": 2039,
    "sha256": "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd",
    "keccak256": "1a698ef9f803879a7f45c3613a679295cd1db22528c2c0e986fc4f9a6b845ba9"}
assert parent_pins["mapEntry"] == {"slot": 94, "bytes": 448,
    "sha256": "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5",
    "keccak256": "47bd965aa8c05997905d9d71684cc4409974e23e06bc6d360d9f06f82099e4ac"}

source = stage / "bootstrap/java/lang/String.java"
hex_path = stage / "bootstrap/java/lang/String.class.hex"
sha_path = stage / "bootstrap/java/lang/String.sha256"
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="java-diff-mc-string-index-of-int-verify-", dir=root / "build") as temp:
    out = Path(temp) / "classes"
    out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, source], check=True)
    generated = (out / "java/lang/String.class").read_bytes()
image = bytes.fromhex(hex_path.read_text().strip())
assert generated == image
assert len(image) == 1773 and sha_path.read_text().strip() == STRING_SHA256
assert hashlib.sha256(image).hexdigest() == STRING_SHA256
old_image = function_image((parent / "engine/MCEntryInterpreter.sol").read_text(), "_bootstrapString")
new_image = function_image((stage / "engine/MCEntryInterpreter.sol").read_text(), "_bootstrapString")
assert hashlib.sha256(old_image).hexdigest() == PARENT_STRING_SHA256
assert new_image == image
old_methods = methods(old_image)
new_methods = methods(new_image)
new_key = ("indexOf", "(I)I")
assert set(new_methods) == set(old_methods) | {new_key}
for key, (old_access, old_attrs) in old_methods.items():
    new_access, new_attrs = new_methods[key]
    assert new_access == old_access, key
    assert [name for name, _ in new_attrs] == [name for name, _ in old_attrs], key
    old_code = [payload for name, payload in old_attrs if name == "Code"]
    new_code = [payload for name, payload in new_attrs if name == "Code"]
    assert len(old_code) == len(new_code) <= 1, key
    if old_code:
        old_stack, old_locals, old_bytes = code_attribute(old_attrs)
        new_stack, new_locals, new_bytes = code_attribute(new_attrs)
        # javac may renumber pre-existing constant-pool references after adding
        # a method, but it must retain every prior method's Code dimensions.
        assert (new_stack, new_locals, len(new_bytes)) == (old_stack, old_locals, len(old_bytes)), key
access, attrs = new_methods[new_key]
assert access == 0x0001 and len(attrs) == 1 and attrs[0][0] == "Code"
max_stack, max_locals, code = code_attribute(attrs)
assert max_stack >= 3 and max_locals >= 6 and code[-1] == 0xac
assert all(name != "indexOf" for name, _ in old_methods)

parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
old_hex = old_image.hex()
expected_engine = parent_engine.replace(old_hex, image.hex())
assert parent_engine.count(old_hex) == 1
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == expected_engine
parent_coord = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coord = parent_coord.replace(parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert parent_coord.count(parent_pins["engine"]["runtimeKeccak256"]) == 1
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_coord
parent_go = (parent / "tools/Go.txt").read_text()
expected_go = parent_go
for old, new in (
    (parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"]),
    ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"]),
    ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"]),
):
    assert expected_go.count(old) == 1, old
    expected_go = expected_go.replace(old, new)
assert expected_go.count("376562") == 2
expected_go = expected_go.replace("376562", "377043")
assert (stage / "tools/Go.txt").read_text() == expected_go

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py", "tools/strip_stackmap.py", "tools/verify_receipts.js", "engine/build.js", "coordinator/build.js",
                 "bootstrap/java/util/Map.java", "bootstrap/java/util/Map$Entry.class.hex", "bootstrap/java/util/Map$Entry.sha256"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

node_env = dict(os.environ, NODE_PATH=str(root / "jvmevm/runtime/node_modules"))
commitment = json.loads(subprocess.check_output([
    "node", here / "bootstrap_commitment.js", stage / "engine/MCEntryInterpreter.sol",
    parent / "root-commitment.json", stage / "root-commitment.json", hex_path,
], cwd=root, env=node_env, text=True))
assert commitment == {
    "bootstrapCount": 95, "changedSlot": 26,
    "parentStringKeccak256": "fa2609af1a1b40f8ede90e7d8f34dfb2bd1586edfa247a02f33e48c5439487be",
    "stringKeccak256": STRING_KECCAK, "bootstrapRoot": ROOT, "unchangedLeaves": 94,
    "scope": "ordered bootstrap image/root verification only; no class or resource execution authority",
}
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "phase": "built", "basis": "classcount68-byte394767-preflight",
    "parentEvidence": "classcount68-byte394767-preflight/{engine,coordinator,tools,bootstrap}",
    "domain": "MC-STRING-INDEX-OF-INT-P1", "bootstrapRoot": ROOT,
    "worker": "string-index-of-int", "engine": ENGINE, "coordinator": COORDINATOR,
    "string": {"slot": 26, "bytes": 1773, "sha256": STRING_SHA256,
        "keccak256": STRING_KECCAK, "surface": "accepted String surface plus indexOf(int) only",
        "java8": "javac -source 8 -target 8 -g:none"},
})
expected_pins["bootstrapSHA256"]["String"] = STRING_SHA256
assert pins == expected_pins
assert pins["bootstrapCount"] == 95 and pins["rawLimits"] == [68, 394767]
assert pins["diagnosticClassBound"] == 163 and pins["runtimeCap"] == 393216
assert pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14
assert pins["integer"] == parent_pins["integer"] and pins["mapEntry"] == parent_pins["mapEntry"]

print(json.dumps({
    "basis": pins["basis"], "bootstrapCount": pins["bootstrapCount"],
    "changedBootstrapSlot": 26, "string": pins["string"], "bootstrapRoot": ROOT,
    "rawLimits": pins["rawLimits"], "diagnosticClassBound": pins["diagnosticClassBound"],
    "engine": ENGINE, "coordinator": COORDINATOR,
    "verification": "Java8-rebuilt-String+method-metadata+sole-image-source-delta+independent-ordered-root",
}, indent=2))
