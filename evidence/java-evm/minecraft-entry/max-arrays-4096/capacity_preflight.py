#!/usr/bin/env python3
"""q4096 ordinary-1B generated array-capacity preflight; no original MC inputs."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
build, fixtures, out = (Path(p).resolve() for p in sys.argv[1:4])
assert build.parent == fixtures.parent == out.parent == ROOT / "build"
assert build.name.startswith("java-diff-mc-max-arrays-4096-build-")
assert fixtures.name.startswith("java-diff-mc-max-arrays-4096-fixtures-")
assert out.name.startswith("java-diff-mc-max-arrays-4096-preflight-") and not out.exists()
node_modules = ROOT / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["maxArrays"] == 4096 and pins["maxObjects"] == 2048 and pins["maxHandles"] == 6401
assert pins["canonicalOOMBootstrapLeafIndex"] == 9
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
env0 = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules),
        "PYTHONDONTWRITEBYTECODE": "1", "GOPROXY": "off", "GOSUMDB": "off"}
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
diagnostic_spec = spec.spec_from_file_location("max_arrays_4096_checkpoint_diagnostic", HERE / "checkpoint_diagnostic.py")
diagnostic = spec.module_from_spec(diagnostic_spec); diagnostic_spec.loader.exec_module(diagnostic)
results = {}
canonical = []


def run(label, argv, fixture):
    env = dict(env0, MC_ENTRY_BINDINGS=",".join(fixture["entries"]))
    log = out / "logs" / (label + ".log"); start = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, argv)), "exit": process.returncode,
           "elapsedSeconds": time.monotonic() - start}
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert process.returncode == 0, (label, process.returncode, log)


for target in (2048, 2049, 4096, 4097):
    label = "array-capacity-%d" % target
    fixture = json.loads((fixtures / (label + ".json")).read_text())
    assert fixture["entries"] == ["generated/ArrayCapacity%d.class" % target]
    assert fixture["requestedOrdinaryArrays"] == target
    assert fixture["explicitAllocations"] == target - 1
    world = out / ("world-" + label + "-q4096")
    archive = fixtures / (label + ".zip")
    args = [world, coordinator, engine, archive, "4096"]
    for phase, argv in (("start", [driver, "setup-chain", *args]),
                        ("finish", [driver, "finish", *args]),
                        ("reopen", [driver, "verify", *args])):
        run(label + "-" + phase, argv, fixture)
    head = json.loads((world / "durable-head.json").read_text())
    checkpoint_path = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    checkpoint = checkpoint_path.read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    expect_oom = target == 4097
    expected = min(target, 4096)
    assert head["quantum"] == 4096 and head["epoch"] > 0
    assert head["lifecycle"] == head["outcome"] == (3 if expect_oom else 2)
    assert head["javaKind"] == (7 if expect_oom else 0)
    assert decoded["lifecycle"] == head["lifecycle"] and decoded["javaKind"] == head["javaKind"]
    counts = decoded["heapCounts"]
    assert counts["ordinaryArrays"] == expected, (target, counts)
    assert counts["ordinaryObjects"] == counts["ordinaryFields"] == counts["arrayElements"] == 0
    arrays = [row for row in decoded["heap"] if int(row["metadata"], 16) >> 255 == 0]
    assert len(arrays) == expected, (target, len(arrays), counts)
    if expect_oom:
        assert decoded["javaRef"] != 0 and head.get("javaClass") in (None, "")
        oom = next(row for row in decoded["heap"] if row["handle"] == decoded["javaRef"])
        assert int(oom["metadata"], 16) >> 255 == 1 and oom["rank"] == 0
        expected_class_index = fixture["bindingCount"] + pins["canonicalOOMBootstrapLeafIndex"]
        assert oom["classIndex"] == expected_class_index
        exception = {"heapHandle": oom["handle"], "classIndex": oom["classIndex"],
                     "exceptionObjects": counts["exceptionObjects"], "exceptionFields": counts["exceptionFields"],
                     "javaClassEmptyByContract": True}
    else:
        assert decoded["javaRef"] == 0 and head.get("javaClass") in (None, "")
        exception = None
    canonical.append(world.name)
    results[str(target)] = {
        "fixtureSHA256": fixture["zipSHA256"],
        "classSHA256": fixture["classSHA256"][fixture["entries"][0]],
        "entryNameIncludesClassSuffix": fixture["entries"][0].endswith(".class"),
        "world": world.name, "quantum": 4096, "epoch": head["epoch"],
        "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
        "machineRoot": head["machineRoot"], "checkpointSHA256": head["checkpointSHA256"],
        "checkpointBytes": len(checkpoint), "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
        "requestedTotalArrays": target, "ordinaryArrays": counts["ordinaryArrays"],
        "ordinaryObjects": counts["ordinaryObjects"], "arrayElements": counts["arrayElements"],
        "arrayRecords": len(arrays), "nextHandle": decoded["nextHandle"],
        "lifecycle": head["lifecycle"], "javaKind": head["javaKind"],
        "javaRef": head["javaRef"], "typedOOM": exception,
    }
with (out / "logs/canonical-receipts.log").open("w") as stream:
    subprocess.run(["node", HERE / "verify_receipts.js", build, out, "1", *canonical],
                   cwd=ROOT, env=env0, stdout=stream, stderr=subprocess.STDOUT,
                   check=True, timeout=1200)
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
assert canonical_receipts["verifiedReceipts"] > 0

summary = {
    "profile": "MC-RANDOM-CLASS-P22-MAX-ARRAYS-4096-worker-candidate",
    "generatedOnly": True, "ordinaryGasCap": 1000000000, "quantum": 4096,
    "bootstrapCount": 97, "bootstrapRoot": pins["bootstrapRoot"],
    "maxArrays": pins["maxArrays"], "maxObjects": pins["maxObjects"],
    "maxHandles": pins["maxHandles"], "runtimeBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": pins["runtimeCap"],
    "targetsIncludeImplicitMainStringArray": True,
    "bindingNamesIncludeClassSuffix": True,
    "typedOOMPolicy": "kind7; derive java/lang/OutOfMemoryError from authenticated heap object classIndex=bindingCount+9; javaClass intentionally empty",
    "canonicalReceipts": canonical_receipts,
    "results": results,
    "execution": "generated ordinary-1B public driver; exact heap counters and checkpoint reopen; no original Minecraft inputs",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
