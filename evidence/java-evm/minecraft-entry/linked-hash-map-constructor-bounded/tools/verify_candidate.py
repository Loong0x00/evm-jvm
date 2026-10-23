#!/usr/bin/env python3
"""Source/artifact/receipt verifier for the generated-only LinkedHashMap P49 candidate."""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
BASE = REPO / "evidence/java-evm/minecraft-entry/linked-hash-map-source-base-p48"

def load(path):
    return json.loads(path.read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check(condition, message):
    if not condition:
        raise AssertionError(message)

# Verify all 13 expressly authorized source-only P48 files before comparisons.
base_manifest = load(BASE / "source-manifest.json")
check(len(base_manifest["files"]) == 13, "P48 manifest count")
for rel, pins in base_manifest["files"].items():
    data = (BASE / rel).read_bytes()
    check(len(data) == pins["bytes"] and sha(data) == pins["sha256"], f"P48 source hash: {rel}")

candidate_pins = load(ROOT / "results/pins.json")
manifest = load(ROOT / "results/manifest.json")
for rel, pins in manifest["files"].items():
    data = (ROOT / rel).read_bytes()
    check(len(data) == pins["bytes"] and sha(data) == pins["sha256"], f"candidate hash: {rel}")

base_helper_spec = importlib.util.spec_from_file_location("p48_root_helper", BASE / "root_helper.py")
base_helper = importlib.util.module_from_spec(base_helper_spec)
base_helper_spec.loader.exec_module(base_helper)
candidate_helper_spec = importlib.util.spec_from_file_location("p49_root_helper", ROOT / "tools/root_helper.py")
candidate_helper = importlib.util.module_from_spec(candidate_helper_spec)
candidate_helper_spec.loader.exec_module(candidate_helper)
env = os.environ.copy()
env["NODE_PATH"] = str(REPO / "jvmevm/runtime/node_modules")
base_source = (BASE / "engine/MCEntryInterpreter.sol").read_text()
candidate_source = (ROOT / "engine/MCEntryInterpreter.sol").read_text()
base_domain = re.search(r'DBOOT\s*=\s*keccak256\("([^"]+)"\)', base_source).group(1)
root_domain = re.search(r'DBOOT\s*=\s*keccak256\("([^"]+)"\)', candidate_source).group(1)
old = base_helper.root_record(base_source, base_domain, str(REPO), env)
new = candidate_helper.root_record(candidate_source, root_domain, str(REPO), env)
check(old["root"] == load(BASE / "pins.json")["bootstrapRoot"], "actual P48 DBOOT source commitment")
check(len(old["leaves"]) == 113 and len(new["leaves"]) == 114, "ordered bootstrap counts")
check(old["leaves"] == new["leaves"][:113], "P48 leaf bytes/order changed")
check(new["leaves"][113] == candidate_pins["linkedHashMap"]["keccak256"], "new leaf differs from actual class image")
check(new["root"] == candidate_pins["bootstrapRoot"], "ordered root pin")
check(new["leaves"] == load(ROOT / "results/root-commitment.json")["orderedLeaves"], "all actual ordered leaves")

# Exact Java 8 generated class image and scoped surface.
classfile = (ROOT / "bootstrap/java/util/LinkedHashMap.class").read_bytes()
check(classfile == (ROOT / "classes/javac/java/util/LinkedHashMap.class").read_bytes(), "reproducible class image copy")
check(len(classfile) == candidate_pins["linkedHashMap"]["bytes"], "class size")
check(sha(classfile) == candidate_pins["linkedHashMap"]["sha256"], "class SHA")
check(classfile[:8] == bytes.fromhex("cafebabe00000034"), "Java 8 class version")
source = (ROOT / "bootstrap/java/util/LinkedHashMap.java").read_text()
check("extends HashMap<K, V>" in source and "private final boolean accessOrder;" in source, "generic hierarchy/state")
check("@Override public native V put(K key, V value);" in source, "explicit unbound put override")
check("public LinkedHashMap()" in source and "super();" in source and "this.accessOrder = false;" in source, "constructor body")
check("MAX_RAW_CLASSES = 150" in candidate_source and "MAX_RAW_BYTES = 1063930" in candidate_source, "raw limits changed")
check("new bytes32[](114)" in candidate_source and "h[113] = keccak256(_bootstrapLinkedHashMap())" in candidate_source, "bootstrap root append")
check("p.classes[classSlot + 74].data = _bootstrapLinkedHashMap()" in candidate_source, "program image append")
check("uint8 public classCount;" in (ROOT / "coordinator/MCEntryCoordinator.sol").read_text(), "raw count wire width changed")
for field in ("address[150] private decoders", "bytes32[150] private classRoots", "uint32[150] private classSizes", "bytes[150] private rawNames"):
    check(field in (ROOT / "coordinator/MCEntryCoordinator.sol").read_text(), f"coordinator raw bound changed: {field}")

for component in ("engine", "coordinator"):
    artifact = load(ROOT / f"{component}/MCEntry{'Interpreter' if component == 'engine' else 'Coordinator'}.json")
    source_file = ROOT / f"{component}/MCEntry{'Interpreter' if component == 'engine' else 'Coordinator'}.sol"
    check(artifact["sourceHashes"][source_file.name] == sha(source_file.read_bytes()), f"{component} source pin")
    check(artifact["codeHashes"]["runtimeKeccak256"] == candidate_pins[component]["runtimeKeccak256"], f"{component} runtime pin")

# Fresh public EVM processes; terminal values are compared while checkpoint hashes are quantum-specific.
results = ROOT / "results"
heads = {}
for q in (1, 7, 16):
    h = load(results / f"q{q}-empty/durable-head.json")
    check(h["stage"] == "final-reopened" and h["lifecycle"] == 2 and h["outcome"] == 2 and h["result"] == 0 and h["javaKind"] == 0, f"q{q} terminal success")
    heads[q] = h
keys = ("lifecycle", "outcome", "result", "javaKind", "jvmSteps", "machineRoot", "vfsRoot")
check(all(tuple(heads[q][k] for k in keys) == tuple(heads[1][k] for k in keys) for q in (7, 16)), "q1/q7/q16 machine equivalence")
check(all(heads[q]["stage"] == "final-reopened" for q in heads), "fresh-process durable reopen")

# High-index proof uses only generated classes in its pinned fixture.
high = load(results / "high-array-q16/durable-head.json")
check(high["stage"] == "final-reopened" and high["lifecycle"] == 2 and high["outcome"] == 2 and high["javaKind"] == 0, "high-index EVM terminal")
check(high["counters"]["readFragmentCount"] == 150 and high["totalClassBytes"] == 20158, "150 raw-class high-index input")
check(candidate_pins["arrayHighIndexProof"] == {"rawClasses": 150, "bootstrapCount": 114, "programClassCount": 264, "maxClassIndex": 263, "arrayClassBase": "0x100", "metadataAtMaxClassIndex": "0x207", "rawIndexType": "uint8 coordinator raw class binding unchanged; EVM class metadata uses uint256"}, "high-index pinned arithmetic")

# Atomic, raw EVM refusals: expected selector/arguments and unchanged durable Head/root.
receipt_files = {
    "LinkedHashMapPutDirect": results / "refusals/reports/LinkedHashMapPutDirect-q16/resume-refusal.json",
    "LinkedHashMapPutHashTyped": results / "refusals/reports/LinkedHashMapPutHashTyped-q16-clean/resume-refusal.json",
    "LinkedHashMapPutMapTyped": results / "refusals/reports/LinkedHashMapPutMapTyped-q16-clean/resume-refusal.json",
    "LinkedHashMapUnsupportedInheritedApi": results / "refusals/reports/LinkedHashMapUnsupportedInheritedApi-q16-clean/resume-refusal.json",
    "LinkedHashMapUnsupportedEquals": results / "refusals/reports/LinkedHashMapUnsupportedEquals-q16-clean/resume-refusal.json",
    "LinkedHashMapUnsupportedHash": results / "refusals/reports/LinkedHashMapUnsupportedHash-q16-clean/resume-refusal.json",
    "LinkedHashMapUnsupportedClone": results / "refusals/reports/LinkedHashMapUnsupportedClone-q16-clean/resume-refusal.json",
    "LinkedHashMapUnsupportedDefault": results / "refusals/reports/LinkedHashMapUnsupportedDefault-q16-clean/resume-refusal.json",
}
for name, path in receipt_files.items():
    r = load(path)
    check(r["selector"] == "0xd631c3a4" and r["uint256Words"][0] == "4", f"{name} EVM raw CallError")
    check(r["rootUnchanged"] and r["durableHeadUnchanged"] and r["durableHeadEpochBefore"] == r["durableHeadEpochAfter"], f"{name} atomicity")
for name, expected in (("LinkedHashMapMissingIntConstructor", ["3", "6"]), ("LinkedHashMapRawReplacement", ["1", "1"])):
    r = load(results / f"refusals/reports/{name}-q16-clean/start-refusal.json")
    selector = "0xd631c3a4" if name.endswith("Constructor") else "0x6a23ad80"
    check(r["selector"] == selector and r["uint256Words"] == expected and r["rootUnchanged"] and r["durableHeadUnchanged"], f"{name} atomic refusal")

print(json.dumps({"baseImages":113,"candidateImages":114,"bootstrapRoot":new["root"],"q1q7q16":"PASS","rawRefusals":len(receipt_files)+2,"highIndex":"raw150/class263/metadata0x207 EVM PASS","P48SourceFiles":13},indent=2))
