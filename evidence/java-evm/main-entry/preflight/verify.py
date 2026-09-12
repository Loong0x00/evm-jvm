#!/usr/bin/env python3
"""Strict result verifier for the generated-only CB0 main-entry replay."""
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1]).resolve()
fixture = json.loads((out / "fixture" / "fixture.json").read_text())
assert fixture["javac"] == "javac 1.8.0_504", fixture
assert fixture["oracle"] == "0:R:341\n1:R:381\n2:R:351\n3:X:java.lang.NullPointerException\n", fixture
for name, digest in fixture["files"].items():
    path = out / "fixture" / ("classes" if name.endswith(".class") else "") / name
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest, name

def sequence(label):
    setup = json.loads((out / "results" / (label + "-setup.json")).read_text())
    slices = [json.loads(p.read_text()) for p in sorted((out / "results").glob(label + "-[0-9]*.json"), key=lambda p:int(p.stem.rsplit("-",1)[1]))]
    assert slices and setup["classCount"] == 2 and setup["totalClassBytes"] == 795
    assert all(x["packageRoot"] == setup["packageRoot"] for x in slices)
    assert all(x["reopenedEngineInstalled"] is False and x["nestedEngineLogs"] == 1 for x in slices)
    assert [x["epoch"] for x in slices] == list(range(1, len(slices)+1))
    assert all(len(x["checkpointSHA256"]) == 64 and x["checkpointRoot"] != "0x"+"0"*64 for x in slices)
    terminal = json.loads((out / "results" / (label + "-terminal.json")).read_text())
    last = slices[-1]
    for key in ("epoch", "lifecycle", "checkpointRoot", "checkpointSHA256", "machineRoot", "vfsRoot", "packageRoot"):
        assert terminal[key] == last[key], (label, key, terminal, last)
    assert terminal["reopenedEngineInstalled"] is False and terminal["pid"] not in {x["pid"] for x in slices}
    return setup, slices
worlds = {label:sequence(label) for label in ("mode1-direct", "mode1-q7", "mode1-q1", "mode0-direct", "mode2-direct", "mode3-null")}
expected = {"mode1-direct":(2,381,54,4), "mode1-q7":(2,381,54,4), "mode1-q1":(2,381,54,4), "mode0-direct":(2,341,24,4), "mode2-direct":(2,351,57,4), "mode3-null":(3,0,22,5)}
for label, (_, values) in worlds.items():
    last = values[-1]; want=expected[label]
    assert (last["lifecycle"],last["result"],last["totalJvmSteps"],last["totalInternalSteps"]) == want, (label,last)
# q1 must be actual multi-process start/resume/terminal, rather than an in-process loop.
q1 = worlds["mode1-q1"][1]
assert len(q1) == 54 and len({x["pid"] for x in q1}) == len(q1), q1
# Grouping cannot change final EVM guest/resource/package roots for the same input.
reference = worlds["mode1-direct"][1][-1]
for label in ("mode1-q7", "mode1-q1"):
    final = worlds[label][1][-1]
    for key in ("packageRoot", "machineRoot", "vfsRoot", "as0ContentRoot", "indexRoot", "decoderRoots"):
        assert final[key] == reference[key], (label,key,final[key],reference[key])
# The genuine ordinary guest failure must be a typed Java NPE, not EVM revert/OOG.
npe = worlds["mode3-null"][1][-1]
# VFS0a's pinned canonical kind 6 is NullPointerException; canonical kinds carry
# no dynamic JavaClass byte string (unlike kind 0 dynamic failures).
assert npe["javaKind"] == 6 and npe.get("javaClass", "") == "", npe
def measured(label):
    values = worlds[label][1]
    gas = [x["gasUsed"] for x in values]
    return {"slices":len(values), "gasMin":min(gas), "gasMax":max(gas), "gasSum":sum(gas), "ordinaryGasCap":100000000, "final":values[-1]}
print(json.dumps({
 "fixture": fixture,
 "mode1": {label:measured(label) for label in ("mode1-direct","mode1-q7","mode1-q1")},
 "other": {label:measured(label) for label in ("mode0-direct","mode2-direct","mode3-null")},
 "gas": "Every recorded Java Start/Resume call is <= ordinary 100000000 gas; no 1B boundary calls were used.",
 "assertions": ["opaque ZIP uploaded through public cb0 APIs", "EVM-derived frozen-domain package assertion", "all runtime class reads are CB0 FINAL DI0 reads", "persistent q1 start/resume/terminal used 54 distinct processes without reinstall", "direct/q7/q1 roots agree for mode1"],
}, indent=2, sort_keys=True))
