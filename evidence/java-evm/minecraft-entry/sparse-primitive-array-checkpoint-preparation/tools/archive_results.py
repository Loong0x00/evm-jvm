#!/usr/bin/env python3
"""Archive a successful disposable build/gate without overwriting evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build, fixtures, gate = [Path(value).resolve() for value in sys.argv[1:4]]
assert build.parent == fixtures.parent == gate.parent == root / "build"
dest = stage / "results/generated-gate-v1"
assert not dest.exists(), f"refuse to overwrite durable evidence: {dest}"
assert (gate / "summary.json").is_file()
dest.mkdir(parents=True)

def copy(source, relative):
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target

copy(build / "pins.json", "build-pins.json")
copy(stage / "baseline-pins.json", "baseline-pins.json")
copy(gate / "summary.json", "gate-summary.json")
copy(gate / "logs/canonical-receipts.log", "canonical-receipts.json")
copy(stage / "results/source-invariants.json", "source-invariants.json")
copy(build / "engine/MCEntryInterpreter.runtime.hex", "artifacts/engine-runtime.hex")
copy(build / "coordinator/MCEntryCoordinator.runtime.hex", "artifacts/coordinator-runtime.hex")
for label in ("sparse-array-stress", "array-savings-boundary", "count-71", "count-72",
              "count-71-471911", "count-71-471912"):
    copy(fixtures / (label + ".zip"), "fixtures/" + label + ".zip")
    copy(fixtures / (label + ".json"), "fixtures/" + label + ".json")

summary = json.loads((gate / "summary.json").read_text())
q1 = summary["results"]["q1-sparse-resume-from-successful-large-array-head"]
proof = {"profile": summary["profile"], "wholeGateSeconds": summary["wholeGateSeconds"],
         "externalLocalGas": summary["externalLocalGas"], "sparseWire": summary["sparseWire"],
         "stressQ1Q7Direct": summary["results"]["sparse-array-stress"],
         "strictSavingBoundaryDirect": summary["results"]["array-savings-boundary"],
         "q1CommittedArrayParentChild": q1, "malformedRefusals": {
             key: {k: value[k] for k in ("selector", "error", "code", "expectedCode", "gas",
                                           "rootUnchanged", "headUnchanged", "logsUnchanged",
                                           "checkpointBytes", "checkpointSHA256")}
             for key, value in summary["results"]["sparse-malformed-refusals"].items()},
         "limitations": "Generated-only candidate; parent independent review, original replay, and acceptance are outstanding."}
(dest / "checkpoint-proof.json").write_text(json.dumps(proof, indent=2) + "\n")

# Preserve only successful terminal checkpoints plus the successful q1 parent
# that already contains a genuine 65536-element guest float array.
for name in ("sparse-array-stress-q1", "sparse-array-stress-q7", "sparse-array-stress-q4096",
             "array-savings-boundary-q4096"):
    world = gate / ("world-" + name)
    head = json.loads((world / "durable-head.json").read_text())
    cp = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    copy(cp, "checkpoints/" + name + ".bin")
    if name == "sparse-array-stress-q1":
        copy(world / "durable-head.json", "checkpoints/sparse-array-stress-q1-head.json")
parent_world = gate / "world-sparse-array-stress-q1"
parent_cp = parent_world / "checkpoints" / (q1["parentCheckpointSHA256"] + ".bin")
copy(parent_cp, "checkpoints/sparse-array-stress-q1-parent-array.bin")
for epoch in (q1["parentEpoch"], q1["childEpoch"]):
    copy(parent_world.parent / "reports" / parent_world.name / ("slice-%020d.json" % epoch),
         "receipts/sparse-array-stress-q1-slice-%d.json" % epoch)
for label in summary["results"]["sparse-malformed-refusals"]:
    copy(gate / "reports/world-sparse-array-stress-q1" / (label + ".json"),
         "refusals/" + label + ".json")

# Build a complete content manifest, then a conventional SHA256SUMS that also
# authenticates the manifest. Neither file hashes itself.
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
files = {p.relative_to(dest).as_posix(): sha(p) for p in sorted(dest.rglob("*")) if p.is_file()}
manifest = {"profile": summary["profile"], "generatedOnly": True,
            "baselineCommit": "511c20c4b", "baselineSourceSHA256": json.loads((stage / "baseline-pins.json").read_text())["engine"]["runtimeSHA256"],
            "candidateSourceSHA256": json.loads((stage / "results/source-invariants.json").read_text())["candidateSourceSHA256"],
            "gateSeconds": summary["wholeGateSeconds"], "limitSeconds": 1200,
            "files": files}
(dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted(p for p in dest.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
(dest / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.relative_to(dest).as_posix()}\n" for p in paths))
print(json.dumps({"archive": str(dest), "files": len(paths), "gateSeconds": summary["wholeGateSeconds"],
                  "sha256sums": str(dest / "SHA256SUMS")}, indent=2))
