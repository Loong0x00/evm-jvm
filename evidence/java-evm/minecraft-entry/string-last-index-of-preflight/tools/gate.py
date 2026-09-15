#!/usr/bin/env python3
"""One generated-only String.lastIndexOf(String) acceptance gate.

It consumes only the build output and fixtures made by sibling stage scripts. It
never names, opens, indexes, or resumes an original Minecraft artifact/world.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build = Path(sys.argv[1]).resolve()
fixtures = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-string-last-index-of-build-")
assert fixtures.name.startswith("java-diff-mc-string-last-index-of-fixtures-")
assert out.name.startswith("java-diff-mc-string-last-index-of-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 85 and pins["rawLimits"] == [30, 262144]
assert pins["diagnosticClassBound"] == 115 and pins["engine"]["bytes"] <= 393216
assert pins["globalNativeBindings"] == 12 and pins["exceptionKinds"] == 14
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic()
commands = []

def fixture(label):
    return json.loads((fixtures / (label + ".json")).read_text())

def bindings(label):
    return ",".join(fixture(label)["entries"])

def report(world):
    return world.parent / "reports" / world.name

def failure(world, name):
    return json.loads((report(world) / name).read_text())

def words(value):
    return list(map(str, value["uint256Words"]))

def run(label, args, fixture_label=None, expect=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    if fixture_label is not None: env["MC_ENTRY_BINDINGS"] = bindings(fixture_label)
    log = out / "logs" / (label + ".log")
    before = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": proc.returncode, "elapsedSeconds": time.monotonic() - before}
    commands.append(row)
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert proc.returncode == expect, (label, proc.returncode, log)

spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_frames.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
rows = {}
canonical_labels = []

def terminal(world, raw_count):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 262144
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + 85
    return head, checkpoint, decoded

def finish(label, fixture_label, quantum, inspect_fn=None):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    head, checkpoint, decoded = terminal(world, fixture(fixture_label)["bindingCount"])
    if inspect_fn is not None: inspect_fn(decoded)
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest()}

def q_equivalent(label, fixture_label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish(label, fixture_label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

# StringBuilder is a real guest class: non-null chained append must preserve
# receiver identity/order, while toString creates independent guest String copies.
def stringbuilder_initialized(decoded):
    raw = fixture("stringbuilder")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
q_equivalent("stringbuilder", "stringbuilder", stringbuilder_initialized)

# The documented null bound is a catchable guest NPE before append allocates.
q_equivalent("stringbuilder-null", "stringbuilder-null")

# Each String.lastIndexOf(String) semantic witness receives independent q1/q7/
# direct/reopen chains. The fixtures cover suffix, middle, prefix, overlap,
# repeats, absence, empty targets/receivers, longer targets, BMP UTF-16 and a
# surrogate-pair UTF-16 sequence without introducing any overload or substring.
for label in (
    "last-index-suffix", "last-index-middle", "last-index-prefix", "last-index-overlap",
    "last-index-repeated", "last-index-absent", "last-index-empty-target",
    "last-index-empty-receiver", "last-index-longer-target", "last-index-utf16",
    "last-index-surrogate",
):
    q_equivalent(label, label)

# Null reaches the ordinary target.length invokevirtual and is caught as the
# existing guest NPE kind; no String-specific native/host branch is permitted.
q_equivalent("last-index-null", "last-index-null")

# A String[] main signature alone must not initialize the String bootstrap.
string_uninitialized = finish("string-uninitialized", "string-uninitialized", 4096)
world = out / string_uninitialized["world"]
_, _, decoded = terminal(world, fixture("string-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("string-uninitialized")["bindingCount"] + 26 not in states
rows["string-uninitialized"] = string_uninitialized

# A no-use root must leave the appended bootstrap uninitialized.
stringbuilder_uninitialized = finish("stringbuilder-uninitialized", "stringbuilder-uninitialized", 4096)
world = out / stringbuilder_uninitialized["world"]
_, _, decoded = terminal(world, fixture("stringbuilder-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("stringbuilder-uninitialized")["bindingCount"] + 84 not in states
rows["stringbuilder-uninitialized"] = stringbuilder_uninitialized

# The generated quota witness allocates two 65536-char guest arrays before its
# second append reaches array-element OOM. Those live arrays cannot fit the fixed
# 1MiB checkpoint, so the pinned engine must refuse publication honestly and
# atomically rather than fabricate a catchable terminal result. The retained
# small field-arena OOM below continues to prove catchable guest OOM semantics.
world = out / "world-stringbuilder-oom-infeasible"
run("stringbuilder-oom-infeasible", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "stringbuilder-oom.zip", "4096"], "stringbuilder-oom")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["stringbuilder-oom-infeasible"] = refusal

# System.err: raw field resolution triggers real System <clinit>; the generated
# constructor handoff checks type assignment and identity without output APIs.
def system_initialized(decoded):
    raw = fixture("system-err")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    system = states[raw + 44]; stream = states[raw + 83]
    assert system["state"] == stream["state"] == 2
    fields = {entry["fieldIndex"]: int(entry["packedValue"], 16) for entry in system["staticValues"]}
    assert fields[2] != 0, fields  # System fields: security, properties, err.
q_equivalent("system-err", "system-err", system_initialized)

# A separate no-use root proves neither image is fabricated/preinitialized.
noinit = finish("system-uninitialized", "system-uninitialized", 4096)
world = out / noinit["world"]
_, _, decoded = terminal(world, fixture("system-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("system-uninitialized")["bindingCount"]
assert raw + 44 not in states and raw + 83 not in states
rows["system-uninitialized"] = noinit

# Retain catchable generic failed-initialization behavior while System remains
# untouched; inducing a failing System initializer would broaden the profile.
def failed_control(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[1]["state"] == 3
    assert 46 not in states and 85 not in states
q_equivalent("failed-init", "failed-init", failed_control)

# Both owned images reject raw replacement before any guest instruction executes.
for label in ("raw-string", "raw-system", "raw-printstream", "raw-stringbuilder"):
    world = out / ("world-" + label)
    run(label + "-replacement", [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
    rows[label] = refusal

# Exact raw30 remains admitted across q1/q7/direct/reopen, while raw31 remains
# atomic at each transport/coordinator/engine layer.
q_equivalent("raw30", "count-30")
world = out / "world-raw31-driver"
run("raw31-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-31.zip", "4096"], "count-31", expect=2)
assert not world.exists(); rows["raw31-driver"] = {"worldExists": False}

def disposable_driver(label, coordinator_keccak):
    source = (build / "main.go").read_text()
    assert source.count("> 30") == 2
    source = source.replace("> 30", "> 31")
    old = "0x" + pins["coordinator"]["runtimeKeccak256"]
    assert source.count(old) == 1
    source = source.replace(old, "0x" + coordinator_keccak)
    path = out / (label + ".go"); exe = out / label; path.write_text(source)
    for suffix, command in (("gofmt", ["gofmt", "-w", path]), ("build", ["go", "build", "-trimpath", "-o", exe, path])):
        with (out / "logs" / (label + "-" + suffix + ".log")).open("w") as stream:
            subprocess.run(list(map(str, command)), cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return exe

coordinator_driver = disposable_driver("raw31-coordinator-driver", pins["coordinator"]["runtimeKeccak256"])
world = out / "world-raw31-coordinator"
run("raw31-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-31.zip", "4096"], "count-31")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
rows["raw31-coordinator"] = refusal

probe = out / "raw31-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[30]") == 4 and text.count("n > 30") == 1
probe_source.write_text(text.replace("[30]", "[31]").replace("n > 30", "n > 31"))
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
with (out / "logs/raw31-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_keccak = json.loads(probe_artifact.read_text())["codeHashes"]["runtimeKeccak256"]
engine_driver = disposable_driver("raw31-engine-driver", probe_keccak)
world = out / "world-raw31-engine"
run("raw31-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-31.zip", "4096"], "count-31")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "31"] and refusal["rootUnchanged"]
rows["raw31-engine"] = refusal

# Aggregate raw-byte bound is unchanged: exactly 262144 reaches the parser and
# +1 is rejected atomically by the coordinator.
world = out / "world-byte-262144"
run("byte-262144", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-30-262144.zip", "4096"], "count-30-262144")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["byte-262144"] = refusal
world = out / "world-byte-262145"
run("byte-262145", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-30-262145.zip", "4096"], "count-30-262145")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
rows["byte-262145"] = refusal

# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.
assert fixture("enumset")["focusLevelAccessFlags"] & 0x4000
for label in ("enumset", "enumset-errors", "enumset-failed"):
    q_equivalent(label, label)
world = out / "world-enumset-uninitialized"
run("enumset-uninitialized", [driver, "setup-chain", world, coordinator, engine, fixtures / "enumset-uninitialized.zip", "4096"], "enumset-uninitialized")
refusal = failure(world, "start-refusal.json")
assert refusal["rootUnchanged"]
rows["enumset-uninitialized"] = refusal
finish("queue", "queue", 4096)
rows["queue"] = {"retained": True}
q_equivalent("oom", "oom")

# Canonically re-encode every successful EVM public receipt (including reopen
# chains); this independent Node verifier has no Java or artifact authority.
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels])
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
summary = {"profile": "MC-STRING-LAST-INDEX-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": time.monotonic() - started,
           "limitations": "Only String.lastIndexOf(String) is added to the prior bounded String surface. No lastIndexOf(String,int), substring, regex, encoding, PrintStream output, Minecraft artifact, or host String implementation is exercised or claimed."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
