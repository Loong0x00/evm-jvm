#!/usr/bin/env python3
"""Independently check durable generated-only identity-hash summaries.

This consumes only tracked JSON summaries. It never parses Java, ZIP, class,
resource, or original input and grants no execution authority.
"""
from pathlib import Path
import hashlib
import json

stage = Path(__file__).resolve().parent.parent
results = stage / "results"
pins = json.loads((results / "build-pins.json").read_text())
fixtures = json.loads((results / "fixture-summary.json").read_text())
gate = json.loads((results / "gate-summary.json").read_text())
manifest = json.loads((results / "manifest.json").read_text())
timing = json.loads((results / "timing.json").read_text())
source = json.loads((results / "source-verification.json").read_text())
receipts = json.loads((results / "canonical-receipts.json").read_text())

assert pins["rawLimits"] == [70, 464925] and pins["diagnosticClassBound"] == 166
assert pins["bootstrapCount"] == 96 and pins["bootstrapRoot"] == manifest["bootstrapRoot"]
assert pins["bootstrapRoot"] == "6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77"
assert pins["globalNativeBindings"] == 17 and pins["stringLocalBinding"] == 12
assert pins["system"]["sha256"] == "6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564"
assert pins["engine"]["bytes"] == 380017 <= 393216
assert source["changedBootstrapLeaves"] == [44] and source["bootstrapRoot"] == pins["bootstrapRoot"]
assert source["globalNativeBindings"] == 17 and source["stringLocalBinding"] == 12

assert fixtures["generatedOnly"] and fixtures["bootstrapCount"] == 96 and fixtures["rawLimits"] == [70, 464925]
for label in ("identity-hash", "identity-no-mutation-control", "object-hashcode-omitted", "system-general-omitted", "raw-system-replacement", "retained-system-out-err", "count-70"):
    assert label in fixtures["fixtures"], label
for label, count, total in (("count-70", 70, None), ("count-71", 71, None),
                            ("count-70-464925", 70, 464925), ("count-70-464926", 70, 464926)):
    row = fixtures["fixtures"][label]
    assert row["bindingCount"] == count
    if total is not None:
        assert row["totalClassBytes"] == total and max(row["classBytes"].values()) <= 262144

assert gate["profile"] == manifest["profile"] == "MC-SYSTEM-IDENTITY-HASH-P1"
assert gate["generatedOnly"] and gate["bootstrapCount"] == 96 and gate["rawLimits"] == [70, 464925]
assert gate["diagnosticClassBound"] == 166 and gate["globalNativeBindings"] == 17 and gate["stringLocalBinding"] == 12
assert gate["engineBytes"] == manifest["engineBytes"] == 380017
assert timing["wholeGateSeconds"] == gate["wholeGateSeconds"] <= timing["limitSeconds"] == 1200
assert timing["commands"] == len(gate["commands"]) == manifest["commands"]
assert timing["canonicalReceipts"] == gate["canonicalReceipts"]["verifiedReceipts"] == receipts["verifiedReceipts"] == manifest["canonicalReceipts"]
assert timing["canonicalReceipts"] == 2227

for label in ("identity-hash", "identity-no-mutation-control", "retained-system-out-err", "lower-ascii", "locale-root", "retained-string", "retained-map", "retained-integer", "count-70"):
    rows = gate["results"][label]
    assert set(rows) == {"q1", "q7", "direct"}, label
    baseline = rows["q1"]
    for value in rows.values():
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
            assert value[key] == baseline[key], (label, key)

for label in ("raw-string-replacement", "raw-locale-replacement", "raw-system-replacement"):
    rows = gate["results"][label]
    assert set(rows) == {"q1", "q7", "direct"}
    for row in rows.values():
        assert row["selector"] == "0x6a23ad80" and row["uint256Words"][0] == "1" and row["rootUnchanged"]
for label in ("object-hashcode-omitted", "system-general-omitted"):
    rows = gate["results"][label]
    assert set(rows) == {"q1", "q7", "direct"}
    for row in rows.values():
        assert row["selector"] == "0xd631c3a4" and row["uint256Words"][0] == "3" and row["rootUnchanged"]

assert gate["results"]["raw71-driver"] == {"worldExists": False}
for label, expected_words in (("raw71-coordinator", ["2"]), ("raw71-engine", ["1", "71"]), ("byte-464926", ["12"])):
    row = gate["results"][label]
    assert row["selector"] == ("0x427cfac5" if label == "raw71-engine" else "0xab23ed08")
    assert row["uint256Words"] == expected_words and row["rootUnchanged"]
    assert row["candidateCheckpoint"] == row["candidateHead"] == ""
byte_ok = gate["results"]["byte-464925"]["checkpointCapRefusal"]
assert byte_ok["selector"] == "0x71540d20" and byte_ok["uint256Words"] == ["1", "0"]
assert byte_ok["rootUnchanged"] and byte_ok["candidateCheckpoint"] == byte_ok["candidateHead"] == ""
assert sum(byte_ok["actualDI0ReadSizes"]) == 464925

for name, expected in manifest["files"].items():
    assert hashlib.sha256((results / name).read_bytes()).hexdigest() == expected, name
print(json.dumps({
    "verified": "durable-generated-identity-handle+q1-q7-direct-reopen+retained-capacity+canonical-receipt-summaries",
    "bootstrapRoot": pins["bootstrapRoot"], "globalNativeBindings": 17,
    "wholeGateSeconds": gate["wholeGateSeconds"], "commands": len(gate["commands"]),
    "canonicalReceipts": timing["canonicalReceipts"],
}, indent=2))
