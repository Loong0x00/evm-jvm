#!/usr/bin/env python3
"""Generated-only EVM gate for genuine guest Throwable frame snapshots.

No original archive/JAR, network input, Minecraft execution, world, EULA, or Done
marker is accepted by this gate.  Host JVM use occurred only while compiling the
trusted generated fixtures.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build = Path(sys.argv[1]).resolve(); fixtures = Path(sys.argv[2]).resolve(); out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-throwable-guest-stack-trace-build-")
assert fixtures.name.startswith("java-diff-mc-throwable-guest-stack-trace-fixtures-")
assert out.name.startswith("java-diff-mc-throwable-guest-stack-trace-gate-") and not out.exists()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 94 and pins["globalNativeBindings"] == 14
assert pins["rawLimits"] == [50, 324338] and pins["diagnosticClassBound"] == 144
assert pins["engine"]["bytes"] <= 393216 and pins["maxFrames"] == 128
assert pins["bootstrapSHA256"]["Throwable"] == "4454ff55c663c08bd8e17f8087193ef72e11f7154e3761f96f5a6cafd4507fa6"
assert pins["bootstrapSHA256"]["StackTraceElement"] == "25ce147f4adc080d71bdf752e245cfebc4191c56b7d0feaa714ad963197a18de"
assert pins["bootstrapRoot"] == json.loads((stage / "root-commitment.json").read_text())["bootstrapRoot"]
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic(); commands = []; rows = {}

def fixture(label): return json.loads((fixtures / (label + ".json")).read_text())
def report_path(world, name): return world.parent / "reports" / world.name / name

def run(label, args, fixture_label=None, expected=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(root / "jvmevm/runtime/node_modules"), PYTHONDONTWRITEBYTECODE="1")
    if fixture_label is not None: env["MC_ENTRY_BINDINGS"] = ",".join(fixture(fixture_label)["entries"])
    log = out / "logs" / (label + ".log"); before = time.monotonic()
    with log.open("w") as stream:
        p = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": p.returncode, "elapsedSeconds": time.monotonic() - before}
    commands.append(row); (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert p.returncode == expected, (label, p.returncode, log)

spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"; coordinator = build / "coordinator/MCEntryCoordinator.json"; engine = build / "engine/MCEntryInterpreter.json"

def terminal(world, label):
    head = json.loads((world / "durable-head.json").read_text()); f = fixture(label)
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == f["bindingCount"] and head["totalClassBytes"] == f["totalClassBytes"]
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint); assert decoded["classCount"] == f["bindingCount"] + 94
    # Every positive source sets its raw static result field to 7 after all guest
    # stack-frame/index/name/freshness checks.  Packed static cells preserve the
    # int payload in the low word.
    raw = f["bindingCount"]; states = {x["classIndex"]: x for x in decoded["initialization"]}
    assert states[0]["state"] == 2
    assert any(int(v["packedValue"], 16) & ((1 << 64) - 1) == 7 for v in states[0]["staticValues"])
    return head, checkpoint, decoded, states

def finish(label, fixture_label, quantum, inspect=None):
    world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    head, checkpoint, decoded, states = terminal(world, fixture_label)
    if inspect: inspect(decoded, states, fixture(fixture_label)["bindingCount"])
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest()}

def q_equivalent(label, fixture_label, inspect=None):
    baseline = None; values = {}
    for quantum in (1, 7, 4096):
        value = finish(label, fixture_label, quantum, inspect)
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for k in ("jvmSteps", "internalSteps", "machineRoot", "opaquePayloadSHA256"):
                assert value[k] == baseline[k], (label, k, value, baseline)
    rows[label] = values

def stack_initialized(decoded, states, raw):
    assert states[raw + 5]["state"] == 2      # Throwable active use
    # Binding14 allocates the bootstrap-owned element directly; ordinary
    # invokevirtual getter dispatch is not class active-use, so its no-<clinit>
    # leaf remains dormant exactly as Thread's prior array allocation did.
    assert raw + 90 not in states

def thread_initialized(decoded, states, raw):
    assert states[raw + 50]["state"] == 2     # Thread.currentThread active use
    assert raw + 90 not in states              # Thread's anewarray is not active use of leaf

# Guest source asserts actual top-first leaf/nested/main and leaf/main sequences,
# real dotted class and method names, three indexed elements, false native flags,
# and fresh returned arrays/elements. q1/q7/direct/reopen preserve the terminal
# machine root and opaque checkpoint payload exactly.
q_equivalent("guest-stack", "guest-stack", stack_initialized)
q_equivalent("guest-stack-two", "guest-stack-two", stack_initialized)
q_equivalent("thread-empty", "thread-empty", thread_initialized)

# Dormant image control: fixed boot leaves do not initialize merely by installation.
uninitialized = finish("uninitialized", "uninitialized", 4096)
world = out / uninitialized["world"]; _, _, decoded, states = terminal(world, "uninitialized")
assert 1 + 5 not in states and 1 + 90 not in states
rows["uninitialized"] = uninitialized

# Raw replacements must be caught before guest execution and leave the EVM root
# unchanged. Throwable retains its historic canonical-family ClassError precedence;
# StackTraceElement is its append-family bootstrap ownership refusal.
for label, selector, words in (("raw-throwable", "0x427cfac5", ["6", "1"]),
                               ("raw-stack-trace-element", "0x6a23ad80", ["1", "1"])):
    world = out / ("world-" + label); archive = fixtures / (label + ".zip")
    run(label + "-start", [driver, "setup-chain", world, coordinator, engine, archive, "4096"], label)
    refusal = json.loads(report_path(world, "start-refusal.json").read_text())
    assert refusal["selector"] == selector and refusal["uint256Words"] == words and refusal["rootUnchanged"]
    head = json.loads((world / "durable-head.json").read_text())
    assert head["epoch"] == 0 and head["checkpointRoot"].endswith("0" * 64)
    rows[label] = refusal

# Independently re-encode all successful public EVM receipts. This Node verifier
# has no Java authority; it only checks the durable ABI/event receipt encoding.
worlds = [v["world"] for r in rows.values() if isinstance(r, dict) for v in r.values() if isinstance(v, dict) and "world" in v]
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *worlds])
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {
    "profile": "MC-THROWABLE-GUEST-STACK-TRACE-PREPARATION", "generatedOnly": True,
    "results": rows, "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": elapsed,
    "limitations": "This verifies only trusted generated guest classes. It snapshots active interpreter frames for Throwable.getStackTrace, keeps Thread.getStackTrace empty, and makes no original/JAR/network/Minecraft/world/EULA/Done claim.",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
