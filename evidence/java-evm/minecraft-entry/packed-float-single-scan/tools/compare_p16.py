#!/usr/bin/env python3
"""Compare generated MR01 payloads against freshly compiled accepted P16."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build, fixtures, candidate_gate = map(Path, sys.argv[1:4])
build = build.resolve(); fixtures = fixtures.resolve(); candidate_gate = candidate_gate.resolve()
mode = sys.argv[4] if len(sys.argv) > 4 else "all-quanta"
assert mode in ("all-quanta", "direct-only")
quanta = (1, 7, 4096) if mode == "all-quanta" else (4096,)
assert build.parent == fixtures.parent == candidate_gate.parent == root / "build"
assert build.name.startswith("java-diff-mc-packed-float-single-scan-build-")
assert fixtures.name.startswith("java-diff-mc-packed-float-single-scan-fixtures-")
assert candidate_gate.name.startswith("java-diff-mc-packed-float-single-scan-gate-")
run_id = candidate_gate.name.rsplit("-", 1)[-1]
archive = stage / ("results/opaque-equivalence-gate-" + run_id + ("-direct" if mode == "direct-only" else ""))
assert not archive.exists(), "durable comparison evidence is append-only"
(archive / "baseline").mkdir(parents=True)
(archive / "candidate").mkdir()
out = build.parent / ("java-diff-mc-packed-float-single-scan-baseline-replay-" + run_id + ("-direct" if mode == "direct-only" else ""))
assert not out.exists()
out.mkdir(); (out / "tmp").mkdir()
env = {
    **os.environ,
    "TMPDIR": str(out / "tmp"),
    "NODE_PATH": str(root / "jvmevm/runtime/node_modules"),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
}
node_keccak = r'''const fs=require('fs'),{keccak256}=require('js-sha3');
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(rows.map(x=>keccak256(Buffer.from(x,'hex')))));'''

def invoke(label, command, fixture):
    local_env = dict(env)
    local_env["MC_ENTRY_BINDINGS"] = ",".join(fixture["entries"])
    local_env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / (label + ".log")
    with log.open("w") as stream:
        subprocess.run(list(map(str, command)), cwd=root, env=local_env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1200)


def world_payload(world):
    head = json.loads((world / "durable-head.json").read_text())
    checkpoint_path = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    checkpoint = checkpoint_path.read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    assert len(checkpoint) >= 280 and checkpoint[280:284] == b"MR01"
    machine_length = int.from_bytes(checkpoint[276:280], "big")
    machine = checkpoint[280:]
    assert len(machine) == machine_length
    return head, checkpoint, machine


started = time.monotonic()
comparison_rows = []
for label in ("packed-array-oracle", "array-savings-boundary", "sparse-array-stress"):
    fixture = json.loads((fixtures / (label + ".json")).read_text())
    zip_path = fixtures / (label + ".zip")
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == fixture["zipSHA256"]
    for quantum in quanta:
        tag = "direct" if quantum == 4096 else "q" + str(quantum)
        candidate_world = candidate_gate / ("world-" + label + "-q" + str(quantum))
        assert candidate_world.is_dir(), (label, quantum, candidate_world)
        baseline_world = out / ("world-" + label + "-q" + str(quantum))
        baseline_driver = build / "baseline-driver"
        coord = build / "baseline/coordinator/MCEntryCoordinator.json"
        engine = build / "baseline/engine/MCEntryInterpreter.json"
        args = [baseline_world, coord, engine, zip_path, str(quantum)]
        invoke("baseline-" + label + "-" + tag + "-setup",
               [baseline_driver, "setup-chain", *args], fixture)
        invoke("baseline-" + label + "-" + tag + "-finish",
               [baseline_driver, "finish", *args], fixture)
        invoke("baseline-" + label + "-" + tag + "-reopen",
               [baseline_driver, "verify", *args], fixture)

        base_head, base_checkpoint, base_machine = world_payload(baseline_world)
        cand_head, cand_checkpoint, cand_machine = world_payload(candidate_world)
        for key in ("lifecycle", "outcome", "result", "javaKind", "javaRef",
                    "jvmSteps", "internalSteps", "artifactRoot", "vfsRoot"):
            assert base_head[key] == cand_head[key], (label, quantum, key,
                                                      base_head.get(key), cand_head.get(key))
        assert base_machine == cand_machine, (label, quantum, "MR01 payload bytes differ")
        hashes = json.loads(subprocess.run(
            ["node", "-e", node_keccak], cwd=root, env=env,
            input=json.dumps([base_machine.hex(), cand_machine.hex()]),
            text=True, capture_output=True, check=True,
        ).stdout)
        assert hashes[0] == hashes[1]
        filename = label + "-" + tag + ".mr01.bin"
        (archive / "baseline" / filename).write_bytes(base_machine)
        (archive / "candidate" / filename).write_bytes(cand_machine)
        row = {
            "fixture": label,
            "fixtureZipSHA256": fixture["zipSHA256"],
            "quantum": quantum,
            "lifecycle": cand_head["lifecycle"],
            "jvmSteps": cand_head["jvmSteps"],
            "internalSteps": cand_head["internalSteps"],
            "baselineMachineRoot": base_head["machineRoot"],
            "candidateMachineRoot": cand_head["machineRoot"],
            "MR01Bytes": len(cand_machine),
            "MR01SHA256": hashlib.sha256(cand_machine).hexdigest(),
            "MR01Keccak256": hashes[0],
            "MR01ByteIdenticalToAcceptedP16": True,
            "baselineOuterCheckpointSHA256": hashlib.sha256(base_checkpoint).hexdigest(),
            "candidateOuterCheckpointSHA256": hashlib.sha256(cand_checkpoint).hexdigest(),
            "outerCheckpointByteEqual": base_checkpoint == cand_checkpoint,
        }
        comparison_rows.append(row)

report = {
    "result": "PASS",
    "generatedOnly": True,
    "baseline": "fresh compile of accepted P16 source parent-50541377b",
    "candidateSourceSHA256": json.loads((stage / "source-invariants.json").read_text())["candidateSourceSHA256"],
    "bootstrapRoot": "8c5bc495513b12e7ee40f71f447c5f8f894d49ec9cf318d2744143f1d20ff310",
    "fixtures": ["packed-array-oracle", "array-savings-boundary (341 tie / 342 packed)", "sparse-array-stress (old sparse floats)"],
    "quanta": list(quanta),
    "comparisonMode": mode,
    "comparisons": comparison_rows,
    "allMR01PayloadBytesAndSHA256KeccakMatch": True,
    "note": "The runtime hash is committed in configRoot and the checkpoint envelope, so configRoot, machineRoot and outer checkpoint SHA256 may differ. Equality is asserted over the complete opaque MR01 payload, its SHA256/Keccak, artifactRoot and vfsRoot.",
    "elapsedSeconds": time.monotonic() - started,
}
(archive / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({
    "result": report["result"],
    "comparisons": len(comparison_rows),
    "comparisonMode": mode,
    "allMR01PayloadBytesAndSHA256KeccakMatch": True,
    "elapsedSeconds": report["elapsedSeconds"],
    "archive": str(archive.relative_to(root)),
}, indent=2))
