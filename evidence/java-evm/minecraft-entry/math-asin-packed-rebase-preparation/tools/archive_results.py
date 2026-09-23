#!/usr/bin/env python3
"""Archive a successful generated-only P9 rebase gate without world stores."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 4
build, fixtures, gate = (Path(v).resolve() for v in sys.argv[1:])
for path, prefix in ((build, "java-diff-mc-math-asin-p9-build-"),
                     (fixtures, "java-diff-mc-math-asin-p9-fixtures-"),
                     (gate, "java-diff-mc-math-asin-p9-gate-")):
    assert path.parent == root / "build" and path.name.startswith(prefix)
summary = json.loads((gate / "summary.json").read_text())
pins = json.loads((build / "pins.json").read_text())
fixture_summary = json.loads((fixtures / "summary.json").read_text())
source = json.loads((stage / "results/source-invariants.json").read_text())
assert summary["profile"] == "MC-RANDOM-CLASS-P9-MATH-ASIN-PACKED-REBASE"
assert summary["generatedOnly"] is True and summary["wholeGateSeconds"] <= 1200
assert pins["engine"]["bytes"] == summary["engineBytes"] <= 393216
assert pins["bootstrapRoot"] == summary["bootstrapRoot"] == source["actualSolidityP9BootstrapRoot"]
assert source["changedBootstrapIndices"] == [89] and source["normalizedByteExactToP6"]
assert summary["canonicalReceipts"]["verifiedReceipts"] == 6112
for key in ("math-asin-bounded-edges", "packed-array-oracle", "sparse-array-stress",
            "q1-packed-resume-from-successful-array-head",
            "q1-sparse-resume-from-successful-large-array-head", "packed-malformed-refusals",
            "sparse-malformed-refusals", "math-sqrt-binary64", "math-sin-bounded-edges"):
    assert key in summary["results"], key
assert fixture_summary["generatedOnly"] is True

out = stage / "results/generated-gate-p9"
assert not out.exists(), f"refuse to overwrite durable evidence: {out}"
out.mkdir(parents=True)

def copy(src, rel):
    src = Path(src); dst = out / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst

def json_copy(src, rel):
    return copy(src, rel)

for src, rel in (
    (build / "pins.json", "build-pins.json"),
    (gate / "summary.json", "gate-summary.json"),
    (gate / "q120-test-only-model.json", "q120-test-only-model.json"),
    (gate / "logs/canonical-receipts.json", "canonical-receipts.json"),
    (gate / "logs/canonical-receipts.log", "canonical-receipts.log"),
    (stage / "results/source-invariants.json", "source-invariants.json"),
    (stage / "root-commitment.json", "root-commitment.json"),
    (stage / "baseline-pins.json", "baseline-pins.json"),
    (stage / "bootstrap/java/lang/Math.java", "bootstrap/Math.java"),
    (stage / "bootstrap/java/lang/Math.class.hex", "bootstrap/Math.class.hex"),
    (stage / "bootstrap/java/lang/Math.sha256", "bootstrap/Math.sha256"),
    (build / "engine/MCEntryInterpreter.runtime.hex", "artifacts/engine-runtime.hex"),
    (build / "coordinator/MCEntryCoordinator.runtime.hex", "artifacts/coordinator-runtime.hex"),
): copy(src, rel)

# Preserve every Java-8 generated fixture's exact ZIP/class commitments.
for label in sorted(fixture_summary["fixtures"]):
    copy(fixtures / (label + ".zip"), "fixtures/" + label + ".zip")
    copy(fixtures / (label + ".json"), "fixtures/" + label + ".json")
copy(fixtures / "summary.json", "fixtures/summary.json")

# Retain canonical reports and gate logs byte-for-byte. No transient world state,
# database snapshots, generated executables, original inputs, or P8 checkpoints.
def add_tree_tar(source, arcname, target):
    with tarfile.open(target, "w:gz", compresslevel=6) as archive:
        for p in sorted(source.rglob("*")):
            if p.is_file():
                archive.add(p, arcname=(Path(arcname) / p.relative_to(source)).as_posix(), recursive=False)
add_tree_tar(gate / "reports", "reports", out / "reports.tar.gz")
add_tree_tar(gate / "logs", "logs", out / "logs.tar.gz")

# Pin terminal heads/checkpoints for primary behavior and packed/sparse codec
# controls, plus the exact successful parent/child resume checkpoints.
def save_checkpoint(world_name, sha, label):
    world = gate / world_name
    blob = world / "checkpoints" / (sha + ".bin")
    raw = blob.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha
    copy(blob, "checkpoints/" + label + ".bin")
    return len(raw)

def save_world(world_name, label):
    world = gate / world_name
    head = json.loads((world / "durable-head.json").read_text())
    copy(world / "durable-head.json", "heads/" + label + ".json")
    length = save_checkpoint(world_name, head["checkpointSHA256"], label)
    assert 280 < length <= 1048576
    return head

for test in ("math-asin-bounded-edges", "packed-array-oracle", "sparse-array-stress"):
    for q in (1, 7, 4096):
        save_world("world-" + test + "-q" + str(q), test + "-q" + str(q))
save_world("world-array-savings-boundary-q4096", "array-savings-boundary-q4096")

for result_key, world_name, parent_name in (
    ("q1-packed-resume-from-successful-array-head", "world-packed-array-oracle-q1", "packed-array-q1-parent"),
    ("q1-sparse-resume-from-successful-large-array-head", "world-sparse-array-stress-q1", "sparse-array-q1-parent"),
):
    row = summary["results"][result_key]
    parent_len = save_checkpoint(world_name, row["parentCheckpointSHA256"], parent_name)
    child_name = parent_name.replace("-parent", "-child")
    child_len = save_checkpoint(world_name, row["childCheckpointSHA256"], child_name)
    assert parent_len == row["parentCheckpointBytes"]
    child_receipt = json.loads((gate / "reports" / world_name / ("slice-%020d.json" % row["childEpoch"])).read_text())
    assert child_receipt["checkpointSHA256"] == row["childCheckpointSHA256"]
    copy(gate / "reports" / world_name / ("slice-%020d.json" % row["parentEpoch"]),
         "continuations/" + child_name + "-parent-receipt.json")
    copy(gate / "reports" / world_name / ("slice-%020d.json" % row["childEpoch"]),
         "continuations/" + child_name + "-child-receipt.json")
    assert child_len == child_receipt["checkpointBytes"]

# Archive all report receipts compressed for complete receipt-chain inspection.
proof = {
    "status": "WORKER_GENERATED_GATE_PASS_PENDING_INDEPENDENT_PARENT_REPLAY",
    "notAcceptance": True,
    "profile": summary["profile"],
    "generatedOnly": True,
    "wholeGateSeconds": summary["wholeGateSeconds"],
    "gateLimitSeconds": 1200,
    "engineBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": pins["runtimeCap"],
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "coordinatorRuntimeSHA256": pins["coordinator"]["runtimeSHA256"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "bootstrapCount": pins["bootstrapCount"],
    "changedBootstrapIndices": source["changedBootstrapIndices"],
    "changedOtherImages": source["changedOther96Images"],
    "globalNativeBindings": pins["globalNativeBindings"],
    "retainedP6Bindings": source["retainedP6Bindings"],
    "mathImage": pins["math"],
    "asinQ1Q7Direct": summary["results"]["math-asin-bounded-edges"],
    "packedFloatQ1Q7Direct": summary["results"]["packed-array-oracle"],
    "packedQ1ParentChild": summary["results"]["q1-packed-resume-from-successful-array-head"],
    "packedMalformedRefusals": summary["results"]["packed-malformed-refusals"],
    "sparseQ1Q7Direct": summary["results"]["sparse-array-stress"],
    "sparseQ1ParentChild": summary["results"]["q1-sparse-resume-from-successful-large-array-head"],
    "sparseMalformedRefusals": summary["results"]["sparse-malformed-refusals"],
    "retainedControls": {k: summary["results"][k] for k in
        ("math-sqrt-binary64", "math-sin-bounded-edges", "math-sin-bounded-grid", "count-71", "byte-471911", "byte-471912")},
    "q120TestOnlyModel": summary["q120TestOnlyModel"],
    "canonicalReceipts": summary["canonicalReceipts"]["verifiedReceipts"],
    "limitations": summary["limitations"],
    "independentReplay": "REQUIRED; not performed by this worker",
    "originalInputs": "No original server/JAR/class/resource/world/EULA/network inputs opened or executed; no P8 checkpoint continued.",
}
(out / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")

# Hash every durable artifact. SHA256SUMS deliberately excludes itself.
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("manifest.json", "SHA256SUMS"))
manifest = {
    "archiveVersion": 1,
    "status": proof["status"],
    "generatedOnly": True,
    "profile": summary["profile"],
    "gateSeconds": summary["wholeGateSeconds"],
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "canonicalReceipts": proof["canonicalReceipts"],
    "files": {p.relative_to(out).as_posix(): sha_file(p) for p in files},
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
all_files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
(out / "SHA256SUMS").write_text("".join(f"{sha_file(p)}  {p.relative_to(out).as_posix()}\n" for p in all_files))
print(json.dumps({"archive": str(out), "files": len(all_files), "gateSeconds": summary["wholeGateSeconds"],
                  "canonicalReceipts": proof["canonicalReceipts"], "engineBytes": proof["engineBytes"],
                  "reportBytes": (out / "reports.tar.gz").stat().st_size}, indent=2))
