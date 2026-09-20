#!/usr/bin/env python3
"""Strict generated-only source verifier for recovered PrintStream.println(String).

Only the accepted StringBuilder parent and this stage's generated source are
read. It never opens original artifacts, JARs, resources, checkpoints or worlds.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "string-builder-append-char-preflight"
PD, D = "MC-SB-APPEND-CHAR-0001", "MC-PRINTLN-STRING-0001"
PE, E = "4d432d53422d415050454e442d434841522d3031", "4d432d5052494e544c4e2d535452494e472d3031"
PO, O = "4d432d53422d415050454e442d434841522d3032", "4d432d5052494e544c4e2d535452494e472d3032"
IMAGE_SHA = "060f9aa1e9c6415ae6d6462678fdb19b8a7d0736e742821fa3130191eb497667"
IMAGE_KECCAK = "03915016b845257751cbb6de613d95effdc3c84cd4b59216de7783d0ca95ff2e"
ENGINE_BYTES = 393206


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

inputs = {
    "engine/MCEntryInterpreter.sol": parent / "engine/MCEntryInterpreter.sol",
    "coordinator/MCEntryCoordinator.sol": parent / "coordinator/MCEntryCoordinator.sol",
    "tools/Go.txt": parent / "tools/Go.txt",
    "tools/checkpoint_diagnostic.py": parent / "tools/checkpoint_diagnostic.py",
    "tools/checkpoint_frames.py": parent / "tools/checkpoint_frames.py",
    "tools/verify_receipts.js": parent / "tools/verify_receipts.js",
    "engine/build.js": parent / "engine/build.js", "coordinator/build.js": parent / "coordinator/build.js",
    "build-pins.json": parent / "build-pins.json", "tools/gate.py": parent / "tools/gate.py",
    "tools/generate_fixtures.py": parent / "tools/generate_fixtures.py",
    "root-commitment.json": parent / "root-commitment.json",
}
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "c5a9e702a", "parentEvidence": "string-builder-append-char-preflight",
    "fixtureBasis": "string-builder-append-char-preflight",
    "sha256": {name: sha(path) for name, path in inputs.items()},
}
assert len(PD) == len(D) == 22 and len(bytes.fromhex(PE)) == len(bytes.fromhex(E)) == 20
assert len(bytes.fromhex(PO)) == len(bytes.fromhex(O)) == 20
parent_pins = json.loads((parent / "build-pins.json").read_text())
assert parent_pins["domain"] == PD and parent_pins["engine"]["bytes"] == 393208
assert parent_pins["runtimeCap"] == 393216 and parent_pins["bootstrapCount"] == 91
assert parent_pins["rawLimits"] == [38, 285489] and parent_pins["diagnosticClassBound"] == 129
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["exceptionKinds"] == 14 and parent_pins["maxFrames"] == 128

# The checked-in class is generated solely by this local fixed producer. Its
# sole println Code body uses balanced monitorenter/monitorexit as its null
# probe before direct storage; it has no host-output path.
spec = importlib.util.spec_from_file_location("build_print_stream", stage / "bootstrap/build_print_stream.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
image = mod.build()
assert len(image) == 243 and hashlib.sha256(image).hexdigest() == IMAGE_SHA
assert image.hex() == "".join((stage / "bootstrap/java/io/PrintStream.class.hex").read_text().split())
assert image.startswith(bytes.fromhex("cafebabe00000034000f0a0004000b"))
assert image.count(bytes.fromhex("2bc22bc32a2bb50002b1")) == 1
assert image.count(b"java/io/PrintStream") == 1 and image.count(b"Ljava/lang/String;") == 2
source = (stage / "bootstrap/java/io/PrintStream.java").read_text()
for required in ("private String println;", "public PrintStream() {}", "public void println(String line)", "synchronized (line) {}", "println = line;"):
    assert source.count(required) == 1
assert source.count("synchronized (line) {}") == 1 and source.count("print(") == 0

# Construct the only permitted engine delta mechanically from the accepted
# parent. h[0] remains dynamic, h[83] alone receives a new exact image leaf.
p = (parent / "engine/MCEntryInterpreter.sol").read_text()
assert p.count(PD) == 9
expected = p.replace(PD, D)
old_comment = "    /// @dev Java 8 constructor-only guest PrintStream; output APIs are omitted.\n"
new_comment = ("    /// @dev Bounded Java 8 PrintStream: constructor plus println(String) only.\n"
               "    /// @dev println performs a balanced monitor null check then stores that exact reference in private println.\n")
assert expected.count(old_comment) == 1
expected = expected.replace(old_comment, new_comment)
pattern = r'(function _bootstrapPrintStream\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})'
assert len(re.findall(pattern, expected)) == 1
expected, n = re.subn(pattern, r'\g<1>' + image.hex() + r'\g<2>', expected); assert n == 1
needle = "    bytes32 private constant DBOOT_STACK_TRACE_ELEMENT = hex\"352c22e6449ab24ec8b39389c0b7ad9cf19d8b19263d5d81ab205447b137619e\";"
assert expected.count(needle) == 1
expected = expected.replace(needle, needle + "\n    bytes32 private constant DBOOT_PRINT_STREAM = hex\"" + IMAGE_KECCAK + "\";")
expected = expected.replace("h[83] = keccak256(_bootstrapPrintStream());", "h[83] = DBOOT_PRINT_STREAM;")
# Three exact safety-preserving cleanups: every caller obtains slice offsets
# from parsed/validated finite class data; the strict loop condition then keeps
# i and each offset+i in range. Thus no checked operation can overflow.
for old, new in (
    ("        for (uint256 i = 0; i < firstLength; ++i) {\n            if (first[firstOffset + i] != second[secondOffset + i]) return false;\n        }", "        unchecked { for (uint256 i = 0; i < firstLength; ++i) {\n            if (first[firstOffset + i] != second[secondOffset + i]) return false;\n        } }"),
    ("        for (uint256 i = 0; i < n; ++i) if (data[off + i] != wanted[i]) return false;", "        unchecked { for (uint256 i = 0; i < n; ++i) if (data[off + i] != wanted[i]) return false; }"),
    ("        for (uint256 i = 0; i < firstLength; ++i) {\n            if (data[firstOffset + i] != data[secondOffset + i]) return false;\n        }", "        unchecked { for (uint256 i = 0; i < firstLength; ++i) {\n            if (data[firstOffset + i] != data[secondOffset + i]) return false;\n        } }"),
):
    assert expected.count(old) == 1
    expected = expected.replace(old, new)
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected
assert "DBOOT_OBJECT" not in engine and engine.count("DBOOT_PRINT_STREAM") == 2
for invariant in ("h[0] = keccak256(_bootstrapObject());", "h[83] = DBOOT_PRINT_STREAM;",
                  "h[84] = keccak256(_bootstrapStringBuilder());", "new bytes32[](91)",
                  "MAX_RAW_CLASSES = 38;", "MAX_RAW_BYTES = 285489;", "MAX_FRAMES = 128;",
                  "COMMIT_RESERVE = 25_000_000;", "return keccak256(abi.encode(DBOOT, h));"):
    assert engine.count(invariant) == 1, invariant

# Recompute the root from all parent-derived leaves. Only leaf83 differs.
base_root = json.loads((parent / "root-commitment.json").read_text())
leaves = list(base_root["keccak256"])
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
js = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8")),w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const leaf=keccak256(Buffer.from(x.image,"hex"));x.keccak256[83]=leaf;const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.keccak256.length),...x.keccak256.map(z=>Buffer.from(z,"hex"))]));process.stdout.write(JSON.stringify({leaf,dboot:d,bootstrapRoot:r,keccak256:x.keccak256}));'''
calc = json.loads(subprocess.run(["node", "-e", js], input=json.dumps({"domain":D,"image":image.hex(),"keccak256":leaves}), text=True, capture_output=True, check=True, env={**os.environ,"NODE_PATH":str(node_modules)}).stdout)
assert calc["leaf"] == IMAGE_KECCAK
record = json.loads((stage / "root-commitment.json").read_text())
assert record == {"domain":D,"bootstrapCount":91,"dboot":calc["dboot"],"bootstrapRoot":calc["bootstrapRoot"],"order":base_root["order"],"keccak256":calc["keccak256"]}
assert [i for i,(a,b) in enumerate(zip(base_root["keccak256"],record["keccak256"])) if a != b] == [83]
assert record["keccak256"][0] == "8f96f9515a06956754c5de9446d653641348a60d238100e36354acf2f2794111"

for name in ("checkpoint_diagnostic.py","checkpoint_frames.py","verify_receipts.js","strip_stackmap.py"):
    assert (stage / "tools" / name).read_bytes() == (parent / "tools" / name).read_bytes()
assert (stage / "engine/build.js").read_bytes() == (parent / "engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "coordinator/build.js").read_bytes()
assert sha(stage / "tools/generate_fixtures.py") == "acf6d157834d7465f19911f6252c97f0cbafd8e99689559c62e2e7e5292463d8"
assert sha(stage / "tools/gate.py") == "65eed14c465a5f0ef5737a6599c799c50ff76e9019ff959ad7dbf6eed87a00bf"

parent_coordinator = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
initial_coordinator = parent_coordinator.replace(PD,D).replace(PE,E)
initial_driver = (parent / "tools/Go.txt").read_text().replace(PD,D).replace(PE,E).replace(PO,O)
args=sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coordinator
    assert (stage / "tools/Go.txt").read_text() == initial_driver
    phase="prebuild"
else:
    assert len(args)==2 and args[0]=="--built"
    pins=json.loads(Path(args[1]).read_text()); boot=dict(parent_pins["bootstrapSHA256"]); boot["PrintStream"]=IMAGE_SHA
    expected_pins={"basis":"c5a9e702a","parentEvidence":"string-builder-append-char-preflight","phase":"built","domain":D,"runtimeBaseline":393208,"runtimeCap":393216,"bootstrapCount":91,"bootstrapSHA256":boot,"globalNativeBindings":13,"stringLocalBinding":10,"exceptionKinds":14,"maxFrames":128,"externalLocalGas":1000000000,"reserve":25000000,"rawLimits":[38,285489],"checkpointCap":1048576,"headCap":32768,"diagnosticClassBound":129,"address":"0x"+E,"owner":"0x"+O,"limitsCommitment":parent_pins["limitsCommitment"],"compiler":parent_pins["compiler"],"engine":pins["engine"],"coordinator":pins["coordinator"]}
    assert pins == expected_pins and pins["engine"]["bytes"] == ENGINE_BYTES and pins["coordinator"]["bytes"] == 5394
    final_coordinator=initial_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"],pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text()==final_coordinator
    final_driver=initial_driver
    for old,new in ((parent_pins["engine"]["runtimeSHA256"],pins["engine"]["runtimeSHA256"]),("0x"+parent_pins["engine"]["runtimeKeccak256"],"0x"+pins["engine"]["runtimeKeccak256"]),("0x"+parent_pins["coordinator"]["runtimeKeccak256"],"0x"+pins["coordinator"]["runtimeKeccak256"])):
        assert final_driver.count(old)==1; final_driver=final_driver.replace(old,new)
    for pat,repl in ((r"len\(coordRun\) != \d+","len(coordRun) != %d"%pins["coordinator"]["bytes"]),(r"len\(engineRun\) != \d+","len(engineRun) != %d"%pins["engine"]["bytes"]),(r"len\(run\) != \d+","len(run) != %d"%pins["engine"]["bytes"])):
        final_driver,n=re.subn(pat,repl,final_driver);assert n==1
    assert (stage / "tools/Go.txt").read_text()==final_driver and json.loads((stage / "build-pins.json").read_text())==pins
    phase="built"
print(json.dumps({"phase":phase,"domain":D,"bootstrapRoot":record["bootstrapRoot"],"printStreamSHA256":IMAGE_SHA,"runtimeBytes":ENGINE_BYTES,"runtimeCap":393216,"dynamicObjectLeaf":record["keccak256"][0]},indent=2))
