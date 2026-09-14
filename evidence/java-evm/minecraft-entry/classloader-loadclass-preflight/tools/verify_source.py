#!/usr/bin/env python3
"""Offline integrity checks for the generated-only ClassLoader preflight."""
from pathlib import Path
import hashlib, json, re

here = Path(__file__).resolve().parents[1]
parent = here.parent / "parent-82e4c5116" / "engine" / "MCEntryInterpreter.sol"
source = (here / "engine" / "MCEntryInterpreter.sol").read_text()
prior = parent.read_text()
pat = re.compile(r'function (_bootstrap\w+)\(\).*?return hex"([0-9a-f]+)";', re.S)
old, new = dict(pat.findall(prior)), dict(pat.findall(source))
assert len(old) == len(new) == 66
assert set(old) == set(new)
assert all(name == "_bootstrapClassLoader" or old[name] == image for name, image in new.items())
loader = bytes.fromhex(new["_bootstrapClassLoader"])
assert len(loader) == 777
assert hashlib.sha256(loader).hexdigest() == "2642b16dc68706079058f50f2b08544328c495a23217740499d4bb897ae69e3d"
assert source.count("MC-CLASSLOADER-LOADCLASS1") == 9
assert "new bytes32[](66)" in source and "h[65] = keccak256(_bootstrapBoolean());" in source
assert 'bytes("loadClass0")' in source
assert 'bytes("(Ljava/lang/String;)Ljava/lang/Class;")' in source
assert "binding == 7 || binding == 8" in source
assert "nativeBinding == 8" in source and "_loadClassByBinaryName(" in source
assert "_classMirrorForTarget(" in source and "return _classMirrorForTarget(" in source
pins = json.loads((here / "pins.json").read_text())
engine = json.loads((here / "artifacts" / "engine" / "MCEntryInterpreter.json").read_text())
coord = json.loads((here / "artifacts" / "coordinator" / "MCEntryCoordinator.json").read_text())
run = bytes.fromhex((here / "artifacts" / "engine" / "MCEntryInterpreter.runtime.hex").read_text().strip())
assert len(run) == pins["engine"]["bytes"] == 354483
assert hashlib.sha256(run).hexdigest() == pins["engine"]["runtimeSHA256"]
assert all(engine["codeHashes"][key] == value for key, value in pins["engine"].items() if key != "bytes")
assert coord["codeHashes"]["runtimeKeccak256"] == pins["coordinator"]["runtimeKeccak256"]
heads = {}
for label, epoch in (("direct", 1), ("q1", 52), ("q7", 8)):
    d = here / "receipts" / label
    head = json.loads((d / "durable-head.json").read_text())
    cp = (d / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(cp).hexdigest() == head["checkpointSHA256"]
    assert head["epoch"] == epoch and head["jvmSteps"] == 52 and head["internalSteps"] == 2
    assert head["lifecycle"] == head["outcome"] == 2
    heads[label] = {"epoch": epoch, "machineRoot": head["machineRoot"], "opaqueSHA256": hashlib.sha256(cp[280:]).hexdigest()}
assert len({v["machineRoot"] for v in heads.values()}) == 1
for n, code in (("LoadClassMissingProbe-refusal.json", "2"), ("LoadClassMalformedProbe-refusal.json", "1")):
    r = json.loads((here / "receipts" / "negatives" / n).read_text())
    assert r["selector"] == "0xccb640f4" and r["uint256Words"] == [code, "1"] and r["rootUnchanged"]
(here / "verified.json").write_text(json.dumps({"images": 66, "onlyClassLoaderChanged": True, "heads": heads}, indent=2) + "\n")
print((here / "verified.json").read_text(), end="")
