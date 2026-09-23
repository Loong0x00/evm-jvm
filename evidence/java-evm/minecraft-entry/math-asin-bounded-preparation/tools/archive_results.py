#!/usr/bin/env python3
"""Archive generated-only Math.asin, retained Math, and sparse evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 4
build, fixtures, gate = [Path(value).resolve() for value in sys.argv[1:4]]
assert build.parent == fixtures.parent == gate.parent == root / "build"
assert build.name.startswith("java-diff-mc-math-asin-build-")
assert fixtures.name.startswith("java-diff-mc-math-asin-fixtures-")
assert gate.name.startswith("java-diff-mc-math-asin-gate-")
dest = stage / "results/generated-gate-v1"
assert not dest.exists(), f"refuse to overwrite durable evidence: {dest}"
summary = json.loads((gate / "summary.json").read_text())
assert summary["wholeGateSeconds"] <= 1200
pins = json.loads((build / "pins.json").read_text())
fixtures_summary = json.loads((fixtures / "summary.json").read_text())
assert pins["bootstrapRoot"] == summary["bootstrapRoot"]
assert pins["engine"]["bytes"] == summary["engineBytes"]
assert summary["profile"] == "MC-RANDOM-CLASS-P2-MATH-ASIN-BOUNDED-Q120"

dest.mkdir(parents=True)

def copy(source, relative):
    source = Path(source)
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target

copy(build / "pins.json", "build-pins.json")
copy(gate / "summary.json", "gate-summary.json")
copy(gate / "q120-test-only-model.json", "q120-test-only-model.json")
copy(stage / "tools/verify_q120.py", "tools/verify_q120.py")
copy(gate / "logs/canonical-receipts.log", "canonical-receipts.json")
copy(stage / "results/source-invariants.json", "source-invariants.json")
copy(stage / "root-commitment.json", "root-commitment.json")
copy(stage / "baseline-pins.json", "baseline-pins.json")
copy(stage / "bootstrap/java/lang/Math.java", "bootstrap/Math.java")
copy(stage / "bootstrap/java/lang/Math.class.hex", "bootstrap/Math.class.hex")
copy(stage / "bootstrap/java/lang/Math.sha256", "bootstrap/Math.sha256")
copy(build / "engine/MCEntryInterpreter.runtime.hex", "artifacts/engine-runtime.hex")
copy(build / "coordinator/MCEntryCoordinator.runtime.hex", "artifacts/coordinator-runtime.hex")

# Retain every generated fixture's exact bytes and Java-8 class/ZIP hashes.
for label in fixtures_summary["fixtures"]:
    copy(fixtures / (label + ".zip"), "fixtures/" + label + ".zip")
    copy(fixtures / (label + ".json"), "fixtures/" + label + ".json")
copy(fixtures / "summary.json", "fixtures/summary.json")

# Preserve q1/q7/direct terminal checkpoints and heads for asin and retained sine
# edge/grid witnesses, sqrt, sparse stress and the strict-saving boundary.
for label in ("math-asin-bounded-edges", "math-sin-bounded-edges", "math-sin-bounded-grid", "math-sqrt-binary64", "sparse-array-stress"):
    for quantum in (1, 7, 4096):
        world_name = "world-" + label + "-q" + str(quantum)
        world = gate / world_name
        head = json.loads((world / "durable-head.json").read_text())
        cp = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
        assert hashlib.sha256(cp.read_bytes()).hexdigest() == head["checkpointSHA256"]
        copy(cp, "checkpoints/" + world_name + ".bin")
        copy(world / "durable-head.json", "heads/" + world_name + ".json")
        if label.startswith("math-sin-") or label == "math-asin-bounded-edges":
            receipt_dir = gate / "reports" / world_name
            for receipt in sorted(receipt_dir.glob("slice-*.json")):
                receipt_copy = copy(receipt, "receipts/" + world_name + "/" + receipt.name)
                row = json.loads(receipt.read_text())
                checkpoint = world / "checkpoints" / (row["checkpointSHA256"] + ".bin")
                assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == row["checkpointSHA256"]
                copy(checkpoint, "checkpoints/" + world_name + "/" + receipt.name[:-5] + "-" + row["checkpointSHA256"] + ".bin")

world_name = "world-array-savings-boundary-q4096"
world = gate / world_name
head = json.loads((world / "durable-head.json").read_text())
copy(world / "checkpoints" / (head["checkpointSHA256"] + ".bin"), "checkpoints/" + world_name + ".bin")
copy(world / "durable-head.json", "heads/" + world_name + ".json")

# The successful q1 parent checkpoint contains the real 65536-element sparse
# primitive arrays. Archive it with the adjacent committed continuation proof.
q1 = summary["results"]["q1-sparse-resume-from-successful-large-array-head"]
parent_world = gate / "world-sparse-array-stress-q1"
parent_cp = parent_world / "checkpoints" / (q1["parentCheckpointSHA256"] + ".bin")
assert hashlib.sha256(parent_cp.read_bytes()).hexdigest() == q1["parentCheckpointSHA256"]
copy(parent_cp, "checkpoints/sparse-array-q1-parent.bin")
for epoch in (q1["parentEpoch"], q1["childEpoch"]):
    copy(gate / "reports/world-sparse-array-stress-q1" / ("slice-%020d.json" % epoch),
         "receipts/sparse-array-q1-slice-%d.json" % epoch)

# Exact refusal receipts cover out-of-domain/nonfinite inputs at q1/q7/direct
# and carry root plus byte-exact durable-Head atomicity witnesses.
refusal_labels = (
    "math-asin-above-bound-refusal", "math-asin-below-negative-bound-refusal",
    "math-asin-nan-refusal", "math-asin-positive-infinity-refusal", "math-asin-negative-infinity-refusal",
    "math-sin-above-bound-refusal", "math-sin-below-negative-bound-refusal",
    "math-sin-nan-refusal", "math-sin-positive-infinity-refusal",
    "math-sin-negative-infinity-refusal",
)
for label in refusal_labels:
    for quantum in (1, 7, 4096):
        world_name = "world-" + label + "-q" + str(quantum)
        report_dir = gate / "reports" / world_name
        receipt = "start-refusal.json" if (report_dir / "start-refusal.json").exists() else "resume-refusal.json"
        copy(report_dir / receipt, "refusals/" + label + "-q" + str(quantum) + ".json")
        copy(gate / world_name / "durable-head.json", "heads/" + label + "-q" + str(quantum) + ".json")
        head = json.loads((gate / world_name / "durable-head.json").read_text())
        if head.get("checkpointSHA256"):
            cp = gate / world_name / "checkpoints" / (head["checkpointSHA256"] + ".bin")
            copy(cp, "checkpoints/" + label + "-q" + str(quantum) + ".bin")

# Keep the canonical malformed sparse-wire refusals used by the retained codec gate.
for label in summary["results"]["sparse-malformed-refusals"]:
    copy(gate / "reports/world-sparse-array-stress-q1" / (label + ".json"),
         "refusals/" + label + ".json")

proof = {
    "profile": summary["profile"],
    "wholeGateSeconds": summary["wholeGateSeconds"],
    "limitSeconds": 1200,
    "engineBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": pins["runtimeCap"],
    "bootstrapCount": pins["bootstrapCount"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "globalNativeBindings": pins["globalNativeBindings"],
    "stringLocalBinding": pins["stringLocalBinding"],
    "rawLimits": pins["rawLimits"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "mathImage": pins["math"],
    "asinEdgesQ1Q7Direct": summary["results"]["math-asin-bounded-edges"],
    "retainedSinEdgesQ1Q7Direct": summary["results"]["math-sin-bounded-edges"],
    "retainedSinGridQ1Q7Direct": summary["results"]["math-sin-bounded-grid"],
    "testOnlyQ120Model": json.loads((gate / "q120-test-only-model.json").read_text()),
    "retainedSqrtQ1Q7Direct": summary["results"]["math-sqrt-binary64"],
    "sparseQ1Q7Direct": summary["results"]["sparse-array-stress"],
    "sparseQ1ParentChild": q1,
    "unsupportedInputs": {label: summary["results"][label] for label in refusal_labels},
    "canonicalReceipts": summary["canonicalReceipts"]["verifiedReceipts"],
    "sourceRootPinCaveat": {
        "historicalP1Pin": json.loads((stage / "root-commitment.json").read_text())["priorHistoricalP1PinRoot"],
        "sourceDerivedP2Root": json.loads((stage / "root-commitment.json").read_text())["bootstrapRoot"],
        "note": "The inherited historical P1 7e17... root is stale. The prior source-derived P2 root is independently recomputed; this stage changes only exact Math image89 and recomputes all 97 ordered leaves.",
    },
    "scope": "Generated fixtures only. Exact Math image89 adds native asin(D)D and only global binding20 is appended; prior binding19 bounded sine, sqrt18, other96 images, String-local12, raw71/471911 and sparse wire remain. Binding20 uses finite |x|<=1, signed-zero identity, a bounded Q120 n=128 series plus exact integer sqrt transform, nearest-even output, and atomic refusals for nonfinite/out-of-domain bits. q1/q7/direct/reopen EVM receipts check selected k/256, signed zero, tiny/half/endpoint edges against generated Java8 <=1 ULP and exact float-cast witnesses. The independent 17,066-row Q120 model is test-only and observes <=1 ULP/0 float mismatches; no original program inputs were used. Retained sine, sqrt, float-packed/sparse q1/reopen/malformed, raw71/471911 and older profiles are separately gated. No original JAR/classes/resources/world/EULA data opened; parent must independently rebuild/gate and perform authorized unchanged-original replay.",
}
(dest / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")

# Authenticate all archived content, then include the manifest in SHA256SUMS.
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
files = {p.relative_to(dest).as_posix(): sha(p) for p in sorted(dest.rglob("*")) if p.is_file()}
manifest = {
    "profile": summary["profile"], "generatedOnly": True,
    "baselineEngineSourceSHA256": json.loads((stage / "results/source-invariants.json").read_text())["baselineEngineSourceSHA256"],
    "candidateEngineSourceSHA256": json.loads((stage / "results/source-invariants.json").read_text())["candidateEngineSourceSHA256"],
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "gateSeconds": summary["wholeGateSeconds"], "limitSeconds": 1200,
    "files": files,
}
(dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted(p for p in dest.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
(dest / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.relative_to(dest).as_posix()}\n" for p in paths))

# The requested top-level results/SHA256SUMS covers the entire durable evidence
# subtree (including the nested archive checksum list), but does not self-hash.
results_root = stage / "results"
result_paths = sorted(p for p in results_root.rglob("*") if p.is_file() and p != results_root / "SHA256SUMS")
(results_root / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.relative_to(results_root).as_posix()}\n" for p in result_paths))
print(json.dumps({"archive": str(dest), "files": len(paths),
                  "gateSeconds": summary["wholeGateSeconds"],
                  "canonicalReceipts": proof["canonicalReceipts"],
                  "sha256sums": str(dest / "SHA256SUMS"),
                  "topLevelSHA256SUMS": str(results_root / "SHA256SUMS")}, indent=2))
