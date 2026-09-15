#!/usr/bin/env python3
"""Generated-only class-count30 EVM gate; no original JAR, class, or world input."""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build = Path(sys.argv[1]).resolve()
fixtures = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert out.name.startswith("java-diff-mc-classcount30-") and not out.exists()
assert (fixtures / "summary.json").is_file()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
out.mkdir()
logs = out / "logs"
logs.mkdir()
start = time.monotonic()
commands = []

def names(label):
    return ",".join(json.loads((fixtures / (label + ".json")).read_text())["entries"])

def run(label, args, bindings=None, expect=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    (out / "tmp").mkdir(exist_ok=True)
    if bindings:
        env["MC_ENTRY_BINDINGS"] = names(bindings)
    log = logs / (label + ".log")
    begun = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": process.returncode, "elapsedSeconds": time.monotonic() - begun}
    commands.append(row)
    (logs / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert process.returncode == expect, (label, process.returncode, log)

def report(world):
    return world.parent / "reports" / world.name

def failure(world, name):
    return json.loads((report(world) / name).read_text())

def words(value):
    return list(map(str, value["uint256Words"]))

spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)

def inspect(world, count, quantum):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == count and head["totalClassBytes"] <= 262144
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    active = {entry["classIndex"] for entry in decoded["initialization"] if entry["state"] == 2}
    assert set(range(count)).issubset(active), (count, quantum, active)
    return {
        "epoch": head["epoch"], "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
        "machineRoot": head["machineRoot"], "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
        "totalClassBytes": head["totalClassBytes"], "counters": head["counters"],
    }

driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
pins = json.loads((stage / "pins.json").read_text())
rows = {}

# Both below-cap and exact-cap packages run independently at q1/q7/direct,
# finish through normal checkpoint resumes, and reopen from durable state.
for count in (29, 30):
    baseline = None
    for tag, quantum in (("q1", 1), ("q7", 7), ("direct", 4096)):
        world = out / ("world-%d-%s" % (count, tag))
        run("%d-%s-start" % (count, tag), [driver, "setup-chain", world, coordinator, engine, fixtures / (str(count) + ".zip"), str(quantum)], str(count))
        run("%d-%s-finish" % (count, tag), [driver, "finish", world, coordinator, engine, fixtures / (str(count) + ".zip"), str(quantum)], str(count))
        run("%d-%s-reopen" % (count, tag), [driver, "verify", world, coordinator, engine, fixtures / (str(count) + ".zip"), str(quantum)], str(count))
        result = inspect(world, count, quantum)
        rows["%d/%s" % (count, tag)] = result
        if baseline is None:
            baseline = result
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert result[key] == baseline[key], (count, tag, key)

world = out / "world-30-reordered"
run("30-reordered-start", [driver, "setup-chain", world, coordinator, engine, fixtures / "30.zip", "4096"], "30-reordered")
run("30-reordered-finish", [driver, "finish", world, coordinator, engine, fixtures / "30.zip", "4096"], "30-reordered")
run("30-reordered-reopen", [driver, "verify", world, coordinator, engine, fixtures / "30.zip", "4096"], "30-reordered")
reordered = inspect(world, 30, 4096)
reordered_head = json.loads((world / "durable-head.json").read_text())
direct_head = json.loads((out / "world-30-direct/durable-head.json").read_text())
assert reordered_head["packageRoot"] != direct_head["packageRoot"]
reordered["packageRoot"] = reordered_head["packageRoot"]
rows["30/reordered"] = reordered

# The product driver's explicit guard refuses 31 before it creates a durable world.
world = out / "world-31-driver"
run("31-driver-pre-mutation-refusal", [driver, "setup-chain", world, coordinator, engine, fixtures / "31.zip", "4096"], "31", expect=2)
assert not world.exists()
rows["31/driver"] = {"layer": "driver", "worldExists": False}

# A disposable generated-only transport guard exposes the product coordinator.
def test_driver(label, coordinator_keccak):
    source = (here / "Go.txt").read_text()
    assert source.count("> 30") == 2
    source = source.replace("> 30", "> 31")
    old = "0x" + pins["coordinator"]["runtimeKeccak256"]
    source = source.replace(old, "0x" + coordinator_keccak)
    path = out / (label + ".go")
    path.write_text(source)
    executable = out / label
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    for suffix, command in (("gofmt", ["gofmt", "-w", path]), ("build", ["go", "build", "-trimpath", "-o", executable, path])):
        with (logs / (label + "-" + suffix + ".log")).open("w") as stream:
            subprocess.run(list(map(str, command)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return executable

coordinator_driver = test_driver("coordinator-31-driver", pins["coordinator"]["runtimeKeccak256"])
world = out / "world-31-coordinator"
run("31-coordinator-atomic-refusal", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "31.zip", "4096"], "31")
rejection = failure(world, "boundary-refusal.json")
assert rejection["selector"] == "0xab23ed08" and words(rejection) == ["2"] and rejection["rootUnchanged"]
rows["31/coordinator"] = rejection

# Only a mechanically widened disposable coordinator exposes the product engine cap.
probe = out / "engine-31-coordinator"
shutil.copytree(stage / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[30]") == 4 and text.count("n > 30") == 1
probe_source.write_text(text.replace("[30]", "[31]").replace("n > 30", "n > 31"))
env = dict(os.environ, NODE_PATH=str(node_modules), TMPDIR=str(out / "tmp"), PYTHONDONTWRITEBYTECODE="1")
with (logs / "31-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", str(probe / "build.js")], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_keccak = json.loads(probe_artifact.read_text())["codeHashes"]["runtimeKeccak256"]
engine_driver = test_driver("engine-31-driver", probe_keccak)
world = out / "world-31-engine"
run("31-engine-atomic-refusal", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "31.zip", "4096"], "31")
rejection = failure(world, "start-refusal.json")
assert rejection["selector"] == "0x427cfac5" and words(rejection) == ["1", "31"] and rejection["rootUnchanged"]
rows["31/engine"] = rejection

# Exact aggregate bytes reach the real parser; +1 is independently rejected by
# the coordinator aggregate guard before engine execution.
world = out / "world-30-262144"
run("262144-start", [driver, "setup-chain", world, coordinator, engine, fixtures / "30-262144.zip", "4096"], "30-262144")
rejection = failure(world, "start-refusal.json")
assert rejection["selector"] == "0x71540d20" and words(rejection) == ["1", "0"] and rejection["rootUnchanged"]
rows["30/262144-infeasible"] = rejection
world = out / "world-30-262145"
run("262145-constructor-refusal", [driver, "boundary-create", world, coordinator, engine, fixtures / "30-262145.zip", "4096"], "30-262145")
rejection = failure(world, "boundary-refusal.json")
assert rejection["selector"] == "0xab23ed08" and words(rejection) == ["12"] and rejection["rootUnchanged"]
rows["30/262145"] = rejection

# Re-encode every successful public receipt after the fresh/reopened chains.
canonical_labels = ["world-%d-%s" % (count, tag) for count in (29, 30) for tag in ("q1", "q7", "direct")] + ["world-30-reordered"]
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels])
canonical = json.loads((logs / "canonical-receipts.log").read_text())
(out / "canonical-receipts.json").write_text(json.dumps(canonical, indent=2) + "\n")
summary = {"profile": "MC-CLASSCOUNT30-C30", "generatedOnly": True, "results": rows, "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": time.monotonic() - start}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
