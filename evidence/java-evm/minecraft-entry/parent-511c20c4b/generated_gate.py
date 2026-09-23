#!/usr/bin/env python3
"""Generated-only Random construction q1/q7/direct/reopen and retained raw71 gate."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
stage = here.parent / "random-class-preflight"
root = here.parents[3]
build, fixtures, out = map(Path, sys.argv[1:4])
build = build.resolve(); fixtures = fixtures.resolve(); out = out.resolve()
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-random-parent-")
assert fixtures.name.startswith("java-diff-mc-random-class-fixtures-")
assert out.name.startswith("java-diff-mc-random-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 97 and pins["rawLimits"] == [71, 471911]
assert pins["diagnosticClassBound"] == 168 and pins["globalNativeBindings"] == 18 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["bootstrapRoot"] == "7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887"
assert pins["math"]["sha256"] == "6092139a4281d1a0cbbaf5292ad894a4d494f5589a45605081ccb12ac3ed9861"
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
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 471911 and head.get("selectedResourceSize", 0) == 0
    if java_kind:
        assert head["javaKind"] == java_kind and head["javaRef"] != 0
    else:
        assert head["javaKind"] == head["javaRef"] == 0
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + 97 and decoded["lifecycle"] == head["lifecycle"]
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
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"], "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(), "lifecycle": head["lifecycle"], "javaKind": head["javaKind"], "initialization": decoded["initialization"], "nextHandle": decoded["nextHandle"], "heap": decoded["heap"], "heapCounts": decoded["heapCounts"]}


def q_equivalent(label, java_kind=0, inspect=None):
    values = {}; baseline = None
    for quantum in (1, 7, 4096):
        value = finish(label, quantum, java_kind, inspect); values["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "lifecycle", "javaKind"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    results[label] = values
    return baseline


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
for label in ("locale-root", "retained-string", "retained-map", "retained-integer", "retained-system-out-err", "retained-properties"):
    q_equivalent(label, inspect=locale_root_state if label == "locale-root" else None)

# Binding18 must produce exactly the Java-8 binary64 raw witnesses across every
# quantum/reopen path; fixture assertions cover normal/subnormal/carry/NaN cases.
q_equivalent("math-sqrt-binary64")


def random_construction_state(decoded, raw):
    main = next(row for row in decoded["initialization"] if row["classIndex"] == 0)
    assert len(main["staticValues"]) == 1
    result = main["staticValues"][0]
    assert result["fieldIndex"] == 0 and (int(result["packedValue"], 16) & 0xffffffff) == 7
    instances = [entry for entry in decoded["heap"]
                 if int(entry["metadata"], 16) >> 255 == 1 and entry["classIndex"] == raw + 96]
    assert len(instances) == 2, instances
    assert instances[0]["handle"] != instances[1]["handle"]


q_equivalent("random-construction", inspect=random_construction_state)


def identity_state(decoded, raw):
    # Static fields retain the direct native results as packed guest ints.
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    main = states[0]
    fields = {entry["fieldIndex"]: int(entry["packedValue"], 16) & 0xffffffff for entry in main["staticValues"]}
    assert list(fields) == list(range(10)), fields
    values = [fields[index] for index in range(10)]
    assert values[0] == 0 and values[1] != 0 and values[1] == values[2]
    assert values[3] != 0 and values[4] != 0 and values[4] == values[5]
    assert values[6] != 0 and values[6] == values[7] and values[8] != 0 and values[9] == 7
    identities = (values[1], values[3], values[4], values[6], values[8])
    assert len(set(identities)) == len(identities), identities
    heap = {entry["handle"]: entry for entry in decoded["heap"]}
    assert set(identities) <= set(heap), (identities, sorted(heap))
    def object_handle(handle, class_index):
        entry = heap[handle]
        assert int(entry["metadata"], 16) >> 255 == 1 and entry["classIndex"] == class_index, entry
    object_handle(values[1], raw)       # ordinary Object
    object_handle(values[3], raw)       # distinct ordinary Object
    array = heap[values[4]]
    assert int(array["metadata"], 16) >> 255 == 0 and array["rank"] == 1 and array["classIndex"] == 0, array
    object_handle(values[6], raw + 39)  # canonical Class mirror
    object_handle(values[8], 1)         # overriding guest class; hashCode was not dispatched


def system_state(value, raw):
    states = {entry["classIndex"]: entry for entry in value["initialization"]}
    return states[raw + 44]


identity = q_equivalent("identity-hash", inspect=identity_state)
control = q_equivalent("identity-no-mutation-control")
# Both generated programs allocate the same ordinary, array, Class-mirror and
# override objects and initialize the same canonical System.  This equality
# excludes the entry's saved int results and proves binding17 made no allocation
# or state write across q1/q7/direct/reopen.
def heap_state_without_generated_class_name(heap):
    # The two raw entry class names differ but have the same UTF-16 length. Their
    # Class-mirror backing char[] contents are deliberately not execution state;
    # every ordinal/type/size/reference cell remains equal.
    return [{**entry, "cells": [] if entry["metadata"] == "0x43" else entry["cells"]} for entry in heap]
assert heap_state_without_generated_class_name(identity["heap"]) == heap_state_without_generated_class_name(control["heap"])
assert identity["heapCounts"] == control["heapCounts"]
assert system_state(identity, 2) == system_state(control, 2)


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
transport_refusal("raw-system-replacement", "0x6a23ad80", "1")
transport_refusal("raw-math-replacement", "0x6a23ad80", "1")
transport_refusal("raw-random-replacement", "0x6a23ad80", "1")
execution_refusal("upper-omitted", "0x32e310eb", "1")
execution_refusal("math-cbrt-omitted", "0xd631c3a4", "3", atomic=True)
execution_refusal("random-next-int-omitted", "0xd631c3a4", "3", atomic=True)
execution_refusal("random-set-seed-omitted", "0xd631c3a4", "3", atomic=True)
execution_refusal("lower-non-ascii-refusal", "0x32e310eb", "1", atomic=True)
execution_refusal("object-hashcode-omitted", "0xd631c3a4", "3", atomic=True)
execution_refusal("system-general-omitted", "0xd631c3a4", "3", atomic=True)


def missing_class_refusal(label):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum)); archive = fixtures / (label + ".zip"); args = [world, coordinator, engine, archive, str(quantum)]
        run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
        location = report(world) / "start-refusal.json"
        if location.exists(): value = json.loads(location.read_text())
        else:
            run(label + "-q%d-finish-refusal" % quantum, [driver, "finish", *args], label)
            value = json.loads((report(world) / "resume-refusal.json").read_text())
        assert value["rootUnchanged"] and value["selector"] == "0x555db429" and words(value)[0] == "4107", value
        values["direct" if quantum == 4096 else "q" + str(quantum)] = value
    results[label] = values


missing_class_refusal("strictmath-sqrt-omitted")


# Exact raw71 is the capacity focus: q1/q7/direct terminal reopens agree.
q_equivalent("count-71")

# Raw72 is refused before a durable product world. A disposable driver widening
# alone reaches the coordinator fixed-array guard; a widened disposable
# coordinator reaches the unchanged engine raw-class guard. Neither mutates
# product code, the checked-in images, or a successful Head.
world = out / "world-raw72-driver"
run("raw72-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-72.zip", "4096"], "count-72", expect=2)
assert not world.exists(); results["raw72-driver"] = {"worldExists": False}


def disposable_driver(label, coordinator_keccak, coordinator_bytes):
    source = (build / "main.go").read_text()
    assert source.count("len(m.Decoders) > 71") == 1 and source.count("len(parts) > 71") == 1
    source = (source.replace("len(m.Decoders) > 71", "len(m.Decoders) > 72")
                    .replace("len(parts) > 71", "len(parts) > 72"))
    old = "0x" + pins["coordinator"]["runtimeKeccak256"]
    assert source.count(old) == 1
    source = source.replace(old, "0x" + coordinator_keccak)
    old_size = "len(coordRun) != %d" % pins["coordinator"]["bytes"]
    assert source.count(old_size) == 1
    source = source.replace(old_size, "len(coordRun) != %d" % coordinator_bytes)
    path = out / (label + ".go"); exe = out / label; path.write_text(source)
    for suffix, command in (("gofmt", ["gofmt", "-w", path]), ("build", ["go", "build", "-trimpath", "-o", exe, path])):
        with (out / "logs" / (label + "-" + suffix + ".log")).open("w") as stream:
            subprocess.run(list(map(str, command)), cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return exe


coordinator_driver = disposable_driver("raw72-coordinator-driver", pins["coordinator"]["runtimeKeccak256"], pins["coordinator"]["bytes"])
world = out / "world-raw72-coordinator"
run("raw72-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-72.zip", "4096"], "count-72")
refusal = json.loads((report(world) / "boundary-refusal.json").read_text())
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
results["raw72-coordinator"] = refusal

probe = out / "raw72-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[71]") == 4 and text.count("n > 71") == 1
probe_source.write_text(text.replace("[71]", "[72]").replace("n > 71", "n > 72"))
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1"}
with (out / "logs/raw72-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_json = json.loads(probe_artifact.read_text())
engine_driver = disposable_driver("raw72-engine-driver", probe_json["codeHashes"]["runtimeKeccak256"], len(probe_json["deployedBytecode"]) // 2)
world = out / "world-raw72-engine"
run("raw72-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-72.zip", "4096"], "count-72")
refusal = json.loads((report(world) / "start-refusal.json").read_text())
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "72"] and refusal["rootUnchanged"]
results["raw72-engine"] = refusal

# Both aggregate witnesses are generated legal DI0 inputs. Exact471911 is
# coordinator-admitted and all raw bytes must be read before the existing 1MiB
# opaque checkpoint cap atomically refuses without a durable Head. Exact471912
# rejects at the coordinator before engine work or checkpoint publication.
for label, total in (("count-71-471911", 471911), ("count-71-471912", 471912)):
    row = fixture(label)
    assert row["bindingCount"] == 71 and row["totalClassBytes"] == total
    assert max(row["classBytes"].values()) <= 262144

world = out / "world-byte-471911"
run("byte-471911", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-71-471911.zip", "4096"], "count-71-471911")
refusal = json.loads((report(world) / "start-refusal.json").read_text())
assert sum(refusal["actualDI0ReadSizes"]) == 471911
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"]
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
results["byte-471911"] = {"coordinatorAccepted": True, "checkpointCapRefusal": refusal}

world = out / "world-byte-471912"
run("byte-471912", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-71-471912.zip", "4096"], "count-71-471912")
refusal = json.loads((report(world) / "boundary-refusal.json").read_text())
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
results["byte-471912"] = refusal

run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical], "lower-ascii")
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {"profile": "MC-RANDOM-CLASS-P1", "generatedOnly": True, "bootstrapCount": 97, "rawLimits": [71, 471911], "diagnosticClassBound": 168, "globalNativeBindings": 18, "stringLocalBinding": 12, "engineBytes": pins["engine"]["bytes"], "engineCapBytes": 393216, "systemSHA256": pins["system"]["sha256"], "stringSHA256": pins["string"]["sha256"], "localeSHA256": pins["locale"]["sha256"], "mathSHA256": pins["math"]["sha256"], "randomSHA256": pins["random"]["sha256"], "bootstrapRoot": pins["bootstrapRoot"], "results": results, "canonicalReceipts": canonical_receipts, "commands": commands, "wholeGateSeconds": elapsed, "limitations": "Only Java8 java/util/Random image97 is appended: concrete Object subclass implementing Serializable with public no-arg constructor only. It has no seed/state or RNG APIs; no Java RNG or host time semantics are claimed. Math.sqrt and the other prior96 images are byte-for-byte retained. Generated Java-8 two-object construction/identity witness, retained Math/identityHash/System/String/Locale/Map/Integer, raw71 and exact capacity refusals only. No original class/JAR/resource/network/provider/world/EULA/Done input is opened, executed, or claimed. Parent genuine replay remains deferred."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
