#!/usr/bin/env python3
"""Verify the generated-only bounded String.toLowerCase(Locale.ROOT) delta.

This verifier reads no original/JAR/resource/world input. It compiler-rebuilds only
checked-in Java-8 bootstrap sources, checks the exact native surface, and derives
the ordered bootstrap root independently from all 96 leaves.
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
parent = stage.parent / "parent-b664e751a"
prior = stage.parent / "locale-root-preflight"
DOMAIN = "MC-STRING-LOWER-LOCALE-P1"
STRING_SHA256 = "259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe"
STRING_KECCAK = "1e87829801f37c026b569269f629c58aa9df25c90f0b44979a8b075b0af458ff"
LOCALE_SHA256 = "8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31"
ROOT = "39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18"
ENGINE = {"bytes": 379383, "initSHA256": "a2516b2dc4a922824be1ee068fe7d692a5327a975428f4b1554eb2c00f771471", "runtimeSHA256": "94d8b0f62cbbc4919c7182997b5183e266e09fc6b486d912425d70ee14f3d598", "runtimeKeccak256": "ac8056d922db9b5661fdc8653f57e8c4c7e328251f3ead090da4b84da2f67593"}
COORDINATOR = {"bytes": 5394, "initSHA256": "ed988e3b1326c4b0b7a61794e60d46d61fbe39d0b24d3c9428f681b62b25fb78", "runtimeSHA256": "a9e2f430132a71a7eff22a4d1e29387f74e200a2b6e1233a19383d4092f4b7ff", "runtimeKeccak256": "b9671c049b6dc0c9a3ef5d159d5b88791ab353874c8f26e95f3c207310a52233"}
OLD_DOMAIN = "MC-LOCALE-ROOT-P2"
OLD_ENGINE = "4d432d4c4f43414c452d524f4f542d5030303032"
NEW_ENGINE = "4d432d535452494e472d4c4f5745522d50303031"
OLD_OWNER = "4d432d4c4f43414c452d524f4f542d4f30303032"
NEW_OWNER = "4d432d535452494e472d4c4f5745522d4f303031"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def text(path): return path.read_text()


def function_image(source, function):
    start = source.index("function " + function + "(")
    end = source.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', source[start:end if end >= 0 else len(source)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def metadata(data):
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8; count = int.from_bytes(data[at:at + 2], "big"); at += 2; cp = [None] * count; i = 1
    while i < count:
        tag = data[at]; at += 1
        if tag == 1:
            n = int.from_bytes(data[at:at + 2], "big"); at += 2; cp[i] = (tag, data[at:at+n].decode()); at += n
        elif tag in (7, 8, 16): cp[i] = (tag, int.from_bytes(data[at:at+2], "big")); at += 2
        elif tag in (3, 4): cp[i] = (tag, data[at:at+4]); at += 4
        elif tag in (5, 6): cp[i] = (tag, data[at:at+8]); at += 8; i += 1
        elif tag in (9, 10, 11, 12, 18): cp[i] = (tag, data[at:at+4]); at += 4
        elif tag == 15: cp[i] = (tag, data[at:at+3]); at += 3
        else: raise AssertionError(("cp", tag, i))
        i += 1
    def u2():
        nonlocal at
        value = int.from_bytes(data[at:at+2], "big"); at += 2; return value
    def u4():
        nonlocal at
        value = int.from_bytes(data[at:at+4], "big"); at += 4; return value
    def utf(i): assert cp[i][0] == 1; return cp[i][1]
    def cname(i): assert cp[i][0] == 7; return utf(cp[i][1])
    def attrs():
        nonlocal at
        out = []
        for _ in range(u2()):
            name = utf(u2()); n = u4(); out.append((name, data[at:at+n])); at += n
        return out
    access, this, super_ = u2(), u2(), u2()
    interfaces = [u2() for _ in range(u2())]
    fields = [(u2(), utf(u2()), utf(u2()), attrs()) for _ in range(u2())]
    methods = [(u2(), utf(u2()), utf(u2()), attrs()) for _ in range(u2())]
    attributes = attrs(); assert at == len(data)
    return {"access": access, "this": cname(this), "super": cname(super_),
            "interfaces": [cname(i) for i in interfaces], "fields": fields,
            "methods": methods, "attributes": attributes}


assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
parent_pins = json.loads(text(parent / "pins.json")); pins = json.loads(text(stage / "build-pins.json")); prior_root = json.loads(text(prior / "root-commitment.json"))
assert parent_pins["bootstrapCount"] == 96 and parent_pins["rawLimits"] == [69, 449904]
assert parent_pins["diagnosticClassBound"] == 165 and parent_pins["stringLocalBinding"] == 11
assert parent_pins["bootstrapSHA256"]["String"] == "42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec"
assert parent_pins["locale"]["sha256"] == LOCALE_SHA256

# Exact Java-8 source/image reproduction; Locale must remain byte-for-byte parent exact.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-lower-locale-verify-", dir=root / "build") as temporary:
    temporary = Path(temporary); out = temporary / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out,
                    stage / "bootstrap/java/lang/String.java", stage / "bootstrap/java/util/Locale.java"], check=True)
    rebuilt_string = (out / "java/lang/String.class").read_bytes(); rebuilt_locale = (out / "java/util/Locale.class").read_bytes()
string_image = bytes.fromhex(text(stage / "bootstrap/java/lang/String.class.hex").strip())
locale_image = bytes.fromhex(text(stage / "bootstrap/java/util/Locale.class.hex").strip())
assert rebuilt_string == string_image and len(string_image) == 1836
assert hashlib.sha256(string_image).hexdigest() == STRING_SHA256
assert text(stage / "bootstrap/java/lang/String.sha256").split()[0] == STRING_SHA256
assert rebuilt_locale == locale_image and hashlib.sha256(locale_image).hexdigest() == LOCALE_SHA256
assert text(stage / "bootstrap/java/util/Locale.sha256").split()[0] == LOCALE_SHA256
assert locale_image == function_image(text(parent / "artifacts/engine/MCEntryInterpreter.sol"), "_bootstrapLocale")

old_string = function_image(text(parent / "artifacts/engine/MCEntryInterpreter.sol"), "_bootstrapString")
old_meta, new_meta = metadata(old_string), metadata(string_image)
assert (new_meta["access"], new_meta["this"], new_meta["super"], new_meta["interfaces"], new_meta["fields"]) == (old_meta["access"], old_meta["this"], old_meta["super"], old_meta["interfaces"], old_meta["fields"])
old_methods = {(name, descriptor): (access, [name for name, _ in attrs]) for access, name, descriptor, attrs in old_meta["methods"]}
new_methods = {(name, descriptor): (access, [name for name, _ in attrs]) for access, name, descriptor, attrs in new_meta["methods"]}
key = ("toLowerCase", "(Ljava/util/Locale;)Ljava/lang/String;")
assert set(new_methods) == set(old_methods) | {key} and new_methods[key] == (0x0101, [])
assert all(new_methods[k] == v for k, v in old_methods.items())
assert b"toUpperCase" not in string_image and b"toLowerCase()" not in string_image and b"java/util/Locale" in string_image
assert b"getDefault" not in locale_image and b"language" not in locale_image and b"country" not in locale_image

engine = text(stage / "engine/MCEntryInterpreter.sol"); parent_engine = text(parent / "artifacts/engine/MCEntryInterpreter.sol")
assert engine.count(DOMAIN) == parent_engine.count(OLD_DOMAIN) == 9 and OLD_DOMAIN not in engine
assert function_image(engine, "_bootstrapString") == string_image
assert function_image(engine, "_bootstrapLocale") == locale_image
# A single exact native name/descriptor pair owns binding12. There is no global slot change.
needle = 'bytes("toLowerCase"))\n            && _equalsLiteral(c.data, doff, dn, bytes("(Ljava/util/Locale;)Ljava/lang/String;"))) return 12;'
assert engine.count(needle) == 1 and engine.count("_lowerCaseLocaleRootString(") == 2
assert "toUpperCase" not in engine and "getDefault" not in engine
for required in ("if (units[i] > 0x7f) revert StringProfileError(1, pc);", "if (!changed) return (receiverHandle, false);", "arena.nextHandle > MAX_HANDLES - 2", "arena.heap.objectHeap[stringHandle][arena.stringHashOffset] = _packInt(0);", "if (_payload(f.stack[base + 1]) == 0)"):
    assert required in engine, required

# Independently enumerate the ordered root. All 95 non-String leaves must equal
# the parent commitment, including Locale at slot95; only slot26 may differ.
body = engine[engine.index("function _bootstrapRoot"):engine.index("function _prepare")]
assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', body)
parent_body = parent_engine[parent_engine.index("function _bootstrapRoot"):parent_engine.index("function _prepare")]
parent_assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', parent_body)
assert len(assignments) == len(parent_assignments) == 96 and [int(i) for i, _, _ in assignments] == list(range(96))
# This is stronger than leaf-hash equality: every non-String function image or
# folded constant is byte-for-byte identical to the parent ordering input.
for index, (_, function, constant) in enumerate(assignments):
    _, parent_function, parent_constant = parent_assignments[index]
    if index == 26: continue
    assert (function, constant) == (parent_function, parent_constant), index
    if function:
        assert function_image(engine, function) == function_image(parent_engine, function), (index, function)
    else:
        here_at = engine.index("bytes32 private constant " + constant)
        parent_at = parent_engine.index("bytes32 private constant " + constant)
        assert engine[here_at:engine.index(";", here_at)] == parent_engine[parent_at:parent_engine.index(";", parent_at)], (index, constant)
rows = []
for _, function, constant in assignments:
    if function: rows.append({"image": function_image(engine, function).hex()})
    else:
        at = engine.index("bytes32 private constant " + constant); declaration = engine[at:engine.index(";", at)]
        folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration); literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
        rows.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
node = root / "jvmevm/runtime/node_modules"; assert node.is_dir()
script = "const{keccak256}=require('js-sha3');const r=JSON.parse(process.argv[1]),w=x=>x.padStart(64,'0'),h=r.map(x=>x.image?keccak256(Buffer.from(x.image,'hex')):x.hash),d=keccak256(process.argv[2]);console.log(JSON.stringify({d,h,root:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
independent = json.loads(subprocess.check_output(["node", "-e", script, json.dumps(rows), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"], cwd=root, env={**os.environ, "NODE_PATH": str(node)}, text=True))
record = json.loads(text(stage / "root-commitment.json"))
assert independent["d"] == record["dboot"] and independent["root"] == ROOT == record["bootstrapRoot"]
assert independent["h"] == record["keccak256"] and record["order"] == prior_root["order"]
assert independent["h"][26] == STRING_KECCAK
assert independent["h"][:26] == prior_root["keccak256"][:26] and independent["h"][27:] == prior_root["keccak256"][27:]
assert independent["h"][95] == parent_pins["locale"]["keccak256"]

expected = copy.deepcopy(parent_pins)
expected.update({"basis": "parent-b664e751a", "parentEvidence": "parent-b664e751a/{artifacts,canonical-driver,checkpoint,pins}", "domain": DOMAIN, "bootstrapRoot": ROOT, "address": "0x" + NEW_ENGINE, "owner": "0x" + NEW_OWNER, "engine": ENGINE, "coordinator": COORDINATOR, "worker": "string-to-lower-case-locale", "stringLocalBinding": 12, "string": {"slot": 26, "bytes": 1836, "sha256": STRING_SHA256, "keccak256": STRING_KECCAK, "surface": "accepted String surface plus ASCII toLowerCase(Locale.ROOT) only", "java8": "javac -source 8 -target 8 -g:none"}})
expected["bootstrapSHA256"]["String"] = STRING_SHA256
assert pins == expected
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 12 and pins["exceptionKinds"] == 14
assert pins["rawLimits"] == [69, 449904] and pins["bootstrapCount"] == 96 and pins["diagnosticClassBound"] == 165
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216

# Coordinator and durable driver are exact domain/hash/address rebinding; the
# copied public checkpoint/receipt diagnostics remain byte-identical.
coord = text(parent / "artifacts/coordinator/MCEntryCoordinator.sol").replace(OLD_DOMAIN, DOMAIN).replace(OLD_ENGINE, NEW_ENGINE).replace(parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert text(stage / "coordinator/MCEntryCoordinator.sol") == coord
transport = text(parent / "canonical-driver.go.txt")
for old, new in ((OLD_DOMAIN, DOMAIN), (OLD_OWNER, NEW_OWNER), (OLD_ENGINE, NEW_ENGINE), (parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"]), ("len(engineRun) != 378675", "len(engineRun) != 379383"), ("len(run) != 378675", "len(run) != 379383")):
    assert old in transport, old; transport = transport.replace(old, new)
assert text(stage / "tools/Go.txt") == transport
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "strip_stackmap.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (prior / "tools" / name).read_bytes(), name
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({"phase": "built", "domain": DOMAIN, "bootstrapImages": 96, "changedBootstrapSlot": 26, "string": pins["string"], "localeSHA256": LOCALE_SHA256, "bootstrapRoot": ROOT, "rawLimits": pins["rawLimits"], "diagnosticClassBound": 165, "globalNativeBindings": 16, "stringLocalBinding": 12, "engine": ENGINE, "coordinator": COORDINATOR, "verification": "Java8-String+metadata+Locale-parent-exact+independent-ordered-root+sole-String-leaf"}, indent=2))
