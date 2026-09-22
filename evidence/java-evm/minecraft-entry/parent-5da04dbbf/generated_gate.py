#!/usr/bin/env python3
"""Full generated/retained Map.Entry q1/q7/direct/reopen gate.

This gate consumes only sibling locally generated Java-8 ZIPs.  It neither opens
an original artifact/JAR/resource/world nor grants host execution authority over
any classfile sent to EVM.
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
root = here.parents[3]
build = Path(sys.argv[1]).resolve()
fixtures = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-map-entry-parent-")
assert fixtures.name.startswith("java-diff-mc-map-entry-link-fixtures-")
assert out.name.startswith("java-diff-mc-map-entry-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 95 and pins["rawLimits"] == [65, 381732]
assert pins["diagnosticClassBound"] == 160 and pins["engine"]["bytes"] <= 393216
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14
assert pins["mapEntry"] == {"slot": 94, "bytes": 448,
    "sha256": "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5",
    "keccak256": "47bd965aa8c05997905d9d71684cc4409974e23e06bc6d360d9f06f82099e4ac"}
assert pins["bootstrapRoot"] == "9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic()
commands = []
rows = {}
canonical_labels = []


def fixture(label):
    return json.loads((fixtures / (label + ".json")).read_text())


def bindings(label):
    return ",".join(fixture(label)["entries"])


def report(world):
    return world.parent / "reports" / world.name


def failure(world):
    return json.loads((report(world) / "start-refusal.json").read_text())


def words(value):
    return list(map(str, value["uint256Words"]))


def run(label, args, fixture_label, expect=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    env["MC_ENTRY_BINDINGS"] = bindings(fixture_label)
    env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log")
    before = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream,
                              stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": proc.returncode,
           "elapsedSeconds": time.monotonic() - before}
    commands.append(row)
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert proc.returncode == expect, (label, proc.returncode, log)


spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"


def terminal(world, raw_count):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 381732
    assert head.get("selectedResourceSize", 0) == 0
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + 95
    return head, checkpoint, decoded


def finish(label, fixture_label, quantum, inspect=None):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    row = fixture(fixture_label)
    head, checkpoint, decoded = terminal(world, row["bindingCount"])
    if inspect is not None:
        inspect(decoded, row["bindingCount"])
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest()}


def q_equivalent(label, inspect=None):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish(label, label, quantum, inspect)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None:
            baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row


# New interface link and dispatch are full q1/q7/direct/reopen proofs.  A null
# checkcast must not add an initialization record merely by resolving image95.
def null_link_uninitialized(decoded, raw):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 94 not in states, states
q_equivalent("map-entry-null-link", null_link_uninitialized)
q_equivalent("map-entry-dispatch")

# Retained executable Map and Integer witnesses run under the same complete
# q1/q7/direct/reopen matrix, not merely a source-image comparison.
q_equivalent("retained-map")
q_equivalent("retained-integer")


def refusal_all_quanta(label, selector=None, first_word=None):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum))
        run(label + "-q%d-refusal" % quantum,
            [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), str(quantum)], label)
        value = failure(world)
        assert value["rootUnchanged"], value
        if selector is not None:
            assert value["selector"] == selector, value
        if first_word is not None:
            assert words(value)[0] == first_word, value
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    rows[label] = values


# Extra Java-8 comparator helpers stay absent: ordinary member resolution fails
# before guest execution.  Valid raw replacement is bootstrap-owned, and a
# locally generated malformed raw image has parser precedence, all atomically.
refusal_all_quanta("map-entry-comparator-omitted", "0xd631c3a4", "3")
refusal_all_quanta("raw-map-entry-replacement", "0x6a23ad80", "1")
refusal_all_quanta("malformed-map-entry", "0x8e473891", "1")

# Canonically re-encode every successful receipt/event/checkpoint chain.  The
# independent verifier has no Java/class/ZIP evaluation authority.
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels], "map-entry-null-link")
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
whole_gate_seconds = time.monotonic() - started
assert whole_gate_seconds <= 1200, whole_gate_seconds
summary = {
    "profile": "MC-MAP-ENTRY-LINK-P1", "generatedOnly": True, "bootstrapCount": 95,
    "rawLimits": [65, 381732], "diagnosticClassBound": 160,
    "engineBytes": pins["engine"]["bytes"], "engineCapBytes": pins["runtimeCap"],
    "mapEntrySHA256": pins["mapEntry"]["sha256"], "bootstrapRoot": pins["bootstrapRoot"],
    "results": rows, "canonicalReceipts": canonical, "commands": commands,
    "wholeGateSeconds": whole_gate_seconds,
    "limitations": "One generated javac Java-8 Map.Entry image95 only: its five abstract methods link/dispatch through a generated implementation. Comparator/default helpers and implementation behavior remain absent. Generated retained Map/Integer witnesses and all positive cases use q1/q7/direct/reopen; refusals are atomic at all three quanta. No original/JAR/external class/resource/network/world/provider/Done input or claim; parent replay remains deferred.",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
