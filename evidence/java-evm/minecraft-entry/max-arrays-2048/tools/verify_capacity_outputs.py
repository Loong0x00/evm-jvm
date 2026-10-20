#!/usr/bin/env python3
"""Read-only verifier for generated MAX_ARRAYS capacity worlds.

Inputs are disposable generated gate outputs only. It reads their generated
checkpoints, but never consults any original Minecraft artifact or world.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
if len(sys.argv) != 4:
    raise SystemExit("usage: verify_capacity_outputs.py BUILD-DIR FIXTURES-DIR GATE-DIR")
build, fixtures, gate = (Path(value).resolve() for value in sys.argv[1:])
for path, prefix in ((build, "java-diff-mc-max-arrays-2048-build-"),
                     (fixtures, "java-diff-mc-max-arrays-2048-fixtures-"),
                     (gate, "java-diff-mc-max-arrays-2048-gate-")):
    assert path.parent == ROOT / "build" and path.name.startswith(prefix), path
pins = json.loads((build / "pins.json").read_text())
assert pins["maxArrays"] == 2048 and pins["maxHandles"] == 3329
assert pins["engine"]["bytes"] == 392090 <= pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 97

spec = importlib.util.spec_from_file_location("maxArraysCheckpointDiagnostic", HERE / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
expected = {1024: (1024, 2), 1025: (1025, 2), 2048: (2048, 2), 2049: (2048, 3)}
rows = {}
for target, (arrays_expected, lifecycle_expected) in expected.items():
    label = f"array-capacity-{target}"
    fixture = json.loads((fixtures / f"{label}.json").read_text())
    assert fixture["bindingCount"] == 1 and fixture["requestedAllocations"] == target - 1
    world = gate / f"world-{label}-q4096"
    head = json.loads((world / "durable-head.json").read_text())
    assert head["quantum"] == 4096 and head["lifecycle"] == head["outcome"] == lifecycle_expected
    assert head["result"] == 0 and head["totalClassBytes"] == fixture["totalClassBytes"]
    checkpoint_path = world / "checkpoints" / f"{head['checkpointSHA256']}.bin"
    checkpoint = checkpoint_path.read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    state = diagnostic.inspect(checkpoint)
    assert state["lifecycle"] == lifecycle_expected and state["classCount"] == 98
    counts = state["heapCounts"]
    assert counts["ordinaryArrays"] == arrays_expected
    assert counts["ordinaryObjects"] == 0 and counts["arrayElements"] == 0
    assert counts["ordinaryFields"] == 0
    arrays = [record for record in state["heap"]
              if record["rank"] == 1 and record["metadata"] != "0x0"]
    assert len(arrays) == arrays_expected and all(record["count"] == 0 for record in arrays)
    assert state["nextHandle"] == len(state["heap"])
    if lifecycle_expected == 2:
        assert head["javaKind"] == head["javaRef"] == 0
        assert counts["emergency"] == 1 and counts["exceptionObjects"] == 0
        assert counts["exceptionFields"] == 2
        exception = None
    else:
        assert head["javaKind"] == state["javaKind"] == 7
        assert head["javaRef"] == state["javaRef"] != 0
        exception = next(record for record in state["heap"] if record["handle"] == state["javaRef"])
        # One raw entry + five absent base interfaces/wrappers precede the
        # Throwable images; OutOfMemoryError is the fourth image (at +4).
        assert exception["classIndex"] == 10 and exception["rank"] == 0
        assert int(exception["metadata"], 16) >> 255 == 1
        assert counts["emergency"] == counts["exceptionObjects"] == 1
        assert counts["exceptionFields"] == 4
        assert head.get("javaClass") in (None, "")
    report_dir = gate / "reports" / world.name
    receipts = sorted(report_dir.glob("slice-*.json"))
    assert len(receipts) == head["epoch"] > 0
    last = json.loads(receipts[-1].read_text())
    assert last["checkpointSHA256"] == head["checkpointSHA256"]
    rows[str(target)] = {
        "fixtureSHA256": fixture["zipSHA256"],
        "requestedAllocations": fixture["requestedAllocations"],
        "ordinaryArrays": counts["ordinaryArrays"],
        "ordinaryObjects": counts["ordinaryObjects"],
        "arrayElements": counts["arrayElements"],
        "ordinaryFields": counts["ordinaryFields"],
        "emergency": counts["emergency"],
        "exceptionObjects": counts["exceptionObjects"],
        "exceptionFields": counts["exceptionFields"],
        "exceptionClassIndex": exception["classIndex"] if exception else None,
        "exceptionHandle": exception["handle"] if exception else None,
        "epoch": head["epoch"],
        "jvmSteps": head["jvmSteps"],
        "internalSteps": head["internalSteps"],
        "checkpointSHA256": head["checkpointSHA256"],
        "checkpointBytes": len(checkpoint),
        "machineRoot": head["machineRoot"],
        "lifecycle": head["lifecycle"],
        "javaKind": head["javaKind"],
    }

print(json.dumps({
    "scope": "generated capacity checkpoints; read-only; no Minecraft input",
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "maxArrays": pins["maxArrays"],
    "maxHandles": pins["maxHandles"],
    "quantum": 4096,
    "worlds": rows,
    "q1q7Caveat": "No high-count q1/q7 capacity chain was run; the full retained suite includes q1/q7/direct/reopen on its prior controls.",
}, indent=2, sort_keys=True))
