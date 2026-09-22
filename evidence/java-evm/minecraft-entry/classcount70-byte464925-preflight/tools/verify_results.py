#!/usr/bin/env python3
"""Independently check durable generated-only raw70 result summaries.

This consumes JSON summaries only. It does not parse Java, ZIP, class, resource,
or original input, and grants no execution authority.
"""
from pathlib import Path
import json

stage = Path(__file__).resolve().parent.parent
results = stage / "results"
pins = json.loads((results / "build-pins.json").read_text())
fixtures = json.loads((results / "fixture-summary.json").read_text())
gate = json.loads((results / "gate-summary.json").read_text())
manifest = json.loads((results / "manifest.json").read_text())
timing = json.loads((results / "timing.json").read_text())

assert pins["rawLimits"] == [70, 464925] and pins["diagnosticClassBound"] == 166
assert pins["bootstrapCount"] == 96 and pins["bootstrapRoot"] == manifest["bootstrapRoot"]
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] == 379383 <= 393216
assert fixtures["generatedOnly"] and fixtures["bootstrapCount"] == 96 and fixtures["rawLimits"] == [70, 464925]
for label, count, total in (("count-70", 70, None), ("count-71", 71, None),
                            ("count-70-464925", 70, 464925), ("count-70-464926", 70, 464926)):
    row = fixtures["fixtures"][label]
    assert row["bindingCount"] == count
    if total is not None:
        assert row["totalClassBytes"] == total and max(row["classBytes"].values()) <= 262144

assert gate["profile"] == manifest["profile"] == "MC-CLASSCOUNT70-BYTE464925-P1"
assert gate["generatedOnly"] and gate["bootstrapCount"] == 96 and gate["rawLimits"] == [70, 464925]
assert gate["diagnosticClassBound"] == 166 and gate["globalNativeBindings"] == 16 and gate["stringLocalBinding"] == 12
assert gate["engineBytes"] == manifest["engineBytes"] == 379383
assert timing["wholeGateSeconds"] == gate["wholeGateSeconds"] <= timing["limitSeconds"] == 1200
assert timing["commands"] == len(gate["commands"]) and timing["canonicalReceipts"] == gate["canonicalReceipts"]["verifiedReceipts"]
assert manifest["commands"] == timing["commands"] and manifest["canonicalReceipts"] == timing["canonicalReceipts"]

for label in ("lower-ascii", "lower-null-caught", "lower-null-uncaught", "locale-root",
              "retained-string", "retained-map", "retained-integer", "count-70"):
    rows = gate["results"][label]
    assert set(rows) == {"q1", "q7", "direct"}, label
    base = rows["q1"]
    for value in rows.values():
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
            assert value[key] == base[key], (label, key)

assert gate["results"]["raw71-driver"] == {"worldExists": False}
for label, expected_words in (("raw71-coordinator", ["2"]), ("raw71-engine", ["1", "71"]),
                              ("byte-464926", ["12"])):
    row = gate["results"][label]
    assert row["selector"] == "0xab23ed08" if label != "raw71-engine" else row["selector"] == "0x427cfac5"
    assert row["uint256Words"] == expected_words and row["rootUnchanged"]
    assert row["candidateCheckpoint"] == row["candidateHead"] == ""

engine_refusal = gate["results"]["raw71-engine"]
assert len(engine_refusal["actualDI0ReadSizes"]) == 71
byte_ok = gate["results"]["byte-464925"]["checkpointCapRefusal"]
assert byte_ok["selector"] == "0x71540d20" and byte_ok["uint256Words"] == ["1", "0"]
assert byte_ok["rootUnchanged"] and byte_ok["candidateCheckpoint"] == byte_ok["candidateHead"] == ""
assert sum(byte_ok["actualDI0ReadSizes"]) == 464925
assert gate["canonicalReceipts"]["verifiedReceipts"] > 0

print(json.dumps({
    "verified": "durable-generated-only-summary-boundaries+q1-q7-direct-reopen-equivalence+canonical-receipt-count",
    "rawLimits": [70, 464925], "diagnosticClassBound": 166,
    "bootstrapRoot": pins["bootstrapRoot"], "wholeGateSeconds": gate["wholeGateSeconds"],
    "commands": len(gate["commands"]), "canonicalReceipts": gate["canonicalReceipts"]["verifiedReceipts"],
}, indent=2))
