#!/usr/bin/env python3
"""Generated-only raw70 / byte464925 q1/q7/direct/reopen capacity gate."""
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
stage = here.parent
root = here.parents[4]
build, fixtures, out = map(Path, sys.argv[1:4])
build = build.resolve(); fixtures = fixtures.resolve(); out = out.resolve()
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-classcount70-byte464925-build-")
assert fixtures.name.startswith("java-diff-mc-classcount70-byte464925-fixtures-")
assert out.name.startswith("java-diff-mc-classcount70-byte464925-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 96 and pins["rawLimits"] == [70, 464925]
assert pins["diagnosticClassBound"] == 166 and pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
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
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 464925 and head.get("selectedResourceSize", 0) == 0
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


# Exact raw70 is the capacity focus: q1/q7/direct terminal reopens agree.
q_equivalent("count-70")

# Raw71 is refused before a durable product world. A disposable driver widening
# alone reaches the coordinator fixed-array guard; a widened disposable
# coordinator reaches the unchanged engine raw-class guard. Neither mutates
# product code, the checked-in images, or a successful Head.
world = out / "world-raw71-driver"
run("raw71-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-71.zip", "4096"], "count-71", expect=2)
assert not world.exists(); results["raw71-driver"] = {"worldExists": False}


def disposable_driver(label, coordinator_keccak, coordinator_bytes):
    source = (build / "main.go").read_text()
    assert source.count("len(m.Decoders) > 70") == 1 and source.count("len(parts) > 70") == 1
    source = (source.replace("len(m.Decoders) > 70", "len(m.Decoders) > 71")
                    .replace("len(parts) > 70", "len(parts) > 71"))
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


coordinator_driver = disposable_driver("raw71-coordinator-driver", pins["coordinator"]["runtimeKeccak256"], pins["coordinator"]["bytes"])
world = out / "world-raw71-coordinator"
run("raw71-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-71.zip", "4096"], "count-71")
refusal = json.loads((report(world) / "boundary-refusal.json").read_text())
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
results["raw71-coordinator"] = refusal

probe = out / "raw71-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[70]") == 4 and text.count("n > 70") == 1
probe_source.write_text(text.replace("[70]", "[71]").replace("n > 70", "n > 71"))
env = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1"}
with (out / "logs/raw71-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_json = json.loads(probe_artifact.read_text())
engine_driver = disposable_driver("raw71-engine-driver", probe_json["codeHashes"]["runtimeKeccak256"], len(probe_json["deployedBytecode"]) // 2)
world = out / "world-raw71-engine"
run("raw71-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-71.zip", "4096"], "count-71")
refusal = json.loads((report(world) / "start-refusal.json").read_text())
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "71"] and refusal["rootUnchanged"]
results["raw71-engine"] = refusal

# Both aggregate witnesses are generated legal DI0 inputs. Exact464925 is
# coordinator-admitted and all raw bytes must be read before the existing 1MiB
# opaque checkpoint cap atomically refuses without a durable Head. Exact464926
# rejects at the coordinator before engine work or checkpoint publication.
for label, total in (("count-70-464925", 464925), ("count-70-464926", 464926)):
    row = fixture(label)
    assert row["bindingCount"] == 70 and row["totalClassBytes"] == total
    assert max(row["classBytes"].values()) <= 262144

world = out / "world-byte-464925"
run("byte-464925", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-70-464925.zip", "4096"], "count-70-464925")
refusal = json.loads((report(world) / "start-refusal.json").read_text())
assert sum(refusal["actualDI0ReadSizes"]) == 464925
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"]
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
results["byte-464925"] = {"coordinatorAccepted": True, "checkpointCapRefusal": refusal}

world = out / "world-byte-464926"
run("byte-464926", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-70-464926.zip", "4096"], "count-70-464926")
refusal = json.loads((report(world) / "boundary-refusal.json").read_text())
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
results["byte-464926"] = refusal

run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical], "lower-ascii")
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {"profile": "MC-CLASSCOUNT70-BYTE464925-P1", "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [70, 464925], "diagnosticClassBound": 166, "globalNativeBindings": 16, "stringLocalBinding": 12, "engineBytes": pins["engine"]["bytes"], "engineCapBytes": 393216, "stringSHA256": pins["string"]["sha256"], "localeSHA256": pins["locale"]["sha256"], "bootstrapRoot": pins["bootstrapRoot"], "results": results, "canonicalReceipts": canonical_receipts, "commands": commands, "wholeGateSeconds": elapsed, "limitations": "Capacity only from raw69/449904/diagnostic165 to raw70/464925/diagnostic166. Generated Java-8 lower-case Locale.ROOT, retained String/Map/Integer controls, raw70 success, raw71 and byte boundary witnesses only. No original class/JAR/resource/network/world/EULA/Done input is opened, executed, or claimed; no Unicode/default-locale/language/country/upper-case surface is supplied. Parent genuine Validate replay remains deferred."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
