#!/usr/bin/env python3
"""Source-only P47-to-candidate consistency verifier; never opens original inputs."""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / "source-basis"
MANIFEST = json.loads((BASE / "source-manifest.json").read_text())

for rel, pin in MANIFEST["files"].items():
    raw = (BASE / rel).read_bytes()
    assert len(raw) == pin["bytes"], rel
    assert hashlib.sha256(raw).hexdigest() == pin["sha256"], rel

candidate_manifest = json.loads((HERE / "manifest.json").read_text())
actual_candidate_files = {
    p.relative_to(HERE).as_posix()
    for p in HERE.rglob("*")
    if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts and p.suffix != ".pyc"
}
assert actual_candidate_files == set(candidate_manifest["files"]), "candidate manifest file set differs"
for rel, pin in candidate_manifest["files"].items():
    raw = (HERE / rel).read_bytes()
    assert len(raw) == pin["bytes"], rel
    assert hashlib.sha256(raw).hexdigest() == pin["sha256"], rel

spec = importlib.util.spec_from_file_location("p47_root_helper", BASE / "root_helper.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def domain(source):
    m = re.search(r'DBOOT\s*=\s*keccak256\("([^"]+)"\)', source)
    assert m
    return m.group(1)


def root_record(source_path):
    source = source_path.read_text()
    return helper.root_record(source, domain(source), str(ROOT), os.environ)


def keccak(raw):
    return subprocess.check_output(
        ["node", "-e", "const {keccak256:k}=require('js-sha3');process.stdout.write(k(Buffer.from(process.argv[1],'hex')))", raw.hex()],
        cwd=ROOT, env=os.environ, text=True,
    ).strip()

base_src = BASE / "engine/MCEntryInterpreter.sol"
candidate_src = HERE / "engine/MCEntryInterpreter.sol"
old = root_record(base_src)
new = root_record(candidate_src)
base_pins = json.loads((BASE / "pins.json").read_text())
assert len(old["leaves"]) == 113
assert old["root"] == base_pins["bootstrapRoot"]
assert new["root"] == json.loads((HERE / "bootstrap-root.json").read_text())["bootstrapRoot"]
assert len(new["leaves"]) == 113
old_pairs = helper.leaf_pairs(base_src.read_text())
new_pairs = helper.leaf_pairs(candidate_src.read_text())
changed = [i for i, (a, b) in enumerate(zip(old_pairs, new_pairs)) if a != b]
assert changed == [53, 110], changed
for i in (40, 94, 100, 104):
    assert old_pairs[i] == new_pairs[i], ("fixed leaf changed", i)

images = {
    53: HERE / "class-images/java/util/Collection.class",
    100: HERE / "class-images/java/util/HashMap.class",
    104: HERE / "class-images/java/util/HashMap$Node.class",
    110: HERE / "class-images/java/util/HashMap$EntrySet.class",
    94: HERE / "class-images/java/util/Map$Entry.class",
}
for i, path in images.items():
    assert keccak(path.read_bytes()) == new["leaves"][i], (i, path)
assert images[100].read_bytes().hex() == re.search(
    r'function _bootstrapHashMap\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',
    base_src.read_text(),
).group(1)
assert images[104].read_bytes().hex() == re.search(
    r'function _bootstrapHashMapNode\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',
    base_src.read_text(),
).group(1)

engine = json.loads((HERE / "engine/MCEntryInterpreter.json").read_text())
coord = json.loads((HERE / "coordinator/MCEntryCoordinator.json").read_text())
base_engine = json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())
base_coord = json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())
assert engine["abi"] == base_engine["abi"]
assert engine["storageLayout"] == base_engine["storageLayout"]
assert coord["abi"] == base_coord["abi"]
assert coord["storageLayout"] == base_coord["storageLayout"]
assert coord["codeHashes"]["runtimeKeccak256"] != base_coord["codeHashes"]["runtimeKeccak256"]
coord_source = (HERE / "coordinator/MCEntryCoordinator.sol").read_text()
assert f'ENGINE_CODEHASH = hex"{engine["codeHashes"]["runtimeKeccak256"]}"' in coord_source
assert engine["sourceHashes"]["MCEntryInterpreter.sol"] == hashlib.sha256(candidate_src.read_bytes()).hexdigest()
assert coord["sourceHashes"]["MCEntryCoordinator.sol"] == hashlib.sha256((HERE / "coordinator/MCEntryCoordinator.sol").read_bytes()).hexdigest()

print(json.dumps({
    "sourceManifestEntriesVerified": len(MANIFEST["files"]),
    "bootstrapCount": len(new["leaves"]),
    "baseRoot": old["root"],
    "candidateRoot": new["root"],
    "changedLeaves": changed,
    "unchangedMap40MapEntry94HashMap100Node104": True,
    "engineABIStorageUnchanged": True,
    "coordinatorABIStorageUnchanged": True,
    "coordinatorEngineCodehashMatches": True,
}, indent=2))
