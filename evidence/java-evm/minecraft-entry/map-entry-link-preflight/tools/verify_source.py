#!/usr/bin/env python3
"""Pin the generated-only Map.Entry append to the raw65 source basis.

Only image95, its bootstrap reservation/layout/root commitments, diagnostic bound,
and fresh local domain/address commitments move.  The verifier regenerates the
nested Java-8 image, parses its metadata without executing it, independently
recomputes the ordered bootstrap root, and rejects artifacts/classes/JARs.
"""
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
parent = stage.parent / "classcount65-byte381732-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

OLD_DOMAIN = "MC-INTEGER-HIGHEST-ONE-BIT-P2"
DOMAIN = "MC-MAP-ENTRY-LINK-P1"
OLD_ENGINE_ADDRESS = "4d432d494e542d484947484553542d4249542d33"
ENGINE_ADDRESS = "4d434d41502d454e5452592d4c494e4b2d503031"
OLD_OWNER_ADDRESS = "4d432d494e542d484947484553542d4249542d34"
OWNER_ADDRESS = "4d434d41502d454e5452592d4c494e4b2d4f3031"
OLD_ENGINE = {
    "bytes": 377409,
    "initSHA256": "ba29504da6b286591c0ac03eda77673ca5f436a880ebc613194e89828161c57a",
    "runtimeSHA256": "76ced9b94e49066523f55c00c11fbce5402caf3c166a3df030b83d8f8869ae0a",
    "runtimeKeccak256": "1624e883bdaf4458be83917fd36006c0d7e9695361a856eaf5943488a3c54dec",
}
ENGINE = {
    "bytes": 376562,
    "initSHA256": "d992af6f052c56c64794ed8d5ca906a1df6464aa7e42f843d9516a2f6df9816f",
    "runtimeSHA256": "d38d37e5f90f5820045466fdc3e2c17a90284c892160cb5ae3fe793107f120e1",
    "runtimeKeccak256": "9af3daf43ee24ce3783d432fa97761ea6599d913e5b978ccb41d44dfa3927636",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "0c8b367bec5ffaa9eb69178308d14713db08d0c8e73d6a02166e0123d6b54668",
    "runtimeSHA256": "26c843fd0933187e3a47f6d6b562483c07293d989a23e7e8b8357bc9b32f9daa",
    "runtimeKeccak256": "92207bf32b49497db710194b1e91beac3cef7927ae4c4f31138326ea2fd93528",
}
MAP_ENTRY_SHA256 = "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5"
MAP_ENTRY_KECCAK = "47bd965aa8c05997905d9d71684cc4409974e23e06bc6d360d9f06f82099e4ac"
ROOT = "9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622"
DBOOT = "62a8b6371369a352e74f30bb6f534ca8044aa0a7132a0b9c8807959554dbd3b7"


def exact(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def local_text(relative):
    return (stage / relative).read_text()


def image_from_function(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    body = text[start:end if end >= 0 else len(text)]
    values = re.findall(r'hex"([0-9a-f]+)"', body)
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def class_metadata(data):
    """Small class-file metadata reader; no Code is parsed or evaluated."""
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


source = local_text("bootstrap/java/util/Map.java")
assert source == """package java.util;

public interface Map<K,V> {
    public static interface Entry<K,V> {
        K getKey();
        V getValue();
        V setValue(V value);
        boolean equals(Object o);
        int hashCode();
    }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="map-entry-link-verify-", dir=root / "build") as temporary:
    temporary = Path(temporary)
    out = temporary / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out,
                    stage / "bootstrap/java/util/Map.java"], check=True)
    image = (out / "java/util/Map$Entry.class").read_bytes()
assert len(image) == 448 and hashlib.sha256(image).hexdigest() == MAP_ENTRY_SHA256
assert image.hex() == local_text("bootstrap/java/util/Map$Entry.class.hex").strip()
assert local_text("bootstrap/java/util/Map$Entry.sha256").split()[0] == MAP_ENTRY_SHA256
meta = class_metadata(image)
assert (meta["access"], meta["this"], meta["super"], meta["interfaces"], meta["fields"]) == (
    0x0601, "java/util/Map$Entry", "java/lang/Object", [], [])
expected_methods = [
    (0x0401, "getKey", "()Ljava/lang/Object;"),
    (0x0401, "getValue", "()Ljava/lang/Object;"),
    (0x0401, "setValue", "(Ljava/lang/Object;)Ljava/lang/Object;"),
    (0x0401, "equals", "(Ljava/lang/Object;)Z"),
    (0x0401, "hashCode", "()I"),
]
assert [(access, name, descriptor) for access, name, descriptor, _ in meta["methods"]] == expected_methods
assert all("Code" not in [name for name, _ in attrs] for _, _, _, attrs in meta["methods"])
assert [name for name, _ in meta["attrs"]] == ["Signature", "InnerClasses"]
assert b"comparingBy" not in image and b"Comparator" not in image

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(local_text("build-pins.json"))
assert parent_pins["rawLimits"] == [65, 381732] and parent_pins["bootstrapCount"] == 94
assert parent_pins["diagnosticClassBound"] == 159 and parent_pins["engine"] == OLD_ENGINE
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "classcount65-byte381732-preflight",
    "parentEvidence": "classcount65-byte381732-preflight/{engine,coordinator,tools}",
    "domain": DOMAIN, "bootstrapCount": 95, "bootstrapRoot": ROOT,
    "diagnosticClassBound": 160, "address": "0x" + ENGINE_ADDRESS,
    "owner": "0x" + OWNER_ADDRESS, "engine": ENGINE, "coordinator": COORDINATOR,
    "worker": "map-entry-link",
})
expected_pins["bootstrapSHA256"] = {**parent_pins["bootstrapSHA256"], "MapEntry": MAP_ENTRY_SHA256}
expected_pins["mapEntry"] = {"slot": 94, "bytes": 448, "sha256": MAP_ENTRY_SHA256,
                             "keccak256": MAP_ENTRY_KECCAK}
assert pins == expected_pins
assert pins["runtimeCap"] == 393216 and pins["engine"]["bytes"] <= pins["runtimeCap"]
assert pins["rawLimits"] == parent_pins["rawLimits"] and pins["integer"] == parent_pins["integer"]

parent_engine = parent_text("engine/MCEntryInterpreter.sol")
map_image = image_from_function(parent_engine, "_bootstrapMap")
integer_image = image_from_function(parent_engine, "_bootstrapInteger")
assert hashlib.sha256(map_image).hexdigest() == "52949052cb75be6d7351abfe7c494bfeb938ffcf1fac1f1ad63edc6f65e530e3"
assert hashlib.sha256(integer_image).hexdigest() == pins["integer"]["sha256"]
engine = exact(parent_engine, OLD_DOMAIN, DOMAIN, 9)
engine = exact(engine, "new bytes32[](94)", "new bytes32[](95)")
engine = exact(engine, '''        // SecurityManager is append-only image94 with only Object-chaining construction.
        h[93] = DBOOT_SECURITY_MANAGER;
        return keccak256(abi.encode(DBOOT, h));''', '''        // SecurityManager is append-only image94 with only Object-chaining construction.
        h[93] = DBOOT_SECURITY_MANAGER;
        // Map.Entry is append-only image95: public static nested interface, core five abstract methods only.
        h[94] = keccak256(_bootstrapMapEntry());
        return keccak256(abi.encode(DBOOT, h));''')
engine = exact(engine, "uint256 count = inputCount + 88 + (suppliedObject ? 0 : 1)",
               "uint256 count = inputCount + 89 + (suppliedObject ? 0 : 1)")
engine = exact(engine, '''            || _isNamedClass(c, bytes("java/util/SortedMap"))
            || _isNamedClass(c, bytes("java/util/Objects"));''', '''            || _isNamedClass(c, bytes("java/util/SortedMap"))
            || _isNamedClass(c, bytes("java/util/Objects"))
            || _isNamedClass(c, bytes("java/util/Map$Entry"));''')
engine = exact(engine, '''        // SecurityManager image94 exposes only public Object-chaining <init>().
        p.classes[classSlot + 54].data = _bootstrapSecurityManager();
    }''', '''        // SecurityManager image94 exposes only public Object-chaining <init>().
        p.classes[classSlot + 54].data = _bootstrapSecurityManager();
        // Map.Entry is the append-only image95; Map itself remains byte-for-byte pinned.
        p.classes[classSlot + 55].data = _bootstrapMapEntry();
    }''')
security = '''    // Image94 has no fields, checks, policy, native, or other member.
    function _bootstrapSecurityManager() private pure returns (bytes memory) { return hex"cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100196a6176612f6c616e672f53656375726974794d616e616765720100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"; }
'''
# Keep the literal source reconstruction readable while still pinning it exactly.
assert security in engine
entry = security + '\n    // Exact Java 8 Map.Entry nested interface: five core abstract methods, no Code/default helpers.\n    function _bootstrapMapEntry() private pure returns (bytes memory) { return hex"' + image.hex() + '"; }\n'
engine = exact(engine, security, entry)
assert local_text("engine/MCEntryInterpreter.sol") == engine
assert image_from_function(engine, "_bootstrapMap") == map_image
assert image_from_function(engine, "_bootstrapInteger") == integer_image
assert image_from_function(engine, "_bootstrapMapEntry") == image

coordinator = exact(parent_text("coordinator/MCEntryCoordinator.sol"), OLD_DOMAIN, DOMAIN, 4)
coordinator = exact(coordinator, OLD_ENGINE_ADDRESS, ENGINE_ADDRESS)
coordinator = exact(coordinator, OLD_ENGINE["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert local_text("coordinator/MCEntryCoordinator.sol") == coordinator

go = exact(parent_text("tools/Go.txt"), OLD_DOMAIN, DOMAIN, 6)
go = exact(go, OLD_OWNER_ADDRESS, OWNER_ADDRESS)
go = exact(go, OLD_ENGINE_ADDRESS, ENGINE_ADDRESS)
go = exact(go, OLD_ENGINE["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, OLD_ENGINE["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
go = exact(go, parent_pins["coordinator"]["runtimeKeccak256"], COORDINATOR["runtimeKeccak256"])
go = exact(go, "377409", "376562", 2)
assert local_text("tools/Go.txt") == go
for relative in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert local_text("tools/" + relative) == exact(parent_text("tools/" + relative), "classes<=159", "classes<=160")
for relative in ("engine/build.js", "coordinator/build.js", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert (stage / relative).read_bytes() == (parent / relative).read_bytes(), relative

# Rebuild the 95 ordered image hash list from local source, rather than trusting
# a parent root or a runtime constant.  The node code uses Keccak-256 from the
# pinned local node_modules package and the exact ABI encoding of bytes32[].
root_body = engine[engine.index("function _bootstrapRoot"):engine.index("function _prepare")]
assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', root_body)
assert len(assignments) == 95 and [int(index) for index, _, _ in assignments] == list(range(95))
leaf_rows = []
for _, function, constant in assignments:
    if function:
        leaf_rows.append({"image": image_from_function(engine, function).hex()})
    else:
        start = engine.index("bytes32 private constant " + constant)
        body = engine[start:engine.index(";", start)]
        folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', body)
        if folded:
            leaf_rows.append({"image": folded.group(1)})
        else:
            literal = re.search(r'= hex"([0-9a-f]+)"', body)
            assert literal, (constant, body)
            leaf_rows.append({"hash": literal.group(1)})
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
script = """const {keccak256}=require('js-sha3');const rows=JSON.parse(process.argv[1]);const hs=rows.map(x=>x.image?keccak256(Buffer.from(x.image,'hex')):x.hash);const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');const r=keccak256(Buffer.from(w(d)+w('40')+w(hs.length.toString(16))+hs.map(w).join(''),'hex'));console.log(JSON.stringify({d,r,hs}));"""
env = {**os.environ, "NODE_PATH": str(node_modules)}
independent = json.loads(subprocess.check_output(["node", "-e", script, json.dumps(leaf_rows),
                                                   "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"],
                                                  cwd=root, env=env, text=True))
assert independent["d"] == DBOOT and independent["r"] == ROOT and independent["hs"][94] == MAP_ENTRY_KECCAK
record = json.loads(local_text("root-commitment.json"))
assert record["domain"] == DOMAIN and record["dboot"] == DBOOT and record["bootstrapRoot"] == ROOT
assert record["bootstrapCount"] == 95 and record["keccak256"] == independent["hs"]
assert record["order"][-1] == "Map$Entry" and len(record["order"]) == 95

assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({
    "basis": pins["basis"], "domain": DOMAIN, "bootstrapImages": 95,
    "mapEntry": pins["mapEntry"], "bootstrapRoot": ROOT,
    "rawLimits": pins["rawLimits"], "diagnosticClassBound": 160,
    "engine": ENGINE, "coordinator": COORDINATOR,
    "verification": "javac-image+metadata+exact-parent-delta+independent-ordered-root",
}, indent=2))
