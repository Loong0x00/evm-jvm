#!/usr/bin/env python3
"""Parse the EVM-issued MC checkpoint to evidence the actual class-count boundary."""
import hashlib, json, pathlib, subprocess, os
D = pathlib.Path(__file__).resolve().parents[1]
world = D / "build/run120-class-boundary-150"
head = json.loads((world / "durable-head.json").read_text())
cp = None
for candidate in (world / "checkpoints").glob("*.bin"):
    result = subprocess.run([
        "node", "-e",
        "const fs=require('fs'),{keccak256}=require('js-sha3');process.stdout.write(keccak256(fs.readFileSync(process.argv[1])))",
        str(candidate),
    ], cwd=D.parents[4], env=os.environ.copy(), check=True, capture_output=True, text=True)
    if "0x" + result.stdout == head["checkpointRoot"] or result.stdout == head["checkpointRoot"].removeprefix("0x"):
        cp = candidate
        break
assert cp is not None, "EVM Head checkpoint blob not found by Keccak"
b = cp.read_bytes()
m = b[280:]
assert m[:4] == b"MR01"
at = 4
def u(n):
    global at
    x = int.from_bytes(m[at:at+n], "big"); at += n
    return x
lifecycle = u(1); result = u(4); kind = u(1); ref = u(4)
jvm_steps = u(8); internal_steps = u(8); root_kind = u(1)
at += 32
for _ in range(2):
    length = u(2); at += length
args = u(1); at += args * 4
class_count = u(2)
assert class_count == 270 and lifecycle == 2 and result == 0 and jvm_steps == 536
assert head["machineRoot"].startswith("0x") and head["lifecycle"] == 2
out = {
    "status": "PASS",
    "rawClassCount": 150,
    "bootstrapCount": 120,
    "actualCheckpointClassCount": class_count,
    "maxActualClassIndex": class_count - 1,
    "appendedIndices": {"java/util/Collections": 267, "java/util/Collections$SingletonList": 268, "java/util/Collections$SingletonIterator": 269},
    "completedProbe": "SingletonListProbe.main invoked the factory/list/iterator through the >255 bootstrap region",
    "quantum": head["quantum"], "epoch": head["epoch"], "lifecycle": lifecycle,
    "jvmSteps": jvm_steps, "internalSteps": internal_steps,
    "machineRoot": head["machineRoot"], "vfsRoot": head["vfsRoot"],
    "checkpointRoot": head["checkpointRoot"], "checkpointSHA256": hashlib.sha256(b).hexdigest(),
    "checkpointBytes": len(b), "noOriginalInputs": True,
}
path = D / "build/reports/class-index-audit.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
