#!/usr/bin/env python3
"""Verify the generated-only Locale.ROOT append from parent-949992642."""
from pathlib import Path
import copy
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
parent = stage.parent / "parent-949992642"
prior = stage.parent / "classcount69-byte449904-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

DOMAIN0 = "MC-MAP-ENTRY-LINK-X3"
DOMAIN = "MC-LOCALE-ROOT-P1"
ENGINE0 = "4d434d41502d454e5452592d4c494e4b2d503133"
ENGINE = "4d432d4c4f43414c452d524f4f542d5030303031"
OWNER0 = "4d434d41502d454e5452592d4c494e4b2d4f3133"
OWNER = "4d432d4c4f43414c452d524f4f542d4f30303031"
LOCALE_SHA256 = "8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31"
LOCALE_KECCAK = "cb4ec03973fafc97a59f911f9c0b46f60b848ef0233807a96f1cdff84d904354"
ROOT = "9d6ac1b79a64b66e5a4654eaf1b3afecafe61c3cff650b825152d278325c7e6c"
DBOOT = "b8bdf23b7bc528577b8fd49cfec135b9ff385487a2e959a7821e3fd2f3c884ab"
ENGINE_PIN = {
    "bytes": 378675,
    "initSHA256": "adf77c5ffe55d755c58a79188b3a1ca2e0b8150919af1864b49d4d829b8524d2",
    "runtimeSHA256": "f3d2b669b05e1ae04e7b5bfa961a25d2dad132a0c12fc78aedd3fefa141ed47d",
    "runtimeKeccak256": "536e756899b808d5e91226ff347a310c2acc1afafb2311efad02fa68f3343328",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "03e47e650e17de1cb91f13b53b4189acb4922a579e1080d3da6715ef621f9338",
    "runtimeSHA256": "7a4eda307afc57e2371e5e582ddaf7e00cdd7d6dfb6253ec4682e3d1f42fa896",
    "runtimeKeccak256": "08b612b9a1b293bdad5e07243041c8a22c617230fac54039500a98caa29a5dc5",
}
PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "d5415711db17780be165fe772ba141c96002c72b41c4bb13d625819b7201e2b9",
    "artifacts/coordinator/MCEntryCoordinator.sol": "faa2e67b95b5edc905c13b1d7025202c84ecda886eee9494950c78f3523707c7",
    "canonical-driver.go.txt": "97647c9e99c8a73d36e53b0e45406539305c6c589d89c686ba5dba1e0f1b8cdd",
    "checkpoint_diagnostic.py": "9eb0ab82cfc0f4518116c6a89e563f9fc9bb26a2d786fb178edd6370cfa4a1f2",
    "checkpoint_frames.py": "9eb0ab82cfc0f4518116c6a89e563f9fc9bb26a2d786fb178edd6370cfa4a1f2",
    "pins.json": "40b6c07e190fbcb5706391d6db45a939349e31b0daf2437d9b9d4408f1cad12b",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PRIOR_ROOT_SHA256 = "fe5a889c9717490f409518790b5cec33fd1bf7b1ae5352fb9e9260a05237552f"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)


def image_from_function(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def class_metadata(data):
    """Metadata-only Java-8 class reader; it does not interpret Code."""
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8
    count = int.from_bytes(data[at:at + 2], "big"); at += 2
    cp = [None] * count
    index = 1
    while index < count:
        tag = data[at]; at += 1
        if tag == 1:
            n = int.from_bytes(data[at:at + 2], "big"); at += 2
            cp[index] = (tag, data[at:at + n].decode("utf-8")); at += n
        elif tag in (7, 8, 16):
            cp[index] = (tag, int.from_bytes(data[at:at + 2], "big")); at += 2
        elif tag in (3, 4):
            cp[index] = (tag, data[at:at + 4]); at += 4
        elif tag in (5, 6):
            cp[index] = (tag, data[at:at + 8]); at += 8; index += 1
        elif tag in (9, 10, 11, 12, 18):
            cp[index] = (tag, data[at:at + 4]); at += 4
        elif tag == 15:
            cp[index] = (tag, data[at:at + 3]); at += 3
        else:
            raise AssertionError(("unexpected cp tag", tag, index))
        index += 1

    def u2():
        nonlocal at
        value = int.from_bytes(data[at:at + 2], "big"); at += 2
        return value

    def u4():
        nonlocal at
        value = int.from_bytes(data[at:at + 4], "big"); at += 4
        return value

    def utf(index):
        assert cp[index][0] == 1
        return cp[index][1]

    def class_name(index):
        assert cp[index][0] == 7
        return utf(cp[index][1])

    def attributes():
        nonlocal at
        result = []
        for _ in range(u2()):
            name = utf(u2()); n = u4()
            assert at + n <= len(data)
            result.append((name, data[at:at + n])); at += n
        return result

    access, this_class, super_class = u2(), u2(), u2()
    interfaces = [u2() for _ in range(u2())]
    fields = []
    for _ in range(u2()):
        field_access, name, descriptor = u2(), utf(u2()), utf(u2())
        fields.append((field_access, name, descriptor, attributes()))
    methods = []
    for _ in range(u2()):
        method_access, name, descriptor = u2(), utf(u2()), utf(u2())
        methods.append((method_access, name, descriptor, attributes()))
    attrs = attributes()
    assert at == len(data)
    return {
        "access": access, "this": class_name(this_class), "super": class_name(super_class),
        "interfaces": [class_name(value) for value in interfaces], "fields": fields,
        "methods": methods, "attrs": attrs,
    }


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
assert sha(prior / "root-commitment.json") == PRIOR_ROOT_SHA256
parent_pins = json.loads((parent / "pins.json").read_text())
prior_root = json.loads((prior / "root-commitment.json").read_text())
assert parent_pins["rawLimits"] == [69, 449904]
assert parent_pins["bootstrapCount"] == 95 and parent_pins["diagnosticClassBound"] == 164
assert parent_pins["bootstrapRoot"] == "2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d"
assert len(prior_root["keccak256"]) == 95 and prior_root["order"][-1] == "Map$Entry"

locale_source = """package java.util;

import java.io.Serializable;

public final class Locale implements Cloneable, Serializable {
    public static final Locale ROOT;

    private Locale() {}

    static {
        ROOT = new Locale();
    }
}
"""
assert (stage / "bootstrap/java/util/Locale.java").read_text() == locale_source
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="locale-root-verify-", dir=root / "build") as temporary:
    temporary = Path(temporary)
    source = temporary / "java/util/Locale.java"; source.parent.mkdir(parents=True)
    source.write_text(locale_source)
    out = temporary / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, source], check=True)
    locale = (out / "java/util/Locale.class").read_bytes()
assert len(locale) == 285 and hashlib.sha256(locale).hexdigest() == LOCALE_SHA256
assert locale.hex() == (stage / "bootstrap/java/util/Locale.class.hex").read_text().strip()
assert (stage / "bootstrap/java/util/Locale.sha256").read_text().split()[0] == LOCALE_SHA256
meta = class_metadata(locale)
assert (meta["access"], meta["this"], meta["super"], meta["interfaces"]) == (
    0x0031, "java/util/Locale", "java/lang/Object", ["java/lang/Cloneable", "java/io/Serializable"])
assert [(access, name, descriptor) for access, name, descriptor, _ in meta["fields"]] == [
    (0x0019, "ROOT", "Ljava/util/Locale;")]
assert [(access, name, descriptor) for access, name, descriptor, _ in meta["methods"]] == [
    (0x0002, "<init>", "()V"), (0x0008, "<clinit>", "()V")]
assert [name for name, _ in meta["attrs"]] == []
assert [attrs[0][1][8:8 + int.from_bytes(attrs[0][1][4:8], "big")] for _, _, _, attrs in meta["methods"]] == [
    bytes.fromhex("2ab70001b1"), bytes.fromhex("bb000259b70003b30004b1")]
assert all(b"getDefault" not in part and b"language" not in part and b"country" not in part for part in (locale,))

pins = json.loads((stage / "build-pins.json").read_text())
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "parent-949992642",
    "parentEvidence": "parent-949992642/{artifacts,canonical-driver,checkpoint,pins}",
    "domain": DOMAIN,
    "bootstrapCount": 96,
    "bootstrapRoot": ROOT,
    "diagnosticClassBound": 165,
    "address": "0x" + ENGINE,
    "owner": "0x" + OWNER,
    "engine": ENGINE_PIN,
    "coordinator": COORDINATOR_PIN,
    "worker": "locale-root",
})
expected_pins["bootstrapSHA256"] = {**parent_pins["bootstrapSHA256"], "Locale": LOCALE_SHA256}
expected_pins["locale"] = {
    "slot": 95, "bytes": 285, "sha256": LOCALE_SHA256, "keccak256": LOCALE_KECCAK,
    "surface": "ROOT singleton plus private Object-chaining constructor and <clinit> only",
    "java8": "javac -source 8 -target 8 -g:none",
}
assert pins == expected_pins
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["rawLimits"] == [69, 449904]
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = exact(parent_engine, DOMAIN0, DOMAIN, 9)
engine = exact(engine, "new bytes32[](95)", "new bytes32[](96)")
engine = exact(engine, '''        // Map.Entry is append-only image95: public static nested interface, core five abstract methods only.
        h[94] = keccak256(_bootstrapMapEntry());
        return keccak256(abi.encode(DBOOT, h));''', '''        // Map.Entry is append-only image95: public static nested interface, core five abstract methods only.
        h[94] = keccak256(_bootstrapMapEntry());
        // Locale is append-only image96: ROOT singleton only, with no locale state/API surface.
        h[95] = keccak256(_bootstrapLocale());
        return keccak256(abi.encode(DBOOT, h));''')
engine = exact(engine, "|| _isReservedSecurityManagerClass(users[i])) {", "|| _isReservedSecurityManagerClass(users[i])\n                || _isReservedLocaleClass(users[i])) {")
engine = exact(engine, "uint256 count = inputCount + 89 + (suppliedObject ? 0 : 1)", "uint256 count = inputCount + 90 + (suppliedObject ? 0 : 1)")
engine = exact(engine, '''        // Map.Entry is the append-only image95; Map itself remains byte-for-byte pinned.
        p.classes[classSlot + 55].data = _bootstrapMapEntry();
    }''', '''        // Map.Entry is the append-only image95; Map itself remains byte-for-byte pinned.
        p.classes[classSlot + 55].data = _bootstrapMapEntry();
        // Locale is append-only image96; <clinit> alone creates the sole ROOT instance.
        p.classes[classSlot + 56].data = _bootstrapLocale();
    }''')
engine = exact(engine, '''    // These classes are interpreter-owned images, not user-supplied platform
    // definitions. This prevents an input bundle from silently replacing the
    // construction/storage hierarchy used by original Properties allocation.
    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {''', '''    // Locale image96 is interpreter-owned so a raw bundle cannot replace its ROOT singleton.
    function _isReservedLocaleClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/util/Locale"));
    }

    // These classes are interpreter-owned images, not user-supplied platform
    // definitions. This prevents an input bundle from silently replacing the
    // construction/storage hierarchy used by original Properties allocation.
    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {''')
map_start = engine.index("    function _bootstrapMapEntry()")
map_end = engine.find("\n    function ", map_start + 1)
assert map_end >= 0
engine = engine[:map_end] + '''

    // Exact Java 8 Locale root: one public static final ROOT, a private Object-chain constructor, and <clinit> only.
    function _bootstrapLocale() private pure returns (bytes memory) { return hex"%s"; }
''' % locale.hex() + engine[map_end:]
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == engine
assert image_from_function(engine, "_bootstrapLocale") == locale
assert hashlib.sha256(image_from_function(engine, "_bootstrapString")).hexdigest() == parent_pins["bootstrapSHA256"]["String"]
assert hashlib.sha256(image_from_function(engine, "_bootstrapInteger")).hexdigest() == parent_pins["integer"]["sha256"]
assert hashlib.sha256(image_from_function(engine, "_bootstrapMapEntry")).hexdigest() == parent_pins["mapEntry"]["sha256"]

parent_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, DOMAIN0, DOMAIN, 4)
coord = exact(coord, ENGINE0, ENGINE)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE_PIN["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord

go = (parent / "canonical-driver.go.txt").read_text()
go = exact(go, DOMAIN0, DOMAIN, 6)
go = exact(go, OWNER0, OWNER)
go = exact(go, ENGINE0, ENGINE)
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE_PIN["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE_PIN["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR_PIN["runtimeKeccak256"])
go = exact(go, "377043", "378675", 2)
assert (stage / "tools/Go.txt").read_text() == go
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == exact((parent / name).read_text(), "classes<=164", "classes<=165")
for local, parent_relative in (("engine/build.js", "artifacts/engine/build.js"), ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / local).read_bytes() == (parent / parent_relative).read_bytes()

# Independently derive each ordered leaf and the ABI-encoded root. The first 95
# hashes must match the immutable parent list byte-for-byte before Locale appends.
root_body = engine[engine.index("function _bootstrapRoot"):engine.index("function _prepare")]
assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', root_body)
assert len(assignments) == 96 and [int(index) for index, _, _ in assignments] == list(range(96))
leaf_rows = []
for _, function, constant in assignments:
    if function:
        leaf_rows.append({"image": image_from_function(engine, function).hex()})
    else:
        begin = engine.index("bytes32 private constant " + constant)
        body = engine[begin:engine.index(";", begin)]
        folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', body)
        literal = re.search(r'= hex"([0-9a-f]+)"', body)
        assert folded or literal, (constant, body)
        leaf_rows.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
script = """const {keccak256}=require('js-sha3');const rows=JSON.parse(process.argv[1]);const hs=rows.map(x=>x.image?keccak256(Buffer.from(x.image,'hex')):x.hash);const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');const r=keccak256(Buffer.from(w(d)+w('40')+w(hs.length.toString(16))+hs.map(w).join(''),'hex'));console.log(JSON.stringify({d,r,hs}));"""
independent = json.loads(subprocess.check_output(["node", "-e", script, json.dumps(leaf_rows), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"], cwd=root, env={**os.environ, "NODE_PATH": str(node_modules)}, text=True))
assert independent["d"] == DBOOT and independent["r"] == ROOT
assert independent["hs"][:95] == prior_root["keccak256"]
assert independent["hs"][95] == LOCALE_KECCAK
record = json.loads((stage / "root-commitment.json").read_text())
assert record == {"domain": DOMAIN, "dboot": DBOOT, "bootstrapCount": 96, "bootstrapRoot": ROOT,
                  "order": prior_root["order"] + ["Locale"], "keccak256": independent["hs"]}
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"basis": pins["basis"], "bootstrapImages": 96, "locale": pins["locale"],
                  "rawLimits": pins["rawLimits"], "diagnosticClassBound": 165,
                  "bootstrapRoot": ROOT, "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN,
                  "verification": "javac-image+metadata+exact-parent-delta+independent-ordered-root"}, indent=2))
