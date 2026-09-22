#!/usr/bin/env python3
"""Verify the literal raw70 / byte464925 capacity delta from parent-629078bb6.

Only checked-in stage sources and locally generated Java-8 bootstrap output are
read. No original artifact, JAR, external class, resource, or network input is
opened or evaluated.
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
parent = stage.parent / "parent-629078bb6"
prior = stage.parent / "string-to-lower-case-locale-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "8e99bcc62602a797789a3536350ec02d19ef12efc059d4eaf0a0490245267822",
    "artifacts/coordinator/MCEntryCoordinator.sol": "785f3b2c5efcc3c0ea0626292e77b3f8207e929407ffd6ddcf00c67c8528f4a6",
    "canonical-driver.go.txt": "90ed9dd77bbbf5c2a534888b42dc1e1a3add2c81b8d73278eb39d7e497fe3929",
    "checkpoint_diagnostic.py": "445fcdb0752ee7a31b4c6386e71f8f5422d1d0d9e463156fe7edb12b503e157d",
    "checkpoint_frames.py": "445fcdb0752ee7a31b4c6386e71f8f5422d1d0d9e463156fe7edb12b503e157d",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PRIOR_SHA256 = {
    "root-commitment.json": "06811501c1a0fe402b0c6d5b725e95188b5b55385ef47e5be9116ae71b5da459",
    "bootstrap/java/lang/String.java": "3f7d9e35a8a10949d34dcea78f5a4e3cb5a5b4255b2aadd764fb98e01cf64077",
    "bootstrap/java/lang/String.class.hex": "69cad4f5531e62ca260b7b0c068609a2af58d683ab6169e236368f06fbdd0b7b",
    "bootstrap/java/lang/String.sha256": "cf524b12441bc6a31e3f827418d770b963196545f796ae8a10fa4ac957e2c1c8",
    "bootstrap/java/util/Locale.java": "6558483205b92fcc43fe7e0f748198b0019ad18cbf0c950f9ec602e7e97a6375",
    "bootstrap/java/util/Locale.class.hex": "16660fe0ab426c6caaa8e400550e9eb1ebe4aec0b387195749d6ce263f0d5ab8",
    "bootstrap/java/util/Locale.sha256": "871b1720b5e2383c5a2a0b7c29246a46f61effc71c0678664ad3e13968631be9",
}
ENGINE = {
    "bytes": 379383,
    "initSHA256": "bd1c00cfd8e37ff4aae7f7bd66ec5ff3222a2455b2f51be02a2fed6afb157f5b",
    "runtimeSHA256": "e8617298590924a2c432b09483e0d8ef4d6e8e8b3244039c969f7d58856dc893",
    "runtimeKeccak256": "053e7f60605341d3e96a917fc08dcfab5252ac7ccefd052f8e2b4c2b9cdc8c2f",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "4f224064d957a33b8180af6de7f8a71974c2f3376c66f75b6caf561bec95a01a",
    "runtimeSHA256": "0765ebde1c36c3a64dd6e4c7ac537556af4573a4ecfec4cfab64015e1b33cde5",
    "runtimeKeccak256": "1ab5437abc92ddb5ebb98d031a66402205703c304acecfa9c551dd8c410d0be2",
}
STRING_SHA256 = "259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe"
LOCALE_SHA256 = "8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31"
ROOT = "39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    actual = text.count(old)
    assert actual == count, (old, actual, count)
    return text.replace(old, new)


def function_image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


for relative, expected in PARENT_SHA256.items():
    assert sha(parent / relative) == expected, relative
for relative, expected in PRIOR_SHA256.items():
    assert sha(prior / relative) == expected, relative
parent_pins = json.loads((parent / "pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
assert parent_pins["rawLimits"] == [69, 449904]
assert parent_pins["diagnosticClassBound"] == 165
assert parent_pins["bootstrapCount"] == 96
assert parent_pins["bootstrapRoot"] == ROOT
assert parent_pins["bootstrapSHA256"]["String"] == STRING_SHA256
assert parent_pins["bootstrapSHA256"]["Locale"] == LOCALE_SHA256
assert parent_pins["globalNativeBindings"] == 16 and parent_pins["stringLocalBinding"] == 12

expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "parent-629078bb6",
    "parentEvidence": "parent-629078bb6/{artifacts,canonical-driver,checkpoint,pins}",
    "rawLimits": [70, 464925],
    "diagnosticClassBound": 166,
    "engine": ENGINE,
    "coordinator": COORDINATOR,
    "worker": "classcount70-byte464925",
})
assert pins == expected_pins
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128

# The only engine source delta is its two capacity constants and the constructor
# configuration tuple. This equality protects every opcode/interpreter/native,
# bootstrap leaf, String/Locale surface, and all other limits byte-for-byte.
parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = exact(parent_engine, "MAX_RAW_CLASSES = 69;", "MAX_RAW_CLASSES = 70;")
engine = exact(engine, "MAX_RAW_BYTES = 449904;", "MAX_RAW_BYTES = 464925;")
engine = exact(engine, "uint32(69), uint32(449904)", "uint32(70), uint32(464925)")
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == engine
assert hashlib.sha256(function_image(engine, "_bootstrapString")).hexdigest() == STRING_SHA256
assert hashlib.sha256(function_image(engine, "_bootstrapLocale")).hexdigest() == LOCALE_SHA256
assert hashlib.sha256(function_image(engine, "_bootstrapInteger")).hexdigest() == pins["integer"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapMapEntry")).hexdigest() == pins["mapEntry"]["sha256"]

# The fixed 96-leaf commitment is independently re-enumerated from the actual
# engine source and folded with the tracked root commitment's frozen DBOOT.
body = engine[engine.index("function _bootstrapRoot"):engine.index("function _prepare")]
assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', body)
assert len(assignments) == 96 and [int(index) for index, _, _ in assignments] == list(range(96))
leaves = []
for _, function, constant in assignments:
    if function:
        leaves.append({"image": function_image(engine, function).hex()})
    else:
        at = engine.index("bytes32 private constant " + constant)
        declaration = engine[at:engine.index(";", at)]
        folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration)
        literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
        assert folded or literal, constant
        leaves.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
root_record = json.loads((stage / "root-commitment.json").read_text())
assert (stage / "root-commitment.json").read_bytes() == (prior / "root-commitment.json").read_bytes()
assert root_record["bootstrapCount"] == 96 and root_record["bootstrapRoot"] == ROOT
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
script = "const{keccak256}=require('js-sha3');const r=JSON.parse(process.argv[1]),w=x=>x.padStart(64,'0'),h=r.map(x=>x.image?keccak256(Buffer.from(x.image,'hex')):x.hash),d=process.argv[2];console.log(JSON.stringify({h,root:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
independent = json.loads(subprocess.check_output(["node", "-e", script, json.dumps(leaves), root_record["dboot"]], cwd=root, env={**os.environ, "NODE_PATH": str(node)}, text=True))
assert independent["h"] == root_record["keccak256"]
assert independent["root"] == ROOT
assert independent["h"][26] == pins["string"]["keccak256"]
assert independent["h"][94] == pins["mapEntry"]["keccak256"]
assert independent["h"][95] == pins["locale"]["keccak256"]

# Checked-in Java-8 inputs reproduce String and Locale exactly. They are only
# bootstrap source verification; no external Java class is read.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="classcount70-byte464925-verify-", dir=root / "build") as temp:
    out = Path(temp) / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out,
                    stage / "bootstrap/java/lang/String.java", stage / "bootstrap/java/util/Locale.java"], check=True)
    rebuilt_string = (out / "java/lang/String.class").read_bytes()
    rebuilt_locale = (out / "java/util/Locale.class").read_bytes()
string_image = bytes.fromhex((stage / "bootstrap/java/lang/String.class.hex").read_text().strip())
locale_image = bytes.fromhex((stage / "bootstrap/java/util/Locale.class.hex").read_text().strip())
assert rebuilt_string == string_image and len(string_image) == 1836 and hashlib.sha256(string_image).hexdigest() == STRING_SHA256
assert rebuilt_locale == locale_image and len(locale_image) == 285 and hashlib.sha256(locale_image).hexdigest() == LOCALE_SHA256
assert (stage / "bootstrap/java/lang/String.sha256").read_text().split()[0] == STRING_SHA256
assert (stage / "bootstrap/java/util/Locale.sha256").read_text().split()[0] == LOCALE_SHA256
for relative in PRIOR_SHA256:
    assert (stage / relative).read_bytes() == (prior / relative).read_bytes(), relative

# Coordinator fixed arrays and the canonical transport change at the same two
# exact capacity boundaries, plus only rebuilt engine/coordinator identities.
parent_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, "[69]", "[70]", 4)
coord = exact(coord, "n > 69", "n > 70")
coord = exact(coord, "449904", "464925", 2)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord
parent_go = (parent / "canonical-driver.go.txt").read_text()
go = exact(parent_go, "len(m.Decoders) > 69", "len(m.Decoders) > 70")
go = exact(go, "len(parts) > 69", "len(parts) > 70")
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
assert (stage / "tools/Go.txt").read_text() == go
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    expected = exact((parent / name).read_text(), "classes<=165", "classes<=166")
    assert (stage / "tools" / name).read_text() == expected
for relative, parent_relative in (("engine/build.js", "artifacts/engine/build.js"), ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / relative).read_bytes() == (parent / parent_relative).read_bytes(), relative

fixtures = (stage / "tools/generate_fixtures.py").read_text()
for fragment in ('count_fixture("count-70", 70)', 'count_fixture("count-71", 71)',
                 'count_fixture("count-70-464925", 70, 464925)',
                 'count_fixture("count-70-464926", 70, 464926)', '"rawLimits": [70, 464925]'):
    assert fragment in fixtures, fragment
gate = (stage / "tools/gate.py").read_text()
for fragment in ('[70, 464925]', 'diagnosticClassBound"] == 166', 'q_equivalent("count-70")',
                 '"count-71.zip"', 'count-70-464925', 'count-70-464926', '["1", "71"]'):
    assert fragment in gate, fragment
assert "<= 1200" in gate and 'actualDI0ReadSizes"]) == 464925' in gate
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"], "engine": ENGINE,
    "coordinator": COORDINATOR, "bootstrapRoot": ROOT,
    "stringSHA256": STRING_SHA256, "localeSHA256": LOCALE_SHA256,
    "mapEntrySHA256": pins["mapEntry"]["sha256"], "integerSHA256": pins["integer"]["sha256"],
    "verification": "literal-capacity-only-source-delta+independent-fixed-96-leaf-root+Java8-String-Locale+generated-input-only",
}, indent=2))
