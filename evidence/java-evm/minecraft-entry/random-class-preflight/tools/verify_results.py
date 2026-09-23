#!/usr/bin/env python3
"""Verify archived generated-only Random class gate summaries and hashes."""
from pathlib import Path
import hashlib
import json

stage = Path(__file__).resolve().parent.parent
results = stage / "results"
pins = json.loads((results / "build-pins.json").read_text())
source = json.loads((results / "source-verification.json").read_text())
fixtures = json.loads((results / "fixture-summary.json").read_text())
gate = json.loads((results / "gate-summary.json").read_text())
receipts = json.loads((results / "canonical-receipts.json").read_text())
timing = json.loads((results / "timing.json").read_text())
manifest = json.loads((results / "manifest.json").read_text())

ROOT = "7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887"
RANDOM = "8d2a1e974c79f6a2a0344a5c776f5feb7b7f09eb7431bd02d54d75518bf76bf3"
assert pins["domain"] == gate["profile"] == manifest["profile"] == "MC-RANDOM-CLASS-P1"
assert pins["rawLimits"] == [71, 471911] and pins["bootstrapCount"] == 97 and pins["diagnosticClassBound"] == 168
assert pins["bootstrapRoot"] == ROOT and pins["globalNativeBindings"] == 18 and pins["stringLocalBinding"] == 12
assert pins["random"]["sha256"] == RANDOM and pins["random"]["slot"] == 96 and pins["engine"]["bytes"] == 383245 <= 393216
assert source["bootstrapRoot"] == ROOT and source["prior96LeavesExact"] is True
assert source["random"]["sha256"] == RANDOM and source["globalNativeBindings"] == 18 and source["stringLocalBinding"] == 12
assert fixtures["generatedOnly"] and fixtures["bootstrapCount"] == 97 and fixtures["rawLimits"] == [71, 471911]
for label in ("random-construction", "random-next-int-omitted", "random-set-seed-omitted", "raw-random-replacement",
              "math-sqrt-binary64", "identity-hash", "retained-properties", "count-71", "count-72",
              "count-71-471911", "count-71-471912"):
    assert label in fixtures["fixtures"], label
assert fixtures["fixtures"]["random-construction"]["bindingCount"] == 1
assert not fixtures["fixtures"]["random-construction"]["java8HostOracle"]
assert fixtures["fixtures"]["raw-random-replacement"]["classSHA256"]["java/util/Random.class"] == RANDOM
for label, total in (("count-71-471911", 471911), ("count-71-471912", 471912)):
    row = fixtures["fixtures"][label]
    assert row["bindingCount"] == 71 and row["totalClassBytes"] == total and max(row["classBytes"].values()) <= 262144
assert gate["generatedOnly"] and gate["rawLimits"] == [71, 471911] and gate["bootstrapRoot"] == ROOT
assert gate["bootstrapCount"] == 97 and gate["diagnosticClassBound"] == 168
assert gate["globalNativeBindings"] == 18 and gate["stringLocalBinding"] == 12 and gate["randomSHA256"] == RANDOM
assert timing["wholeGateSeconds"] == gate["wholeGateSeconds"] <= timing["limitSeconds"] == 1200
assert timing["commands"] == len(gate["commands"])
assert timing["canonicalReceipts"] == receipts["verifiedReceipts"] == gate["canonicalReceipts"]["verifiedReceipts"]
for label in ("random-construction", "math-sqrt-binary64", "retained-properties", "identity-hash",
              "retained-system-out-err", "lower-ascii", "locale-root", "retained-string",
              "retained-map", "retained-integer", "count-71"):
    rows = gate["results"][label]
    assert set(rows) == {"q1", "q7", "direct"}, label
    first = rows["q1"]
    for value in rows.values():
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
            assert value[key] == first[key], (label, key)
for label in ("raw-math-replacement", "raw-random-replacement", "raw-string-replacement", "raw-locale-replacement", "raw-system-replacement"):
    for value in gate["results"][label].values():
        assert value["selector"] == "0x6a23ad80" and value["uint256Words"][0] == "1" and value["rootUnchanged"]
for label in ("random-next-int-omitted", "random-set-seed-omitted", "math-cbrt-omitted", "object-hashcode-omitted", "system-general-omitted"):
    for value in gate["results"][label].values():
        assert value["selector"] == "0xd631c3a4" and value["uint256Words"][0] == "3" and value["rootUnchanged"]
for value in gate["results"]["strictmath-sqrt-omitted"].values():
    assert value["selector"] == "0x555db429" and value["uint256Words"][0] == "4107" and value["rootUnchanged"]
assert gate["results"]["raw72-driver"] == {"worldExists": False}
for label, selector, words in (("raw72-coordinator", "0xab23ed08", ["2"]),
                               ("raw72-engine", "0x427cfac5", ["1", "72"]),
                               ("byte-471912", "0xab23ed08", ["12"])):
    value = gate["results"][label]
    assert value["selector"] == selector and value["uint256Words"] == words and value["rootUnchanged"]
exact = gate["results"]["byte-471911"]["checkpointCapRefusal"]
assert exact["selector"] == "0x71540d20" and exact["uint256Words"] == ["1", "0"]
assert exact["rootUnchanged"] and sum(exact["actualDI0ReadSizes"]) == 471911
for name, digest in manifest["files"].items():
    assert hashlib.sha256((results / name).read_bytes()).hexdigest() == digest, name
print(json.dumps({"verified": "generated-random-link-construction+prior96+q1-q7-direct-reopen+retained-raw71",
                  "bootstrapRoot": ROOT, "randomSHA256": RANDOM,
                  "engineBytes": pins["engine"]["bytes"], "wholeGateSeconds": gate["wholeGateSeconds"],
                  "canonicalReceipts": receipts["verifiedReceipts"]}, indent=2))
