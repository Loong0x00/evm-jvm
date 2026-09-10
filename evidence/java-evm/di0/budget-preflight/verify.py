#!/usr/bin/env python3
"""Strict report gate for disposable MC-DI0 budget evidence."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
execution = json.loads((root / "execution-report.json").read_text())
trees = json.loads((root / "trees/evm.json").read_text())
java = json.loads((root / "trees/java8.json").read_text())
performance = json.loads((root / "performance-report.json").read_text())
artifact = json.loads((root / "artifact-summary.json").read_text())

ok = {"verified-EVM-output", "expected-EVM-rejection", "expected-constructor-rejection"}
assert len(execution["Results"]) == 37
assert all(row["Outcome"] in ok for row in execution["Results"])
assert max(row["Gas"]["StepMax"] for row in execution["Results"]) < 100_000_000
assert execution["QEquality"]["equal"] is True
assert execution["Controls"]["allExactSelectors"] is True
assert execution["OOG"]["postWriteProof"] is True
assert execution["OOG"]["publishRolledBack"] is True
assert execution["OOG"]["publishRetrySameChild"] is True
assert execution["Persistence"]["successfulDurablePublications"] == 60
assert execution["Persistence"]["distinctChildPIDs"] is True
dynamic = execution["Persistence"]["dynamicCacheFreshProcesses"]
assert dynamic["fixture"] == "deflate-dynamic-go"
assert dynamic["distinctChildPIDs"] is True
assert all(stage["verified"] for stage in dynamic["freshProcessStages"])

assert len(trees) == 29
assert all(row["EVM"]["Outcome"] in ok for row in trees)
assert max(row["EVM"]["Gas"]["StepMax"] for row in trees) < 100_000_000
by_name = {row["Name"]: row["EVM"] for row in trees}
for name in ("deep-full-tree-q128", "many-empty-dynamic-q64", "many-empty-dynamic-q128"):
    assert by_name[name]["Outcome"] == "verified-EVM-output"
assert by_name["fixed-reserved-literal-286"]["Error"] == 15
assert by_name["fixed-reserved-literal-287"]["Error"] == 15
assert by_name["fixed-reserved-distance-30"]["Error"] == 16
assert by_name["fixed-reserved-distance-31"]["Error"] == 16

assert java["javaVersion"] == "1.8.0_504"
jby = {row["name"]: row for row in java["fixtures"]}
assert set(jby) == set(by_name)
for name, evm in by_name.items():
    j = jby[name]
    if evm["Outcome"] == "verified-EVM-output":
        assert not j["inflaterError"] and j["finished"] and j["remaining"] == 0
        assert not j["zipFileError"] and not j["zipInputStreamError"]
        assert j["plainBytes"] == evm["Plain"] == j["zipFileBytes"] == j["zipInputStreamBytes"]
    else:
        assert j["inflaterError"] and j["zipFileError"] and j["zipInputStreamError"]

assert performance["artifactSHA"] == artifact["artifact"]["reproducibleIgnoredJSONSHA256"]
assert performance["allEqual"] and performance["allCallsBelow100M"]
assert len(performance["pairs"]) == 4 and all(pair["equal"] for pair in performance["pairs"])
assert len(performance["sweeps"]) == 3
assert all(sweep["quantums"] == 128 and sweep["allEqual"] and sweep["maxStepGas"] < 100_000_000 for sweep in performance["sweeps"])
assert artifact["artifact"]["runtimeBytes"] <= artifact["limitsUnchanged"]["runtimeBytes"]
assert artifact["artifact"]["maxCompleteInitBytesFor256ByteName"] <= artifact["limitsUnchanged"]["completeInitBytes"]
print("STRICT PASS: 37 original, 29 tree/Java8, 4 same-binding pairs, 3 complete q1..q128 sweeps")
