#!/usr/bin/env python3
"""Generated-only raw68/394767 q1/q7/direct/reopen capacity gate.

Only sibling locally generated Java-8 ZIPs are supplied to the ordinary EVM
transport.  No original artifact, JAR, external class/resource, network, world,
provider, EULA, or Done input is opened or claimed.
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
root = here.parents[3]
build = Path(sys.argv[1]).resolve()
fixtures = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-raw68-parent-")
assert fixtures.name.startswith("java-diff-mc-classcount68-byte394767-fixtures-")
assert out.name.startswith("java-diff-mc-raw68-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 95 and pins["rawLimits"] == [68, 394767]
assert pins["diagnosticClassBound"] == 163 and pins["engine"]["bytes"] <= 393216
assert pins["globalNativeBindings"] == 16 and pins["stringLocalBinding"] == 11 and pins["exceptionKinds"] == 14
assert pins["mapEntry"] == {"slot": 94, "bytes": 448,
    "sha256": "5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5",
    "keccak256": "47bd965aa8c05997905d9d71684cc4409974e23e06bc6d360d9f06f82099e4ac"}
assert pins["integer"] == {"slot": 70, "bytes": 2039,
    "sha256": "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd",
    "keccak256": "1a698ef9f803879a7f45c3613a679295cd1db22528c2c0e986fc4f9a6b845ba9"}
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


def failure(world, name="start-refusal.json"):
    return json.loads((report(world) / name).read_text())


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
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 394767
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


# The retained Map.Entry and Integer roots are ordinary executable regressions.
# The null cast must link image95 without creating an initialization record.
def null_link_uninitialized(decoded, raw):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 94 not in states, states

q_equivalent("map-entry-null-link", null_link_uninitialized)
q_equivalent("map-entry-dispatch")
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


# Existing omission/raw/parser precedence is retained while limits move.
refusal_all_quanta("map-entry-comparator-omitted", "0xd631c3a4", "3")
refusal_all_quanta("raw-map-entry-replacement", "0x6a23ad80", "1")
refusal_all_quanta("malformed-map-entry", "0x8e473891", "1")

# Exact raw68 is the capacity focus: q1/q7/direct and terminal reopens agree.
q_equivalent("count-68")

# Raw69 is refused before a durable world by the product driver.  A disposable
# driver widening alone reaches the coordinator guard; a widened disposable
# coordinator reaches the unchanged engine guard.  Neither changes production.
world = out / "world-raw69-driver"
run("raw69-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-69.zip", "4096"], "count-69", expect=2)
assert not world.exists(); rows["raw69-driver"] = {"worldExists": False}


def disposable_driver(label, coordinator_keccak, coordinator_bytes):
    source = (build / "main.go").read_text()
    assert source.count("len(m.Decoders) > 68") == 1 and source.count("len(parts) > 68") == 1
    source = (source.replace("len(m.Decoders) > 68", "len(m.Decoders) > 69")
                    .replace("len(parts) > 68", "len(parts) > 69"))
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


coordinator_driver = disposable_driver("raw69-coordinator-driver", pins["coordinator"]["runtimeKeccak256"], pins["coordinator"]["bytes"])
world = out / "world-raw69-coordinator"
run("raw69-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-69.zip", "4096"], "count-69")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
rows["raw69-coordinator"] = refusal

probe = out / "raw69-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[68]") == 4 and text.count("n > 68") == 1
probe_source.write_text(text.replace("[68]", "[69]").replace("n > 68", "n > 69"))
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
with (out / "logs/raw69-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe = json.loads(probe_artifact.read_text())
engine_driver = disposable_driver("raw69-engine-driver", probe["codeHashes"]["runtimeKeccak256"], len(probe["deployedBytecode"]) // 2)
world = out / "world-raw69-engine"
run("raw69-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-69.zip", "4096"], "count-69")
refusal = failure(world)
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "69"] and refusal["rootUnchanged"]
rows["raw69-engine"] = refusal

# Both aggregate witnesses are individually legal DI0 inputs. Exactly394767 is
# coordinator-admitted and all raw bytes are read before the unchanged 1MiB
# opaque checkpoint cap refuses without a Head. Exactly394768 is rejected by
# the coordinator before engine work or checkpoint publication.
for label, total in (("count-68-394767", 394767), ("count-68-394768", 394768)):
    row = fixture(label)
    assert row["bindingCount"] == 68 and row["totalClassBytes"] == total
    assert max(row["classBytes"].values()) <= 262144

world = out / "world-byte-394767"
run("byte-394767", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-68-394767.zip", "4096"], "count-68-394767")
refusal = failure(world)
assert sum(refusal["actualDI0ReadSizes"]) == 394767
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"]
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
rows["byte-394767"] = {"coordinatorAccepted": True, "checkpointCapRefusal": refusal}

world = out / "world-byte-394768"
run("byte-394768", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-68-394768.zip", "4096"], "count-68-394768")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
rows["byte-394768"] = refusal

# Independently re-encode every public success receipt/event/checkpoint chain;
# this verifier has no Java, ZIP, or artifact evaluation authority.
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels], "map-entry-null-link")
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
whole_gate_seconds = time.monotonic() - started
assert whole_gate_seconds <= 1200, whole_gate_seconds
summary = {
    "profile": "MC-RAW68-BYTE394767-P1", "generatedOnly": True,
    "bootstrapCount": 95, "rawLimits": [68, 394767], "diagnosticClassBound": 163,
    "engineBytes": pins["engine"]["bytes"], "engineCapBytes": pins["runtimeCap"],
    "mapEntrySHA256": pins["mapEntry"]["sha256"], "integerSHA256": pins["integer"]["sha256"],
    "bootstrapRoot": pins["bootstrapRoot"], "results": rows,
    "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
    "limitations": "Only raw capacity advances from raw67/392193/diagnostic162 to raw68/394767/diagnostic163. Bootstrap image95 Map.Entry/root and Integer image/highestOneBit remain byte-identical. The exact raw68 and retained generated Map/Integer focus run q1/q7/direct/reopen; raw69 and 394768 are atomic refusal witnesses. Generated inputs only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine nf.class replay remains deferred.",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
