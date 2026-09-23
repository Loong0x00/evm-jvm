#!/usr/bin/env python3
"""Exact generated-only source/image verification for bootstrap image97 Random."""
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
base = stage.parent / "math-sqrt-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

DOMAIN_OLD = "MC-MATH-SQRT-P1"
DOMAIN = "MC-RANDOM-CLASS-P1"
ROOT = "7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887"
RANDOM_SHA = "8d2a1e974c79f6a2a0344a5c776f5feb7b7f09eb7431bd02d54d75518bf76bf3"
RANDOM_KECCAK = "7c7093faf1a5f9610a8a179f48e634e451e0621862af33c14ec409dc8d6ef184"
RANDOM_BYTES = 159
ADDRESS = "0x4d432d52414e444f4d2d434c4153532d50310000"
OWNER = "0x4d432d52414e444f4d2d434c4153532d50310001"
ENGINE = {"bytes": 383245, "initSHA256": "85eb323b0d10a75959b299534f455cf699dfd1d2bc81cf1331537152ab32659f", "runtimeSHA256": "520aa224c934bc0b0bd16d27646f922a76a3aeb6ec3c9b80edfeca9de5cc6c44", "runtimeKeccak256": "4906f920b37aff22f84c07b25290d2970e0b70f73e2da4f64242e2a4004077de"}
COORDINATOR = {"bytes": 5394, "initSHA256": "b3e676f2028dfb9f5d81ef6f27817dd95c79ac5307c19309c4097e2c476b570d", "runtimeSHA256": "68cc0846106f072f992c9eff86c7905e53e6615f64ec66f4b8ece850bd1a99d4", "runtimeKeccak256": "404a288b969f1fc96adb41e39d93fc1f6db9d88f850e56b4504494a83bfbe1dd"}


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:100], text.count(old), count)
    return text.replace(old, new)


def image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def expected_engine(math_engine, random_hex):
    text = exact(math_engine, DOMAIN_OLD, DOMAIN, 9)
    text = exact(text, 'bytes32 private constant DBOOT_MATH =',
                 f'bytes32 private constant DBOOT_RANDOM = hex"{RANDOM_KECCAK}";\n    bytes32 private constant DBOOT_MATH =')
    text = exact(text, 'bytes32[] memory h = new bytes32[](96);',
                 'bytes32[] memory h = new bytes32[](97);')
    text = exact(text, '        h[95] = keccak256(_bootstrapLocale());',
                 '        h[95] = keccak256(_bootstrapLocale());\n        h[96] = DBOOT_RANDOM;')
    text = exact(text, 'uint256 count = inputCount + 90 +', 'uint256 count = inputCount + 91 +')
    text = exact(text, '                || _isReservedLocaleClass(users[i])) {',
                 '                || _isReservedLocaleClass(users[i])\n'
                 '                || _isNamedClass(users[i], bytes("java/util/Random"))) {')
    text = exact(text, '        p.classes[classSlot + 56].data = _bootstrapLocale();',
                 '        p.classes[classSlot + 56].data = _bootstrapLocale();\n'
                 '        // Image97 appends after the exact prior96-image bootstrap tail.\n'
                 '        p.classes[classSlot + 57].data = _bootstrapRandom();')
    marker = '    function _bootstrapWeakReference() private pure returns (bytes memory) {'
    helper = ('    /// @dev Java 8 java.util.Random link/construction-only profile. No RNG state,\n'
              '    /// seeding source, or next* API is claimed; generated calls outside this exact\n'
              '    /// constructor surface fail through ordinary method resolution.\n'
              '    function _bootstrapRandom() private pure returns (bytes memory) { return hex"'
              + random_hex + '"; }\n\n')
    return exact(text, marker, helper + marker)


def parse_class(data):
    assert data[:4] == bytes.fromhex("cafebabe")
    minor, major = int.from_bytes(data[4:6], "big"), int.from_bytes(data[6:8], "big")
    at = 8
    count = int.from_bytes(data[at:at+2], "big"); at += 2
    cp = [None] * count
    idx = 1
    while idx < count:
        tag = data[at]; at += 1
        if tag == 1:
            n = int.from_bytes(data[at:at+2], "big"); at += 2
            cp[idx] = (tag, data[at:at+n].decode("utf-8")); at += n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; idx += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[idx] = (tag, int.from_bytes(data[at:at+2], "big")); at += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[idx] = (tag, int.from_bytes(data[at:at+2], "big"), int.from_bytes(data[at+2:at+4], "big")); at += 4
        elif tag == 15: at += 3
        else: raise AssertionError(("constant pool tag", tag))
        idx += 1
    def u2():
        nonlocal at
        v = int.from_bytes(data[at:at+2], "big"); at += 2
        return v
    def utf(index):
        assert cp[index][0] == 1
        return cp[index][1]
    def class_name(index):
        assert cp[index][0] == 7
        return utf(cp[index][1])
    access, this_class, super_class = u2(), u2(), u2()
    interfaces = [class_name(u2()) for _ in range(u2())]
    def members(is_method=False):
        nonlocal at
        rows = []
        for _ in range(u2()):
            flags, name, desc, attrs = u2(), utf(u2()), utf(u2()), u2()
            code = None
            for _ in range(attrs):
                attr_name, size = utf(u2()), int.from_bytes(data[at:at+4], "big"); at += 4
                end = at + size
                if is_method and attr_name == "Code":
                    at += 4  # max_stack and max_locals
                    n = int.from_bytes(data[at:at+4], "big"); at += 4
                    code = data[at:at+n]; at += n
                at = end
            rows.append((flags, name, desc, code) if is_method else (flags, name, desc))
        return rows
    fields, methods = members(), members(True)
    attributes = u2()
    for _ in range(attributes):
        u2(); size = int.from_bytes(data[at:at+4], "big"); at += 4 + size
    assert at == len(data)
    return {"minor": minor, "major": major, "access": access,
            "this": class_name(this_class), "super": class_name(super_class),
            "interfaces": interfaces, "fields": fields, "methods": methods, "cp": cp}


def root_leaves(text):
    body = text[text.index("function _bootstrapRoot"):text.index("function _prepare")]
    assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(_[A-Za-z0-9]+)\(\)(?:\)|);|h\[(\d+)\] = (DBOOT_[A-Z_]+);', body)
    out = []
    for match in assignments:
        index = int(match[0] or match[2])
        assert index == len(out), (index, len(out))
        if match[1]:
            out.append({"image": image(text, match[1]).hex()})
        else:
            name = match[3]
            start = text.index("bytes32 private constant " + name)
            declaration = text[start:text.index(";", start)]
            folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration)
            literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
            assert folded or literal, name
            out.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
    return out


pins = json.loads((stage / "build-pins.json").read_text())
parent_pins = json.loads((base / "build-pins.json").read_text())
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "math-sqrt-preflight", "parentEvidence": "MC-MATH-SQRT-P1 exact prior96-image source and generated gates",
                      "domain": DOMAIN, "bootstrapCount": 97, "bootstrapRoot": ROOT,
                      "diagnosticClassBound": 168, "globalNativeBindings": 18,
                      "address": ADDRESS, "owner": OWNER, "worker": "random-class",
                      "engine": ENGINE, "coordinator": COORDINATOR})
expected_pins["bootstrapSHA256"] = dict(parent_pins["bootstrapSHA256"])
expected_pins["bootstrapSHA256"]["Random"] = RANDOM_SHA
expected_pins["random"] = {"slot": 96, "bytes": RANDOM_BYTES, "sha256": RANDOM_SHA,
                            "keccak256": RANDOM_KECCAK,
                            "surface": "public concrete class directly extending Object and implementing Serializable; only public no-arg constructor, no fields or RNG APIs",
                            "java8": "javac -source 8 -target 8 -g:none"}
assert pins == expected_pins
assert pins["rawLimits"] == [71, 471911] and pins["bootstrapCount"] == 97 and pins["diagnosticClassBound"] == 168
assert pins["globalNativeBindings"] == 18 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216

source = (stage / "bootstrap/java/util/Random.java").read_text()
assert source == ('package java.util;\n\nimport java.io.Serializable;\n\n'
                  '/** Link/construction-only Java 8 profile for the measured platform type. */\n'
                  'public class Random implements Serializable {\n'
                  '    public Random() { super(); }\n'
                  '}\n')
for forbidden in ("nextInt", "nextLong", "nextFloat", "nextDouble", "setSeed", "nanoTime", "AtomicLong", "seed ="):
    assert forbidden not in source, forbidden
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="random-class-verify-", dir=root / "build") as name:
    tmp = Path(name); src = tmp / "java/util/Random.java"; src.parent.mkdir(parents=True); src.write_text(source)
    out = tmp / "classes"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    random_bytes = (out / "java/util/Random.class").read_bytes()
hex_bytes = bytes.fromhex("".join((stage / "bootstrap/java/util/Random.class.hex").read_text().split()))
assert random_bytes == hex_bytes and len(random_bytes) == RANDOM_BYTES
assert sha_bytes(random_bytes) == RANDOM_SHA
parsed = parse_class(random_bytes)
assert parsed["minor"] == 0 and parsed["major"] == 52
assert parsed["access"] == 0x0021 and parsed["this"] == "java/util/Random"
assert parsed["super"] == "java/lang/Object" and parsed["interfaces"] == ["java/io/Serializable"]
assert parsed["fields"] == []
assert [(x[0], x[1], x[2]) for x in parsed["methods"]] == [(0x0001, "<init>", "()V")]
code = parsed["methods"][0][3]
assert code == bytes.fromhex("2ab70001b1")
method_ref = parsed["cp"][int.from_bytes(code[2:4], "big")]
assert method_ref[0] == 10
owner_name = parsed["cp"][method_ref[1]]
nt = parsed["cp"][method_ref[2]]
assert parsed["cp"][owner_name[1]][1] == "java/lang/Object"
assert (parsed["cp"][nt[1]][1], parsed["cp"][nt[2]][1]) == ("<init>", "()V")

base_engine = (base / "engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(base_engine, random_bytes.hex())
for fixed in ("MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;", "new bytes32[](97)",
              "new uint256[](14)", "h[96] = DBOOT_RANDOM;", "inputCount + 91 +",
              "p.classes[classSlot + 57].data = _bootstrapRandom();", "return 18;", "binding != 18"):
    assert fixed in engine, fixed
assert engine.count("new bytes32[](97)") == 1
assert engine.count("_bootstrapRandom()") == 2
assert hashlib.sha256(image(engine, "_bootstrapRandom")).hexdigest() == RANDOM_SHA

base_leaves, leaves = root_leaves(base_engine), root_leaves(engine)
assert len(base_leaves) == 96 and len(leaves) == 97
assert leaves[:96] == base_leaves
assert leaves[96] == {"hash": RANDOM_KECCAK}
record = json.loads((stage / "root-commitment.json").read_text())
base_record = json.loads((base / "root-commitment.json").read_text())
assert record["bootstrapCount"] == 97 and record["parentBootstrapRoot"] == base_record["bootstrapRoot"]
assert record["prior96LeafKeccak256"] == base_record["leafKeccak256"]
assert record["changedLeafSlots"] == [96]
assert record["randomImage"] == {"slot": 96, "bytes": RANDOM_BYTES, "sha256": RANDOM_SHA, "keccak256": RANDOM_KECCAK}
assert record["leafKeccak256"] == base_record["leafKeccak256"] + [RANDOM_KECCAK]

node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = ('const{keccak256}=require("js-sha3"),p=JSON.parse(process.argv[1]),'
        'w=x=>x.padStart(64,"0"),h=p.l.map(x=>x.image?keccak256(Buffer.from(x.image,"hex")):x.hash),'
        'd=keccak256(Buffer.from(p.domain)),r=keccak256(Buffer.from(w(d)+w("40")+'
        'w(h.length.toString(16))+h.map(w).join(""),"hex"));'
        'console.log(JSON.stringify({leaves:h,root:r,domainHash:d}));')
folded = json.loads(subprocess.check_output(["node", "-e", node,
    json.dumps({"domain": "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1", "l": leaves})],
    cwd=root, env={**os.environ, "NODE_PATH": str(node_modules)}, text=True))
assert folded["root"] == ROOT == pins["bootstrapRoot"] == record["bootstrapRoot"]
assert folded["domainHash"] == record["dboot"]
assert folded["leaves"] == record["leafKeccak256"]

base_coord = (base / "coordinator/MCEntryCoordinator.sol").read_text()
coord_expected = exact(base_coord, DOMAIN_OLD, DOMAIN, 4)
coord_expected = exact(coord_expected, "4d432d4d4154482d535152542d50310000000000", ADDRESS[2:])
coord_expected = exact(coord_expected, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord_expected
assert (stage / "engine/build.js").read_bytes() == (base / "engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (base / "coordinator/build.js").read_bytes()

base_driver = (base / "tools/Go.txt").read_text()
driver = exact(base_driver, DOMAIN_OLD, DOMAIN, 6)
for old, new in (("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"]),
                 ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"]),
                 (parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"]),
                 ("0x4d432d4d4154482d535152542d50310000000000", ADDRESS),
                 ("0x4d432d4d4154482d535152542d50310000000001", OWNER)):
    driver = exact(driver, old, new)
for name, size in (("engineRun", ENGINE["bytes"]), ("coordRun", COORDINATOR["bytes"]), ("run", ENGINE["bytes"])):
    driver, count = re.subn(r"(len\(" + name + r"\) != )\d+", r"\g<1>" + str(size), driver)
    assert count == 1, name
assert (stage / "tools/Go.txt").read_text() == driver
base_diagnostic = (base / "tools/checkpoint_diagnostic.py").read_text()
expected_diagnostic = exact(base_diagnostic, "classes=u(2);assert classes<=167;states=[]",
                            "classes=u(2);assert classes<=168;states=[]")
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == expected_diagnostic
for name in ("checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (base / "tools" / name).read_bytes()

print(json.dumps({"basis": "math-sqrt-preflight", "domain": DOMAIN,
                  "random": {"slot": 96, "bytes": RANDOM_BYTES, "sha256": RANDOM_SHA,
                             "keccak256": RANDOM_KECCAK, "surface": "constructor only"},
                  "prior96LeavesExact": True, "bootstrapRoot": ROOT,
                  "rawLimits": [71, 471911], "diagnosticClassBound": 168,
                  "globalNativeBindings": 18, "stringLocalBinding": 12,
                  "engine": ENGINE, "coordinator": COORDINATOR,
                  "verification": "exact-java8-image+prior96-leaves+actual-ordered-root+only-random-append"}, indent=2))
