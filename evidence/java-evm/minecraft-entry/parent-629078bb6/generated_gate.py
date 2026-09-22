#!/usr/bin/env python3
"""Generated-only q1/q7/direct/reopen lower-case Locale.ROOT gate."""
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
stage = here.parent / "string-to-lower-case-locale-preflight"
root = here.parents[3]
build, fixtures, out = map(Path, sys.argv[1:4])
build = build.resolve(); fixtures = fixtures.resolve(); out = out.resolve()
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-string-lower-locale-parent-")
assert fixtures.name.startswith("java-diff-mc-string-lower-locale-fixtures-")
assert out.name.startswith("java-diff-mc-string-lower-locale-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 96 and pins["rawLimits"] == [69, 449904]
assert pins["diagnosticClassBound"] == 165 and pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] == 379383 <= pins["runtimeCap"] == 393216
assert pins["bootstrapRoot"] == "39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic(); commands = []; results = {}; canonical = []


def fixture(label): return json.loads((fixtures / (label + ".json")).read_text())
def report(world): return world.parent / "reports" / world.name
def words(value): return [str(word) for word in value["uint256Words"]]


def run(label, arguments, fixture_label, expect=0):
    env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1", "MC_ENTRY_BINDINGS": ",".join(fixture(fixture_label)["entries"])}
    env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log"); began = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, arguments)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, arguments)), "exit": process.returncode, "elapsedSeconds": time.monotonic() - began}
    commands.append(row); (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert process.returncode == expect, (label, process.returncode, log)


spec = importlib.util.spec_from_file_location("lower_checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"; coordinator = build / "coordinator/MCEntryCoordinator.json"; engine = build / "engine/MCEntryInterpreter.json"


def terminal(world, raw_count, java_kind=0):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == (3 if java_kind else 2) and head["result"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 449904 and head.get("selectedResourceSize", 0) == 0
    if java_kind:
        assert head["javaKind"] == java_kind and head["javaRef"] != 0
    else:
        assert head["javaKind"] == head["javaRef"] == 0
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + 96 and decoded["lifecycle"] == head["lifecycle"]
    assert decoded["javaKind"] == head["javaKind"] and decoded["javaRef"] == head["javaRef"]
    return head, checkpoint, decoded


def finish(label, quantum, java_kind=0, inspect=None):
    world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (label + ".zip"); args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], label)
    head, checkpoint, decoded = terminal(world, fixture(label)["bindingCount"], java_kind)
    if inspect: inspect(decoded, fixture(label)["bindingCount"])
    canonical.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"], "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(), "lifecycle": head["lifecycle"], "javaKind": head["javaKind"], "initialization": decoded["initialization"]}


def q_equivalent(label, java_kind=0, inspect=None):
    values = {}; baseline = None
    for quantum in (1, 7, 4096):
        value = finish(label, quantum, java_kind, inspect); values["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    results[label] = values


def locale_root_state(decoded, raw):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    state = states[raw + 95]
    assert state["state"] == 2 and state["initializerStarted"] == 1 and state["staticFields"] == 1
    assert len(state["staticValues"]) == 1 and int(state["staticValues"][0]["packedValue"], 16) != 0


# Exact positive lower-case identities/results, caught NPE, uncaught NPE, Locale
# singleton, and retained independent String/Map$Entry/Integer behaviour.
q_equivalent("lower-ascii", inspect=locale_root_state)
q_equivalent("lower-null-caught")
q_equivalent("lower-null-uncaught", java_kind=6)
for label in ("locale-root", "retained-string", "retained-map", "retained-integer"):
    q_equivalent(label, inspect=locale_root_state if label == "locale-root" else None)


def transport_refusal(label, selector, first_word):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum))
        run(label + "-q%d-refusal" % quantum, [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), str(quantum)], label)
        value = json.loads((report(world) / "start-refusal.json").read_text())
        assert value["rootUnchanged"] and value["selector"] == selector and words(value)[0] == first_word, value
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    results[label] = values


def execution_refusal(label, selector, first_word, atomic=False):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (label + ".zip"); args = [world, coordinator, engine, archive, str(quantum)]
        run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
        location = report(world) / "start-refusal.json"
        if location.exists(): value = json.loads(location.read_text())
        else:
            run(label + "-q%d-finish-refusal" % quantum, [driver, "finish", *args], label)
            location = report(world) / "resume-refusal.json"; value = json.loads(location.read_text())
        assert value["rootUnchanged"] and value["selector"] == selector and words(value)[0] == first_word, value
        # `rootUnchanged` is the driver’s before/after EVM-root assertion for
        # the failed slice: non-ASCII therefore cannot publish a partial String.
        if atomic: assert value["rootUnchanged"]
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    results[label] = values


transport_refusal("raw-string-replacement", "0x6a23ad80", "1")
transport_refusal("raw-locale-replacement", "0x6a23ad80", "1")
execution_refusal("upper-omitted", "0x32e310eb", "1")
execution_refusal("lower-non-ascii-refusal", "0x32e310eb", "1", atomic=True)

run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical], "lower-ascii")
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {"profile": "MC-STRING-LOWER-LOCALE-P1", "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [69, 449904], "diagnosticClassBound": 165, "globalNativeBindings": 16, "stringLocalBinding": 12, "engineBytes": 379383, "engineCapBytes": 393216, "stringSHA256": pins["string"]["sha256"], "localeSHA256": pins["locale"]["sha256"], "bootstrapRoot": pins["bootstrapRoot"], "results": results, "canonicalReceipts": canonical_receipts, "commands": commands, "wholeGateSeconds": elapsed, "limitations": "Generated Java-8 ASCII String.toLowerCase(Locale.ROOT), exact Locale ROOT, refusal and retained controls only. No original class/JAR/resource/network/world/EULA/Done input is opened, executed, or claimed; no Unicode/default-locale/language/country/upper-case surface is supplied."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
