#!/usr/bin/env python3
"""Fast q4096 object-quota smoke before the complete retained gate."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
build, fixtures, out = map(lambda p: Path(p).resolve(), sys.argv[1:4])
assert build.parent == fixtures.parent == out.parent == ROOT / "build"
assert build.name.startswith("java-diff-mc-max-objects-2048-build-")
assert fixtures.name.startswith("java-diff-mc-max-objects-2048-fixtures-")
assert out.name.startswith("java-diff-mc-max-objects-2048-preflight-") and not out.exists()
node_modules = ROOT / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["maxObjects"] == 2048 and pins["maxArrays"] == 2048 and pins["maxHandles"] == 4353
assert pins["canonicalOOMBootstrapLeafIndex"] == 9
assert pins["canonicalOOMClass"] == "java/lang/OutOfMemoryError"
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
env_base = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules),
            "PYTHONDONTWRITEBYTECODE": "1"}

def run(label, argv, fixture_label):
    fixture = json.loads((fixtures / (fixture_label + ".json")).read_text())
    env = dict(env_base, MC_ENTRY_BINDINGS=",".join(fixture["entries"]))
    log = out / "logs" / (label + ".log")
    start = time.monotonic()
    with log.open("w") as stream:
        cp = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, stdout=stream,
                            stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "argv": list(map(str, argv)), "exit": cp.returncode,
           "elapsedSeconds": time.monotonic() - start}
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert cp.returncode == 0, (label, cp.returncode, log)
    return row

spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
diagnostic_spec = spec.spec_from_file_location("max_objects_2048_diagnostic", HERE / "checkpoint_diagnostic.py")
diagnostic = spec.module_from_spec(diagnostic_spec); diagnostic_spec.loader.exec_module(diagnostic)
results = {}
for target in (1024, 1025, 2048, 2049):
    label = "object-capacity-%d" % target
    fixture = json.loads((fixtures / (label + ".json")).read_text())
    assert fixture["entries"] == ["generated/ObjectCapacity%d.class" % target]
    assert fixture["requestedAllocations"] == target
    world = out / ("world-" + label + "-q4096")
    archive = fixtures / (label + ".zip")
    args = [world, coordinator, engine, archive, "4096"]
    for phase, argv in (
        ("start", [driver, "setup-chain", *args]),
        ("finish", [driver, "finish", *args]),
        ("reopen", [driver, "verify", *args]),
    ):
        run(label + "-" + phase, argv, label)
    head = json.loads((world / "durable-head.json").read_text())
    cp_path = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    checkpoint = cp_path.read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    expected = min(target, 2048)
    assert head["quantum"] == 4096 and head["epoch"] > 0
    assert head["lifecycle"] == head["outcome"] == (3 if target == 2049 else 2)
    assert head["javaKind"] == (7 if target == 2049 else 0)
    assert decoded["lifecycle"] == head["lifecycle"] and decoded["javaKind"] == head["javaKind"]
    assert decoded["heapCounts"]["ordinaryObjects"] == expected
    assert decoded["heapCounts"]["ordinaryArrays"] == 1
    assert decoded["heapCounts"]["ordinaryFields"] == 0
    assert decoded["heapCounts"]["arrayElements"] == 0
    objects = [row for row in decoded["heap"]
               if int(row["metadata"], 16) >> 255 == 1
               and row["classIndex"] == fixture["bindingCount"]]
    assert len(objects) == expected
    assert all(row["rank"] == 0 and row["count"] == 0 and row["cells"] == [] for row in objects)
    if target == 2049:
        assert decoded["javaRef"] != 0
        oom = next(row for row in decoded["heap"] if row["handle"] == decoded["javaRef"])
        assert int(oom["metadata"], 16) >> 255 == 1
        expected_class_index = fixture["bindingCount"] + pins["canonicalOOMBootstrapLeafIndex"]
        assert oom["classIndex"] == expected_class_index and oom["rank"] == 0
        assert head.get("javaClass") in (None, "")
    else:
        assert decoded["javaRef"] == 0 and head.get("javaClass") in (None, "")
    results[str(target)] = {
        "fixtureSHA256": fixture["zipSHA256"], "classSHA256": fixture["classSHA256"][fixture["entries"][0]],
        "world": world.name, "quantum": 4096, "epoch": head["epoch"],
        "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
        "machineRoot": head["machineRoot"], "checkpointSHA256": head["checkpointSHA256"],
        "checkpointBytes": len(checkpoint), "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
        "requestedAllocations": target, "ordinaryObjects": decoded["heapCounts"]["ordinaryObjects"],
        "ordinaryArrays": decoded["heapCounts"]["ordinaryArrays"],
        "ordinaryFields": decoded["heapCounts"]["ordinaryFields"],
        "arrayElements": decoded["heapCounts"]["arrayElements"],
        "objectRecords": len(objects), "lifecycle": head["lifecycle"],
        "javaKind": head["javaKind"], "javaRef": head["javaRef"],
        "oomClassIndexDerivedFromHeap": (fixture["bindingCount"] + pins["canonicalOOMBootstrapLeafIndex"])
        if target == 2049 else None,
    }
summary = {
    "stage": "MC-RANDOM-CLASS-P22-MAX-OBJECTS-2048",
    "capacityQuantum": 4096,
    "capacityQuantumCaveat": "Only high-count q4096 runs are made; q1/q7 are explicitly not claimed or attempted.",
    "bindingNamesIncludeClassSuffix": True,
    "canonicalOOMPolicy": "guest kind7; javaClass intentionally empty; derive java/lang/OutOfMemoryError from exception heap classIndex10",
    "results": results,
    "execution": "generated trusted fixtures, ordinary local 1B gas, no original classes/resources/world",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
