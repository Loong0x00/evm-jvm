#!/usr/bin/env python3
"""Create one clean, generated-only parent replay record for this stage.

This wrapper deliberately rebuilds the EVM artifacts, regenerates trusted fixture
sources, and reruns the complete gate in fresh ignored build directories.  It
copies only compact, reproducible result records into the tracked evidence tree.
It never accepts an existing build directory or any original Minecraft input.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
if len(sys.argv) != 2:
    raise SystemExit("usage: parent_replay.py REPLAY_ID")
replay_id = sys.argv[1]
assert replay_id and all(c.isalnum() or c in "-_" for c in replay_id)
results = stage / "results"
assert results.is_dir() and not any(results.iterdir()), "refusing to overwrite replay evidence"

prefix = "java-diff-mc-string-builder-append-int-"
build = root / "build" / (prefix + "build-parent-replay-" + replay_id)
fixtures = root / "build" / (prefix + "fixtures-parent-replay-" + replay_id)
gate = root / "build" / (prefix + "gate-parent-replay-" + replay_id)
assert not any(path.exists() for path in (build, fixtures, gate)), "fresh ignored build paths required"

started = time.monotonic()
commands = []
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
def run(label, command):
    before = time.monotonic()
    subprocess.run([str(x) for x in command], cwd=root, env=env, check=True)
    commands.append({"label": label, "command": [str(x) for x in command],
                     "elapsedSeconds": time.monotonic() - before})

run("build", [sys.executable, here / "build.py", build])
run("fixtures", [sys.executable, here / "generate_fixtures.py", fixtures])
run("gate", [sys.executable, here / "gate.py", build, fixtures, gate])

pins = json.loads((build / "pins.json").read_text())
gate_summary = json.loads((gate / "summary.json").read_text())
fixture_summary = json.loads((fixtures / "summary.json").read_text())
assert gate_summary["generatedOnly"] is True
assert gate_summary["wholeGateSeconds"] <= 1200
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 94 and pins["rawLimits"] == [50, 324338]
assert gate_summary["canonicalReceipts"]["verifiedReceipts"] > 0

for source, target in (
    (build / "pins.json", results / "build-pins.json"),
    (build / "source-verification-final.log", results / "source-verification.json"),
    (fixtures / "summary.json", results / "fixture-summary.json"),
    (gate / "summary.json", results / "gate-summary.json"),
    (gate / "logs/canonical-receipts.log", results / "canonical-receipts.json"),
    (stage / "root-commitment.json", results / "root-commitment.json"),
):
    shutil.copy2(source, target)

focused = {key: gate_summary["results"][key] for key in (
    "stringbuilder-append-int-min", "stringbuilder-append-int-negative-one",
    "stringbuilder-append-int-zero", "stringbuilder-append-int-positive",
    "stringbuilder-append-int-max", "stringbuilder-append-int-existing-prefix",
    "stringbuilder-append-long-omitted", "stringbuilder-append-object-omitted",
)}
summary = {
    "profile": gate_summary["profile"],
    "generatedOnly": True,
    "parentReplay": True,
    "wholeGateSeconds": gate_summary["wholeGateSeconds"],
    "wholeGateLimitSeconds": 1200,
    "commandCount": len(gate_summary["commands"]),
    "canonicalReceiptCount": gate_summary["canonicalReceipts"]["verifiedReceipts"],
    "runtimeBytes": pins["engine"]["bytes"],
    "runtimeCap": pins["runtimeCap"],
    "bootstrapCount": pins["bootstrapCount"],
    "diagnosticClassBound": pins["diagnosticClassBound"],
    "rawLimits": pins["rawLimits"],
    "bootstrapRoot": json.loads((stage / "root-commitment.json").read_text())["bootstrapRoot"],
    "stringBuilderAppendInt": focused,
    "limitations": gate_summary["limitations"],
}
(results / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {
    "replayID": replay_id,
    "sourceRevision": revision,
    "generatedOnly": True,
    "freshBuildDirectories": [str(x.relative_to(root)) for x in (build, fixtures, gate)],
    "steps": commands,
    "elapsedSeconds": time.monotonic() - started,
    "resultSHA256": {path.name: digest(path) for path in sorted(results.iterdir()) if path.is_file()},
    "note": "The ignored build directories are disposable. Tracked results retain compact replay records; no original artifact, JAR, class, resource, world, provider, factory, or Done input was used.",
}
(results / "parent-replay.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"results": str(results), "summary": summary, "parentReplay": manifest}, indent=2))
