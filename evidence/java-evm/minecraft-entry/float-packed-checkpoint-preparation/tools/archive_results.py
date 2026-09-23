#!/usr/bin/env python3
"""Archive generated-only float-packed checkpoint evidence, refusing overwrite."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import sys
import tarfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
assert len(sys.argv) == 4
build, fixtures, gate = [Path(value).resolve() for value in sys.argv[1:4]]
assert build.parent == fixtures.parent == gate.parent == root / "build"
assert build.name.startswith("java-diff-mc-float-packed-build-")
assert fixtures.name.startswith("java-diff-mc-float-packed-fixtures-")
assert gate.name.startswith("java-diff-mc-float-packed-gate-")
dest = stage / "results/generated-gate-v5"
assert not dest.exists(), f"refuse to overwrite durable evidence: {dest}"
summary = json.loads((gate / "summary.json").read_text())
pins = json.loads((build / "pins.json").read_text())
fixture_summary = json.loads((fixtures / "summary.json").read_text())
assert summary["generatedOnly"] is True
assert summary["profile"] == "MC-RANDOM-CLASS-P5-FLOAT-PACKED-CHECKPOINT"
assert summary["wholeGateSeconds"] <= 1200
assert pins["bootstrapRoot"] == summary["bootstrapRoot"]
assert pins["engine"]["bytes"] == summary["engineBytes"] <= pins["runtimeCap"] == 393216
assert pins["sourceInvariants"]["result"] == "PASS"
assert len(fixture_summary["fixtures"]["packed-array-oracle"]["hostOutput"]) == 1024
assert summary["results"]["packed-array-oracle"]["q1"]["machineRoot"] == summary["results"]["packed-array-oracle"]["q7"]["machineRoot"] == summary["results"]["packed-array-oracle"]["direct"]["machineRoot"]
assert summary["results"]["packed-array-oracle"]["q1"]["opaquePayloadSHA256"] == summary["results"]["packed-array-oracle"]["q7"]["opaquePayloadSHA256"] == summary["results"]["packed-array-oracle"]["direct"]["opaquePayloadSHA256"]
assert summary["canonicalReceipts"]["verifiedReceipts"] >= 5000

dest.mkdir(parents=True)

def copy(source, relative):
    source = Path(source)
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target

# Pinned source, build inputs and exact compiled artifacts.
for source, relative in (
    (stage / "engine/MCEntryInterpreter.sol", "source/MCEntryInterpreter.sol"),
    (stage / "engine/build.js", "source/engine-build.js"),
    (stage / "coordinator/MCEntryCoordinator.sol", "source/MCEntryCoordinator.sol"),
    (stage / "coordinator/build.js", "source/coordinator-build.js"),
    (stage / "tools/Go.txt", "source/canonical-driver.go.txt"),
    (stage / "baseline-pins.json", "source/baseline-pins.json"),
    (stage / "results/source-invariants.json", "source/source-invariants.json"),
    (stage.parent / "parent-56f2377a5/artifacts/engine/MCEntryInterpreter.sol", "baseline/MCEntryInterpreter.sol"),
    (stage.parent / "parent-56f2377a5/artifacts/coordinator/MCEntryCoordinator.sol", "baseline/MCEntryCoordinator.sol"),
    (stage.parent / "parent-56f2377a5/canonical-driver.go.txt", "baseline/canonical-driver.go.txt"),
    (stage / "tools/verify_source.py", "tools/verify_source.py"),
    (stage / "tools/checkpoint_diagnostic.py", "tools/checkpoint_diagnostic.py"),
    (stage / "tools/checkpoint_frames.py", "tools/checkpoint_frames.py"),
    (stage / "tools/generate_fixtures.py", "tools/generate_fixtures.py"),
    (stage / "tools/gate.py", "tools/gate.py"),
    (stage / "tools/build.py", "tools/build.py"),
    (stage / "tools/verify_q120.py", "tools/verify_q120.py"),
    (stage / "tools/verify_receipts.js", "tools/verify_receipts.js"),
    (stage / "tools/verify_results.py", "tools/verify_results.py"),
    (build / "pins.json", "build/pins.json"),
    (build / "engine/MCEntryInterpreter.json", "artifacts/MCEntryInterpreter.json"),
    (build / "engine/MCEntryInterpreter.abi.json", "artifacts/MCEntryInterpreter.abi.json"),
    (build / "engine/MCEntryInterpreter.runtime.hex", "artifacts/MCEntryInterpreter.runtime.hex"),
    (build / "engine/MCEntryInterpreter.init.hex", "artifacts/MCEntryInterpreter.init.hex"),
    (build / "coordinator/MCEntryCoordinator.json", "artifacts/MCEntryCoordinator.json"),
    (build / "coordinator/MCEntryCoordinator.abi.json", "artifacts/MCEntryCoordinator.abi.json"),
    (build / "coordinator/MCEntryCoordinator.runtime.hex", "artifacts/MCEntryCoordinator.runtime.hex"),
    (build / "coordinator/MCEntryCoordinator.init.hex", "artifacts/MCEntryCoordinator.init.hex"),
    (build / "main.go", "artifacts/driver-main.go"),
    (gate / "summary.json", "gate-summary.json"),
    (gate / "q120-test-only-model.json", "q120-test-only-model.json"),
    (gate / "logs/canonical-receipts.json", "canonical-receipts.json"),
    (gate / "logs/canonical-receipts.log", "canonical-receipts.log"),
    (fixtures / "summary.json", "fixtures/summary.json"),
):
    copy(source, relative)

# Preserve the Java-8-generated guest bundles and their exact raw-class oracles.
for label in fixture_summary["fixtures"]:
    copy(fixtures / (label + ".zip"), "fixtures/" + label + ".zip")
    copy(fixtures / (label + ".json"), "fixtures/" + label + ".json")

# Reports contain the complete canonical receipt set, malformed input hashes,
# atomic Head/root witnesses, process receipts, and replay command details.
# Normalize tar metadata and gzip time so this evidence archive is reproducible.
reports_tar = dest / "canonical-reports.tar.gz"
with reports_tar.open("wb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for path in sorted((gate / "reports").rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(gate).as_posix()
                info = archive.gettarinfo(str(path), arcname=relative)
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.mode = 0o644
                with path.open("rb") as stream:
                    archive.addfile(info, stream)

# Retain terminal checkpoint/head pairs for packed q1/q7/direct, the large
# sparse compatibility control, and the measured strict-savings boundary.
def copy_head_checkpoint(world_name, label):
    world = gate / world_name
    head = json.loads((world / "durable-head.json").read_text())
    checkpoint = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    data = checkpoint.read_bytes()
    assert hashlib.sha256(data).hexdigest() == head["checkpointSHA256"]
    copy(checkpoint, "checkpoints/" + label + ".bin")
    copy(world / "durable-head.json", "heads/" + label + ".json")
    return head

for label in ("packed-array-oracle", "sparse-array-stress"):
    for quantum in (1, 7, 4096):
        copy_head_checkpoint("world-" + label + "-q" + str(quantum), label + "-q" + str(quantum))
copy_head_checkpoint("world-array-savings-boundary-q4096", "array-savings-boundary-direct")

# Preserve the successful packed-array parent state plus the exact committed q1
# continuation checkpoint and receipts, proving cross-process decode/re-encode.
resume = summary["results"]["q1-packed-resume-from-successful-array-head"]
packed_q1 = gate / "world-packed-array-oracle-q1"
for role, epoch, digest in (
    ("parent", resume["parentEpoch"], resume["parentCheckpointSHA256"]),
    ("child", resume["childEpoch"], resume["childCheckpointSHA256"]),
):
    cp = packed_q1 / "checkpoints" / (digest + ".bin")
    assert hashlib.sha256(cp.read_bytes()).hexdigest() == digest
    copy(cp, "checkpoints/packed-array-q1-resume-" + role + ".bin")
    receipt = gate / "reports/world-packed-array-oracle-q1" / ("slice-%020d.json" % epoch)
    copy(receipt, "receipts/packed-array-q1-resume-" + role + ".json")
    row = json.loads(receipt.read_text())
    assert row["checkpointSHA256"] == digest

# Convenient byte-for-byte refusal receipts; complete reports (including all
# canonical q1/q7/direct receipts) are retained in canonical-reports.tar.gz.
refusals = list(summary["results"]["packed-malformed-refusals"])
for label in refusals:
    copy(gate / "reports/world-packed-array-oracle-q1" / (label + ".json"),
         "refusals/" + label + ".json")
for label in summary["results"]["sparse-malformed-refusals"]:
    copy(gate / "reports/world-sparse-array-stress-q1" / (label + ".json"),
         "refusals/" + label + ".json")

proof = {
    "profile": summary["profile"],
    "generatedOnly": True,
    "wholeGateSeconds": summary["wholeGateSeconds"],
    "gateTimeoutSeconds": 1200,
    "runtimeBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": pins["runtimeCap"],
    "runtimeSHA256": pins["engine"]["runtimeSHA256"],
    "runtimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "sourceSHA256": pins["sourceInvariants"]["candidateSourceSHA256"],
    "bootstrapCount": pins["bootstrapCount"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "rawLimits": pins["rawLimits"],
    "globalNativeBindings": pins["globalNativeBindings"],
    "stringLocalBinding": pins["stringLocalBinding"],
    "canonicalReceipts": summary["canonicalReceipts"]["verifiedReceipts"],
    "packedFixture": {
        "length": 1024,
        "nonzeroCells": 348,
        "packedPayloadBytes": 4096,
        "sparsePayloadBytes": 4180,
        "strictWireSavingBytes": 84,
        "specialRawCells": {
            "customQuietNaN": "0x7fc12345",
            "negativeZero": "0x80000000",
            "positiveInfinity": "0x7f800000",
            "negativeInfinity": "0xff800000",
            "positiveMinimumSubnormal": "0x00000001",
            "negativeMinimumSubnormal": "0x80000001",
            "maximumFinite": "0x7f7fffff",
        },
        "q1Steps": summary["results"]["packed-array-oracle"]["q1"]["jvmSteps"],
        "q1Q7DirectEquivalent": True,
        "allHostOracleRawBitsEqual": True,
    },
    "packedQ1Resume": resume,
    "malformedPackedRefusals": {
        label: json.loads((gate / "reports/world-packed-array-oracle-q1" / (label + ".json")).read_text())
        for label in refusals
    },
    "scope": "Generated Java-8 fixtures only. MR01 float-only packed wire; restored guest heap remains dense uint64[]. Legacy sparse arrays and controls retained. No original Minecraft JAR/class/resource/world/EULA data was opened; no q1-fatal, startup-ready, EULA, world, or Done claim.",
}
(dest / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")

# The manifest lists every archived item except itself; SHA256SUMS covers the
# manifest too and intentionally does not self-hash.
def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

files = {path.relative_to(dest).as_posix(): sha(path)
         for path in sorted(dest.rglob("*")) if path.is_file()}
manifest = {
    "profile": summary["profile"],
    "generatedOnly": True,
    "baselineCommit": "56f2377a5",
    "baselineSourceSHA256": pins["sourceInvariants"]["baselineSourceSHA256"],
    "candidateSourceSHA256": pins["sourceInvariants"]["candidateSourceSHA256"],
    "runtimeSHA256": pins["engine"]["runtimeSHA256"],
    "runtimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "gateSeconds": summary["wholeGateSeconds"],
    "canonicalReceipts": summary["canonicalReceipts"]["verifiedReceipts"],
    "files": files,
}
(dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted(path for path in dest.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
(dest / "SHA256SUMS").write_text("".join(f"{sha(path)}  {path.relative_to(dest).as_posix()}\n" for path in paths))

# Top-level results checksum covers all durable result files, including this
# archive's checksum list, but excludes itself.
results_root = stage / "results"
result_paths = sorted(path for path in results_root.rglob("*")
                      if path.is_file() and path != results_root / "SHA256SUMS")
(results_root / "SHA256SUMS").write_text("".join(
    f"{sha(path)}  {path.relative_to(results_root).as_posix()}\n" for path in result_paths
))
print(json.dumps({"archive": str(dest), "files": len(paths),
                  "canonicalReceipts": proof["canonicalReceipts"],
                  "gateSeconds": proof["wholeGateSeconds"],
                  "reportsTarBytes": reports_tar.stat().st_size,
                  "sha256sums": str(dest / "SHA256SUMS")}, indent=2))
