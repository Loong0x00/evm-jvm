#!/usr/bin/env python3
"""q4096 ordinary-1B generated zero-field Object boundary and gas-blocker probe."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
build, fixtures, out = (Path(p).resolve() for p in sys.argv[1:4])
assert build.parent == fixtures.parent == out.parent == ROOT / "build"
assert build.name.startswith("java-diff-mc-max-objects-4096-build-")
assert fixtures.name.startswith("java-diff-mc-max-objects-4096-fixtures-")
assert out.name.startswith("java-diff-mc-max-objects-4096-preflight-") and not out.exists()
node_modules = ROOT / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["maxArrays"] == pins["maxObjects"] == 4096 and pins["maxHandles"] == 8449
assert pins["canonicalOOMBootstrapLeafIndex"] == 9
assert pins["canonicalOOMClass"] == "java/lang/OutOfMemoryError"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
env0 = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules),
        "PYTHONDONTWRITEBYTECODE": "1", "GOPROXY": "off", "GOSUMDB": "off"}
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
diag_spec = importlib.util.spec_from_file_location("max_objects_4096_checkpoint_diagnostic", HERE / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(diag_spec); diag_spec.loader.exec_module(diagnostic)
started = time.monotonic()
results = {}
canonical_worlds = []
blocker = None


def run(label, argv, fixture):
    env = dict(env0, MC_ENTRY_BINDINGS=",".join(fixture["entries"]))
    log = out / "logs" / (label + ".log")
    began = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, argv)), "exit": process.returncode,
           "elapsedSeconds": time.monotonic() - began}
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert process.returncode == 0, (label, process.returncode, log)


def head_for(world):
    return json.loads((world / "durable-head.json").read_text())


def inspect_world(world, fixture):
    head = head_for(world)
    cp_path = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    checkpoint = cp_path.read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    return head, checkpoint, decoded


for target in (2048, 2049, 4096, 4097):
    label = "object-capacity-%d" % target
    fixture = json.loads((fixtures / (label + ".json")).read_text())
    assert fixture["entries"] == ["generated/ObjectCapacity%d.class" % target]
    assert fixture["requestedAllocations"] == target
    assert fixture["expectedOrdinaryObjects"] == min(target, 4096)
    assert fixture["expectedLifecycle"] == (3 if target == 4097 else 2)
    assert fixture["expectedJavaKind"] == (7 if target == 4097 else 0)
    assert fixture["entryClass"].endswith("ObjectCapacity%d" % target)
    world = out / ("world-" + label + "-q4096")
    archive = fixtures / (label + ".zip")
    args = [world, coordinator, engine, archive, "4096"]
    run(label + "-start", [driver, "setup-chain", *args], fixture)
    run(label + "-finish-q4096", [driver, "finish", *args], fixture)
    head = head_for(world)
    q4096_refusal = None
    narrow_refusal = None
    narrow_resume_calls = 0

    # A blocked full-q4096 call must be independently recorded, then a bounded
    # q256 diagnostic checks whether the issue is simply oversized per-slice work.
    # This never raises the 1B ordinary budget or changes the persisted q4096 cap.
    if head["lifecycle"] == 1:
        refusal_path = out / "reports" / world.name / "resume-refusal.json"
        q4096_refusal = json.loads(refusal_path.read_text())
        assert q4096_refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
        assert q4096_refusal["suppliedGas"] == 1000000000 and q4096_refusal["gas"] <= 1000000000
        assert q4096_refusal["durableHeadUnchanged"] and q4096_refusal["rootUnchanged"]
        if target not in (4096, 4097):
            raise AssertionError(("unexpected q4096 refusal below capacity frontier", target, q4096_refusal))
        while head["lifecycle"] == 1:
            assert narrow_resume_calls < 128, (target, head)
            prior_epoch = head["epoch"]
            narrow_resume_calls += 1
            run(label + "-resume-q256-%03d" % narrow_resume_calls,
                [driver, "resume-one-q", *args[:-1], "4096", "256"], fixture)
            head = head_for(world)
            if head["lifecycle"] == 1 and head["epoch"] == prior_epoch:
                narrow_refusal = json.loads(refusal_path.read_text())
                assert narrow_refusal["durableHeadUnchanged"] and narrow_refusal["rootUnchanged"]
                break

    head, checkpoint, decoded = inspect_world(world, fixture)
    counts = decoded["heapCounts"]
    expected_objects = min(target, 4096)
    expect_oom = target == 4097
    if head["lifecycle"] in (2, 3):
        assert head["lifecycle"] == head["outcome"] == (3 if expect_oom else 2)
        assert head["javaKind"] == (7 if expect_oom else 0)
        assert counts["ordinaryObjects"] == expected_objects
        assert counts["ordinaryArrays"] == 1
        assert counts["ordinaryFields"] == counts["arrayElements"] == 0
        ordinary = [row for row in decoded["heap"]
                    if int(row["metadata"], 16) >> 255 == 1
                    and row["classIndex"] == fixture["bindingCount"]]
        assert len(ordinary) == expected_objects
        assert all(row["rank"] == 0 and row["count"] == 0 and row["cells"] == [] for row in ordinary)
        if expect_oom:
            assert decoded["javaRef"] != 0 and head.get("javaClass") in (None, "")
            oom = next(row for row in decoded["heap"] if row["handle"] == decoded["javaRef"])
            class_index = fixture["bindingCount"] + pins["canonicalOOMBootstrapLeafIndex"]
            assert int(oom["metadata"], 16) >> 255 == 1 and oom["classIndex"] == class_index
            assert counts["exceptionObjects"] >= 1
            typed_oom = {"heapHandle": oom["handle"], "classIndex": oom["classIndex"],
                         "exceptionObjects": counts["exceptionObjects"],
                         "exceptionFields": counts["exceptionFields"],
                         "javaClassEmptyByContract": True}
        else:
            assert decoded["javaRef"] == 0 and head.get("javaClass") in (None, "")
            typed_oom = None
        expected_status = "typed-oom" if expect_oom else "success"
    else:
        assert head["lifecycle"] == 1 and target in (4096, 4097)
        assert q4096_refusal is not None and narrow_refusal is not None
        assert head["quantum"] == 4096
        assert q4096_refusal["durableHeadUnchanged"] and narrow_refusal["durableHeadUnchanged"]
        ordinary = [row for row in decoded["heap"]
                    if int(row["metadata"], 16) >> 255 == 1
                    and row["classIndex"] == fixture["bindingCount"]]
        assert len(ordinary) == counts["ordinaryObjects"]
        assert all(row["rank"] == 0 and row["count"] == 0 and row["cells"] == [] for row in ordinary)
        typed_oom = None
        expected_status = "blocked-before-terminal-by-ordinary-1B-oog"
        blocker = {
            "target": target, "world": world.name, "status": expected_status,
            "head": {key: head[key] for key in ("epoch", "quantum", "lifecycle", "jvmSteps", "internalSteps", "machineRoot", "checkpointSHA256")},
            "heapCounts": counts, "ordinaryObjectRecords": len(ordinary),
            "q4096Refusal": q4096_refusal, "q256Refusal": narrow_refusal,
            "q256ResumeCalls": narrow_resume_calls,
            "note": "Both full q4096 and narrower q256 resume calls fail at the unchanged Head under the 1B ordinary ceiling; the object limit is not reached.",
        }
    before_head = head_for(world)
    run(label + "-reopen", [driver, "verify", *args], fixture)
    after_head = head_for(world)
    authority_keys = ("trieRoot", "engine", "engineCodeHash", "coordinatorCodeHash",
                      "packageRoot", "instanceId", "epoch", "checkpointRoot",
                      "checkpointSHA256", "lifecycle", "outcome", "result",
                      "machineRoot", "vfsRoot", "javaKind", "javaRef", "javaClass",
                      "jvmSteps", "internalSteps")
    assert all(before_head.get(key) == after_head.get(key) for key in authority_keys), (target, "reopen changed EVM authority")
    canonical_worlds.append(world.name)
    results[str(target)] = {
        "status": expected_status, "fixtureSHA256": fixture["zipSHA256"],
        "classSHA256": fixture["classSHA256"][fixture["entries"][0]],
        "entryNameIncludesClassSuffix": fixture["entries"][0].endswith(".class"),
        "world": world.name, "setupQuantum": 4096,
        "finishQ4096Calls": 1, "q4096Refusal": q4096_refusal,
        "q256ResumeCalls": narrow_resume_calls, "q256Refusal": narrow_refusal,
        "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
        "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
        "checkpointSHA256": head["checkpointSHA256"], "checkpointBytes": len(checkpoint),
        "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
        "requestedObjects": target, "ordinaryObjects": counts["ordinaryObjects"],
        "ordinaryArrays": counts["ordinaryArrays"], "ordinaryFields": counts["ordinaryFields"],
        "arrayElements": counts["arrayElements"], "ordinaryObjectRecords": len(ordinary),
        "nextHandle": decoded["nextHandle"], "lifecycle": head["lifecycle"],
        "javaKind": head["javaKind"], "javaRef": head["javaRef"], "typedOOM": typed_oom,
    }
    if blocker:
        break

with (out / "logs/canonical-receipts.log").open("w") as stream:
    subprocess.run(["node", HERE / "verify_receipts.js", build, out, "1", *canonical_worlds],
                   cwd=ROOT, env=env0, stdout=stream, stderr=subprocess.STDOUT,
                   check=True, timeout=1200)
receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
assert receipts["verifiedReceipts"] > 0
elapsed = time.monotonic() - started
summary = {
    "schema": 1,
    "status": "BLOCKED" if blocker else "PASS",
    "profile": "MC-RANDOM-CLASS-P23-MAX-OBJECTS-4096-WORKER-CANDIDATE",
    "generatedOnly": True, "ordinaryGasCap": 1000000000,
    "bootstrapCount": 97, "bootstrapRoot": pins["bootstrapRoot"],
    "maxArrays": 4096, "maxObjects": 4096, "maxHandles": 8449,
    "runtimeBytes": pins["engine"]["bytes"], "runtimeCapBytes": 393216,
    "requestedObjectCountsExcludeImplicitMainStringArray": True,
    "bindingNamesIncludeClassSuffix": True,
    "typedOOMPolicy": "kind7; derive java/lang/OutOfMemoryError from authenticated heap object classIndex=bindingCount+9; javaClass intentionally empty",
    "canonicalReceipts": receipts, "results": results, "blocker": blocker,
    "notAttempted": [target for target in (2048, 2049, 4096, 4097) if str(target) not in results],
    "capacityQuantumCaveat": "Worlds start with persisted q4096. Target4096 hits ordinary-1B OOG before reaching MAX_OBJECTS and a q256 diagnostic retry also OOGs with Head/root unchanged. Target4097 is not attempted because the same per-call gas blocker prevents reaching the object cap. High-count q1/q7 worlds were not attempted.",
    "execution": "Generated Java-8 zero-field java/lang/Object allocations, ordinary local 1B gas, exact heap counters and durable reopen; no original Minecraft inputs.",
    "elapsedSeconds": elapsed,
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
