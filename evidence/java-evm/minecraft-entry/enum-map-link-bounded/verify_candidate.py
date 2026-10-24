#!/usr/bin/env python3
"""Source-only and generated-run verifier for the P58 EnumMap link candidate."""
import hashlib, importlib.util, json, os, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = REPO / "evidence/java-evm/minecraft-entry/enum-map-link-source-base-p57"

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(pathlib.Path(p).read_text())

base_manifest = load(BASE / "source-manifest.json")
for rel, meta in base_manifest["files"].items():
    p = BASE / rel
    assert p.stat().st_size == meta["bytes"] and sha(p) == meta["sha256"], f"P57 source snapshot mismatch {rel}"
print(f"P57 approved source-only snapshot: {len(base_manifest['files'])}/11 hashes verified")

basepins = load(BASE / "pins.json")
eng = load(ROOT/"engine/MCEntryInterpreter.json"); co = load(ROOT/"coordinator/MCEntryCoordinator.json")
source = (ROOT / "engine/MCEntryInterpreter.sol").read_text()
cosource = (ROOT / "coordinator/MCEntryCoordinator.sol").read_text()
spec = importlib.util.spec_from_file_location("enum_map_root", ROOT / "root_helper.py")
rh = importlib.util.module_from_spec(spec); spec.loader.exec_module(rh)
domain = "JVMEVM:MC-ENUM-MAP-LINK-BOUNDED-1:BOOTSTRAP:1"
record = rh.root_record(source, domain, str(REPO), os.environ.copy())
assert len(record["leaves"]) == 124
assert record["leaves"][:123] == basepins["orderedBootstrapLeaves"], "accepted P57 123-leaf prefix changed"
assert record["leaves"][105:123] == basepins["orderedBootstrapLeaves"][105:123], "tail 105..122 shifted/changed"
assert record["leaves"][123] == rh.root_record(source, domain, str(REPO), os.environ.copy())["leaves"][123]
assert "new bytes32[](124)" in source and "h[123] = keccak256(_bootstrapEnumMap());" in source
assert "p.classes[classSlot + 84].data = _bootstrapEnumMap();" in source
assert "uint256 count = inputCount + 111" in source
for old, new in [("count - 18", "count - 19"), ("count - 17", "count - 18"), ("count - 16", "count - 17"),
                 ("count - 15", "count - 16"), ("count - 14", "count - 15"), ("count - 7", "count - 8"),
                 ("count - 6", "count - 7"), ("count - 5", "count - 6"), ("count - 4", "count - 5"),
                 ("count - 3", "count - 4"), ("count - 2", "count - 3"), ("count - 1", "count - 2")]:
    assert f"p.classes[{new}]" in source, f"count-relative tail {new} missing"
assert "java/util/EnumMap" in source and "function _isReservedEnumClass" in source
assert all(f"JVMEVM:MC-ENUM-MAP-LINK-BOUNDED-1:{d}:1" in source for d in ("ROOT","ARTIFACT","BOOTSTRAP","CONFIG","MACHINE","SEED","VFS","FILE"))
assert "JVMEVM:MC-ENUM-MAP-LINK-BOUNDED-1:MAIN:EMPTY-STRING-ARRAY:1" in source
assert all(f'MC-ENUM-MAP-LINK-BOUNDED-1/{d}/v1' in cosource for d in ("package","class","selected-resource","vm"))
assert "bytes32 private constant ENGINE_CODEHASH = hex\"072360ef8f04101a9977368c2c64e669d045932ca05f5d65235cb2e1a9533f1f\";" in cosource

# Runtime ABI, storage/config API and non-EnumMap dependencies remain exactly P57.
for rel in ("engine/MCEntryInterpreter.json", "coordinator/MCEntryCoordinator.json"):
    art=load(ROOT/rel); old=load(BASE/rel)
    assert art["abi"] == old["abi"], f"ABI changed: {rel}"
pins=load(ROOT/"pins.json")
assert pins["bootstrapCount"] == 124 and pins["bootstrapRoot"] == record["root"]
assert pins["newLeafIndex"] == 123 and pins["diagnosticClassBound"] == 273
assert pins["engine"]["runtimeSHA256"] == eng["codeHashes"]["runtimeSHA256"]
assert pins["coordinator"]["runtimeKeccak256"] == co["codeHashes"]["runtimeKeccak256"]
assert pins["canonicalDriver"]["sha256"] == sha(ROOT/"canonical-driver.go")
assert pins["testArchiveSHA256"] == sha(ROOT/"tests/generated-probe.zip")
assert len(record["leaves"]) == 124
img=(ROOT/"bootstrap/classes/java/util/EnumMap.class")
assert img.exists() and img.read_bytes() == bytes.fromhex(re.search(r'function _bootstrapEnumMap\(\).*?hex"([0-9a-f]+)"',source).group(1))
assert len(img.read_bytes()) == 532
javap=(ROOT/"tests/EnumMap.javap.txt").read_text()
assert "public class java.util.EnumMap extends java.util.AbstractMap implements java.io.Serializable,java.lang.Cloneable" in javap
assert "private java.util.EnumMap();" in javap
assert "java/util/AbstractMap.\"<init>\":()V" in javap
assert not re.search(r"public java\.util\.EnumMap\((?:java\.lang\.Class|java\.util\.EnumMap|java\.util\.Map)", javap)
assert "ACC_FINAL" not in javap
assert "public native java.lang.Object get(java.lang.Object);" in javap
assert "public native java.lang.Object put(java.lang.Object, java.lang.Object);" in javap
assert all(x in javap for x in ("public native int size();","public native boolean isEmpty();","public native void clear();","public native boolean containsKey(java.lang.Object);","public native java.util.Set entrySet();"))
assert "Signature:" not in javap
marker=(ROOT/"bootstrap/java/util/EnumMap.java").read_text()
assert "public class EnumMap extends AbstractMap implements Serializable, Cloneable" in marker
assert "private EnumMap()" in marker and "new EnumMap" not in marker
assert not re.search(r"new\s+EnumMap\s*\(", (ROOT/"tests-src/EnumMapTypeLinkProbe.java").read_text())

# Recomputed artifact fingerprints and actual q1/q7 receipts.
engine=load(ROOT/"engine/MCEntryInterpreter.json"); coord=load(ROOT/"coordinator/MCEntryCoordinator.json")
runtime_bytes=bytes.fromhex(engine["deployedBytecode"])
coord_runtime=bytes.fromhex(coord["deployedBytecode"])
assert hashlib.sha256(runtime_bytes).hexdigest() == engine["codeHashes"]["runtimeSHA256"]
assert hashlib.sha256(coord_runtime).hexdigest() == coord["codeHashes"]["runtimeSHA256"]
assert len(runtime_bytes) == 446380
assert len(coord_runtime) == 5411
for quantum in ("q1","q7"):
    label=f"world-{quantum}-raw150-002"
    rpt=load(ROOT/f"reports/{label}/start.json")
    files=sorted((ROOT/f"reports/{label}").glob("slice-*.json"))
    terminal=load(files[-1])["slice"]
    assert rpt["zipBytes"] == 45191
    assert len(rpt["resourceRoots"]) == 150
    assert terminal["lifecycle"] == 2 and terminal["outcome"] == 2 and terminal["javaKind"] == 0
    assert terminal["totalJvmSteps"] == 208 and terminal["totalInternalSteps"] == 6
    assert not (ROOT/f"reports/{label}/resume-refusal.json").exists()
assert load(ROOT/"reports/world-q1-raw150-002/slice-00000000000000000208.json")["slice"]["machineStateRoot"] == load(ROOT/"reports/world-q7-raw150-002/slice-00000000000000000030.json")["slice"]["machineStateRoot"]
for q in ("q1","q7"):
    assert any((ROOT/f"reports/world-{q}-raw150-002").glob("process-*.json"))
print(f"P58 prefix/root: {record['root']} ({len(record['leaves'])} leaves); appended EnumMap leaf {record['leaves'][123]}")
print("ABI unchanged; P58 image javap signature/constructors/native guard surface verified")
print("q1/q7: raw150, fresh 124-image bootstrap array; same terminal machine root, reopen receipts present")
