#!/usr/bin/env python3
"""Generated-only Locale.ROOT q1/q7/direct/reopen gate; no original inputs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
stage = here.parent / "locale-root-preflight"
root = here.parents[3]
build = Path(sys.argv[1]).resolve(); fixtures = Path(sys.argv[2]).resolve(); out = Path(sys.argv[3]).resolve()
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-locale-root-parent-")
assert fixtures.name.startswith("java-diff-mc-locale-root-fixtures-")
assert out.name.startswith("java-diff-mc-locale-root-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 96 and pins["rawLimits"] == [69, 449904]
assert pins["diagnosticClassBound"] == 165 and pins["engine"]["bytes"] == 378675 <= pins["runtimeCap"] == 393216
assert pins["bootstrapRoot"] == "9d6ac1b79a64b66e5a4654eaf1b3afecafe61c3cff650b825152d278325c7e6c"
assert pins["locale"] == {"slot": 95, "bytes": 285, "sha256": "8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31", "keccak256": "cb4ec03973fafc97a59f911f9c0b46f60b848ef0233807a96f1cdff84d904354", "surface": "ROOT singleton plus private Object-chaining constructor and <clinit> only", "java8": "javac -source 8 -target 8 -g:none"}
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir(); started = time.monotonic(); commands = []; results = {}; canonical = []


def fixture(label): return json.loads((fixtures / (label + ".json")).read_text())
def report(world): return world.parent / "reports" / world.name
def failure(world, name="start-refusal.json"): return json.loads((report(world) / name).read_text())
def words(value): return list(map(str, value["uint256Words"]))


def run(label, arguments, fixture_label, expect=0):
    env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1", "MC_ENTRY_BINDINGS": ",".join(fixture(fixture_label)["entries"])}
    env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log"); began = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, arguments)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, arguments)), "exit": process.returncode, "elapsedSeconds": time.monotonic() - began}
    commands.append(row); (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert process.returncode == expect, (label, process.returncode, log)


spec = importlib.util.spec_from_file_location("locale_root_checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"; coordinator = build / "coordinator/MCEntryCoordinator.json"; engine = build / "engine/MCEntryInterpreter.json"


def terminal(world, raw_count):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0 and head["javaKind"] == head["javaRef"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 449904 and head.get("selectedResourceSize", 0) == 0
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint); assert decoded["classCount"] == raw_count + 96
    return head, checkpoint, decoded


def finish(label, fixture_label, quantum, inspect=None):
    world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (fixture_label + ".zip"); args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    head, checkpoint, decoded = terminal(world, fixture(fixture_label)["bindingCount"])
    if inspect: inspect(decoded, fixture(fixture_label)["bindingCount"])
    canonical.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"], "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(), "initialization": decoded["initialization"]}


def q_equivalent(label, inspect=None):
    values = {}; baseline = None
    for quantum in (1, 7, 4096):
        value = finish(label, label, quantum, inspect); values["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    results[label] = values


# Locale.class links/mirrors the owned image but cannot create ROOT. This is
# read-only checkpoint metadata after normal guest execution, not a fake init.
def locale_uninitialized(decoded, raw):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 95 not in states, states


# ROOT reads execute Locale.<clinit> exactly once. The sole declared static field
# holds one nonzero packed guest reference; equivalence includes opaque state.
def locale_root_state(decoded, raw):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    state = states[raw + 95]
    assert state["state"] == 2 and state["initializerStarted"] == 1 and state["staticFields"] == 1
    values = state["staticValues"]; assert len(values) == 1 and values[0]["fieldIndex"] == 0 and int(values[0]["packedValue"], 16) != 0


q_equivalent("locale-class-literal-uninitialized", locale_uninitialized)
q_equivalent("locale-root", locale_root_state)
for label in ("retained-string", "retained-map", "retained-integer"):
    q_equivalent(label)


def transport_refusal(label, selector, first_word):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum))
        run(label + "-q%d-refusal" % quantum, [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), str(quantum)], label)
        value = failure(world); assert value["rootUnchanged"] and value["selector"] == selector and words(value)[0] == first_word, value
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    results[label] = values


def execution_refusal(label, selector, first_word):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (label + ".zip"); args = [world, coordinator, engine, archive, str(quantum)]
        run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
        where = report(world) / "start-refusal.json"
        if where.exists(): value = json.loads(where.read_text())
        else:
            run(label + "-q%d-finish-refusal" % quantum, [driver, "finish", *args], label)
            value = failure(world, "resume-refusal.json")
        assert value["rootUnchanged"] and value["selector"] == selector and words(value)[0] == first_word, value
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    results[label] = values


transport_refusal("raw-locale-replacement", "0x6a23ad80", "1")
transport_refusal("malformed-locale", "0x8e473891", "1")
execution_refusal("locale-default-omitted", "0xd631c3a4", "3")
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical], "locale-root")
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {"profile": "MC-LOCALE-ROOT-P1", "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [69, 449904], "diagnosticClassBound": 165, "engineBytes": 378675, "engineCapBytes": 393216, "localeSHA256": pins["locale"]["sha256"], "bootstrapRoot": pins["bootstrapRoot"], "results": results, "canonicalReceipts": canonical_receipts, "commands": commands, "wholeGateSeconds": elapsed, "limitations": "Generated Java-8 Locale ROOT plus retained String/Map/Integer controls only. No original class/JAR/resource/network/world/EULA/Done input is opened, executed, or claimed; no Locale API beyond ROOT is supplied."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
