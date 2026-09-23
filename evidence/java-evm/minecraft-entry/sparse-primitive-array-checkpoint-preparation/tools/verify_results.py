#!/usr/bin/env python3
"""Verify the archived generated-only sparse checkpoint candidate evidence."""
from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile

stage = Path(__file__).resolve().parent.parent
archive = stage / "results/generated-gate-v1"
pins = json.loads((archive / "build-pins.json").read_text())
baseline = json.loads((archive / "baseline-pins.json").read_text())
source = json.loads((archive / "source-invariants.json").read_text())
gate = json.loads((archive / "gate-summary.json").read_text())
receipts = json.loads((archive / "canonical-receipts.json").read_text())
proof = json.loads((archive / "checkpoint-proof.json").read_text())
manifest = json.loads((archive / "manifest.json").read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()

ROOT = "7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887"
assert pins["domain"] == "MC-RANDOM-CLASS-P2"
assert gate["profile"] == "MC-RANDOM-CLASS-P2-SPARSE-CHECKPOINT"
assert gate["generatedOnly"] and manifest["generatedOnly"]
assert pins["bootstrapCount"] == gate["bootstrapCount"] == 97
assert pins["bootstrapRoot"] == gate["bootstrapRoot"] == source["bootstrapRoot"] == ROOT
assert source["bootstrapSourceAndRootByteIdentical"] is True
assert pins["rawLimits"] == gate["rawLimits"] == [71, 471911]
assert pins["globalNativeBindings"] == gate["globalNativeBindings"] == 18
assert pins["stringLocalBinding"] == gate["stringLocalBinding"] == 12
assert pins["diagnosticClassBound"] == gate["diagnosticClassBound"] == 168
assert pins["engine"]["bytes"] == gate["engineBytes"] == 385803 <= pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == gate["externalLocalGas"] == 1000000000
assert pins["coordinator"]["bytes"] == baseline["coordinator"]["bytes"] == 5394
assert sha((stage / "engine/MCEntryInterpreter.sol").read_bytes()) == source["candidateSourceSHA256"]
assert source["candidateSourceSHA256"] == manifest["candidateSourceSHA256"]
assert source["baselineCommit"] == "511c20c4b"
assert source["onlySemanticFunctionsChanged"] == ["_machineSize", "_encodeMachine", "_decodeMachine"]
assert source["runtimeCapBytes"] == 393216
assert pins["sparseWire"] == gate["sparseWire"] == proof["sparseWire"]
assert pins["sparseWire"]["flag"] == "0x80000000" and pins["sparseWire"]["minimumLength"] == 1024
assert gate["wholeGateSeconds"] == manifest["gateSeconds"] <= manifest["limitSeconds"] == 1200
assert receipts["verifiedReceipts"] == gate["canonicalReceipts"]["verifiedReceipts"] == 3068

stress = gate["results"]["sparse-array-stress"]
assert set(stress) == {"q1", "q7", "direct"}
first = stress["q1"]
for quantum, row in stress.items():
    assert row["machineRoot"] == first["machineRoot"]
    assert row["opaquePayloadSHA256"] == first["opaquePayloadSHA256"]
    assert row["jvmSteps"] == first["jvmSteps"] and row["jvmSteps"] > 0
    assert row["lifecycle"] == 2 and row["javaKind"] == 0
    assert row["heapCounts"]["arrayElements"] == 197638
arrays = [row for row in first["heap"] if row["rank"] == 1]
large = [row for row in arrays if row["count"] == 65536]
assert len(large) == 3 and all(row["sparse"] for row in large)
assert {row["metadata"] for row in large} == {"0x46", "0x49", "0x44"}
assert sorted(row["sparseCount"] for row in large) == [0, 1, 3]
by_leaf = {row["metadata"]: row for row in large}
assert by_leaf["0x46"]["sparseCount"] == 0
assert [(c["index"], int(c["value"], 16) & 0xffffffff) for c in by_leaf["0x49"]["sparseCells"]] == [(65535, 5)]
assert [(c["index"], int(c["value"], 16)) for c in by_leaf["0x44"]["sparseCells"]] == [(0, 0x3ff4000000000000), (32768, 0xc004000000000000), (65535, 0x400e000000000000)]
refs = [row for row in arrays if row["count"] == 1024]
assert len(refs) == 1 and not refs[0]["sparse"]
small = [row for row in arrays if row["count"] == 2]
assert len(small) == 1 and not small[0]["sparse"]

boundary = gate["results"]["array-savings-boundary"]["direct"]
boundary_arrays = [row for row in boundary["heap"] if row["rank"] == 1 and row["count"] == 1024]
assert sorted(row["sparseCount"] if row["sparse"] else -1 for row in boundary_arrays) == [-1, 511]
assert boundary["lifecycle"] == 2 and boundary["jvmSteps"] == 8226

q1 = proof["q1CommittedArrayParentChild"]
parent_cp = (archive / "checkpoints/sparse-array-stress-q1-parent-array.bin").read_bytes()
assert sha(parent_cp) == q1["parentCheckpointSHA256"]
assert len(parent_cp) == q1["parentCheckpointBytes"] and q1["largePrimitiveArrays"] == 1
spec = importlib.util.spec_from_file_location("sparseCheckpointDiagnostic", stage / "tools/checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
parent_state = diagnostic.inspect(parent_cp)
assert any(row["count"] == 65536 and row["sparse"] for row in parent_state["heap"])
child = json.loads((archive / ("receipts/sparse-array-stress-q1-slice-%d.json" % q1["childEpoch"])).read_text())
assert child["epoch"] == q1["childEpoch"] and child["method"] == "resumeMain"
assert child["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
assert child["suppliedGas"] == pins["externalLocalGas"] == 1000000000
assert child["gasUsed"] == q1["childGasUsed"] <= 1000000000
assert child["elapsedMS"] == q1["childElapsedMS"] <= 30000

for label, row in proof["malformedRefusals"].items():
    assert row["selector"] == "0x71540d20" and row["error"] == "LC0StateError"
    assert row["code"] == row["expectedCode"] and row["rootUnchanged"]
    assert row["headUnchanged"] and row["logsUnchanged"]
    if label == "sparse-noncanonical-dense-refusal": assert row["code"] == 3
    elif label == "sparse-truncated-pairs-refusal": assert row["code"] == 2
    else: assert row["code"] == 6

probe = gate["results"]["byte-471911"]
assert probe["classification"] == "EXPECTED_LOCAL1B_OUT_OF_GAS_NOT_CHECKPOINT_CAP_ACCEPTANCE"
assert probe["allClassBytesRead"] is True
assert sum(probe["localCeilingProbe"]["actualDI0ReadSizes"]) == 471911
assert probe["localCeilingProbe"]["selector"] == "0x"
assert probe["localCeilingProbe"]["rootUnchanged"] and probe["localCeilingProbe"]["checkpointBytes"] == 0
assert gate["results"]["byte-471912"]["selector"] == "0xab23ed08"
assert gate["results"]["byte-471912"]["uint256Words"] == ["12"]

for label in ("sparse-array-stress", "array-savings-boundary", "count-71", "count-72",
              "count-71-471911", "count-71-471912"):
    metadata = json.loads((archive / ("fixtures/" + label + ".json")).read_text())
    bundle = archive / ("fixtures/" + label + ".zip")
    assert sha(bundle.read_bytes()) == metadata["zipSHA256"]
    with zipfile.ZipFile(bundle) as z:
        for name, digest in metadata["classSHA256"].items():
            assert sha(z.read(name)) == digest, (label, name)
assert json.loads((archive / "fixtures/sparse-array-stress.json").read_text())["java8HostOracle"]

for name, digest in manifest["files"].items():
    assert sha((archive / name).read_bytes()) == digest, name
for line in (archive / "SHA256SUMS").read_text().splitlines():
    digest, name = line.split("  ", 1)
    assert sha((archive / name).read_bytes()) == digest, name
assert "manifest.json" in {line.split("  ", 1)[1] for line in (archive / "SHA256SUMS").read_text().splitlines()}
print(json.dumps({"verified": "generated-only sparse-array canonical checkpoint + q1/q7/direct/reopen + atomic refusals",
                  "bootstrapRoot": ROOT, "engineBytes": pins["engine"]["bytes"],
                  "wholeGateSeconds": gate["wholeGateSeconds"], "canonicalReceipts": receipts["verifiedReceipts"],
                  "knownNonAcceptance": probe["classification"],
                  "originalReplay": "deferred to parent"}, indent=2))
