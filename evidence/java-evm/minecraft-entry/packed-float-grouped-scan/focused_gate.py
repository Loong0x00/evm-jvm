#!/usr/bin/env python3
"""Bounded generated-only grouped-scan acceptance and exact same-P18 MR01 comparison."""
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
stage = here.parent / "packed-float-bulk-u32"
root = here.parents[3]
if len(sys.argv) != 5:
    raise SystemExit("usage: focused_gate.py BUILD FIXTURES OUT RUN-ID")
build, fixtures, out = map(lambda x: Path(x).resolve(), sys.argv[1:4])
run_id = sys.argv[4]
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-packed-float-bulk-u32-build-")
assert fixtures.name.startswith("java-diff-mc-packed-float-bulk-u32-fixtures-")
assert out.name.startswith("java-diff-mc-packed-float-bulk-u32-focused-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert 0 < pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 97 and pins["rawLimits"] == [71, 471911]
assert pins["bootstrapRoot"] == "828af33f62f6e92513d9605bf832437e1330b4d325bb04f913b97fd6f20596bd"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic()
commands = []
canonical = []
results = {"candidate": {}, "sameP18BaselineMR01Equality": {}, "malformedAtomicRefusals": {}}

def fixture(label):
    return json.loads((fixtures / (label + ".json")).read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def report(world):
    return world.parent / "reports" / world.name

def words(value):
    return [str(word) for word in value["uint256Words"]]

def run(label, command, fixture_label=None, expect=0):
    env = {
        **os.environ,
        "TMPDIR": str(out / "tmp"),
        "NODE_PATH": str(node_modules),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GOPROXY": "off",
        "GOSUMDB": "off",
    }
    if fixture_label is not None:
        env["MC_ENTRY_BINDINGS"] = ",".join(fixture(fixture_label)["entries"])
    env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log")
    began = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, command)), cwd=root, env=env,
                              stdout=stream, stderr=subprocess.STDOUT,
                              timeout=1200)
    row = {"label": label, "command": list(map(str, command)),
           "exit": proc.returncode, "elapsedSeconds": time.monotonic() - began}
    commands.append(row)
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert proc.returncode == expect, (label, proc.returncode, log)
    return row

spec = importlib.util.spec_from_file_location("bulk_u32_checkpoint_diagnostic",
                                               here.parent / "parent-e23eea569" / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def terminal(world, raw_count):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == raw_count
    assert head["totalClassBytes"] <= 471911 and head.get("selectedResourceSize", 0) == 0
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert sha(checkpoint) == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + 97 and decoded["lifecycle"] == 2
    assert decoded["javaKind"] == decoded["javaRef"] == 0
    return head, checkpoint, decoded


def gas_summary(world):
    rows = [json.loads(path.read_text()) for path in
            sorted(report(world).glob("slice-*.json"))]
    head = json.loads((world / "durable-head.json").read_text())
    assert len(rows) == head["epoch"] and rows
    assert [int(row["epoch"]) for row in rows] == list(range(1, head["epoch"] + 1))
    for row in rows:
        assert row["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
        assert row["suppliedGas"] == 1000000000 and 0 < row["gasUsed"] <= 1000000000
        assert row["elapsedMS"] <= 30000
    return {"sliceCount": len(rows), "totalGas": sum(int(row["gasUsed"]) for row in rows),
            "maxSliceGas": max(int(row["gasUsed"]) for row in rows)}


def finish(variant, label, quantum, inspect=None):
    driver = build / ("baseline-driver" if variant == "baseline" else "candidate-driver")
    coord = build / variant / "coordinator/MCEntryCoordinator.json"
    engine = build / variant / "engine/MCEntryInterpreter.json"
    world = out / ("world-%s-%s-q%d" % (variant, label, quantum))
    args = [world, coord, engine, fixtures / (label + ".zip"), str(quantum)]
    run(variant + "-" + label + "-q%d-start" % quantum,
        [driver, "setup-chain", *args], label)
    run(variant + "-" + label + "-q%d-finish" % quantum,
        [driver, "finish", *args], label)
    run(variant + "-" + label + "-q%d-reopen" % quantum,
        [driver, "verify", *args], label)
    metadata = fixture(label)
    head, checkpoint, decoded = terminal(world, metadata["bindingCount"])
    if inspect:
        inspect(decoded, metadata["bindingCount"])
    gas = gas_summary(world)
    if variant == "candidate":
        canonical.append(world.name)
    return {
        "world": world.name,
        "quantum": quantum,
        "epoch": head["epoch"],
        "jvmSteps": head["jvmSteps"],
        "internalSteps": head["internalSteps"],
        "machineRoot": head["machineRoot"],
        "checkpointSHA256": head["checkpointSHA256"],
        "checkpointBytes": len(checkpoint),
        "mr01Bytes": len(checkpoint) - 280,
        "opaqueMR01SHA256": sha(checkpoint[280:]),
        "lifecycle": head["lifecycle"],
        "nextHandle": decoded["nextHandle"],
        "heapCounts": decoded["heapCounts"],
        **gas,
    }


def equivalent_candidate(label, inspect=None, quanta=(1, 7, 4096)):
    values = {}
    base = None
    for quantum in quanta:
        value = finish("candidate", label, quantum, inspect)
        values["direct" if quantum == 4096 else "q%d" % quantum] = value
        if base is None:
            base = value
        else:
            for key in ("machineRoot", "opaqueMR01SHA256", "mr01Bytes", "jvmSteps",
                        "internalSteps", "lifecycle", "nextHandle", "heapCounts"):
                assert value[key] == base[key], (label, key, value, base)
    results["candidate"][label] = values
    return values


def savings_boundary_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["rank"] == 1 and entry["metadata"] == "0x46"]
    tied = [entry for entry in arrays if entry["count"] == 1024 and entry["sparse"]]
    packed = [entry for entry in arrays if entry["count"] == 1024 and entry["packedFloat"]]
    assert len(tied) == len(packed) == 1
    assert tied[0]["sparseCount"] == 341 and packed[0]["cells"]
    assert all(int(cell["value"], 16) == 0x40000000 for cell in tied[0]["sparseCells"])
    assert all(int(cell, 16) == 0x3f800000 for cell in packed[0]["cells"][:342])
    assert all(int(cell, 16) == 0 for cell in packed[0]["cells"][342:])


def packed_oracle_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["rank"] == 1
              and entry["metadata"] == "0x46" and entry["count"] == 1024]
    assert len(arrays) == 1 and arrays[0]["packedFloat"]
    expected = [int(value, 16) for value in fixture("packed-array-oracle")["hostOutput"]]
    actual = [int(value, 16) for value in arrays[0]["cells"]]
    assert actual == expected and len(actual) == 1024
    assert sum(value != 0 for value in actual) == 348
    assert [actual[i] for i in (0, 500, 501, 502, 503, 504, 505)] == [
        0x7fc12345, 0x80000000, 0x7f800000, 0xff800000,
        0x00000001, 0x80000001, 0x7f7fffff,
    ]


def sparse_array_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["metadata"] != "0x0" and entry["rank"] == 1]
    large = [entry for entry in arrays if entry["count"] == 65536]
    assert len(large) == 3
    by_leaf = {entry["metadata"]: entry for entry in large if entry["sparse"]}
    assert set(by_leaf) == {"0x46", "0x49", "0x44"}
    assert by_leaf["0x46"]["sparseCount"] == 0
    assert [(cell["index"], int(cell["value"], 16)) for cell in by_leaf["0x49"]["sparseCells"]] == [(65535, 5)]
    assert [(cell["index"], int(cell["value"], 16)) for cell in by_leaf["0x44"]["sparseCells"]] == [
        (0, 0x3ff4000000000000), (32768, 0xc004000000000000),
        (65535, 0x400e000000000000),
    ]


def packed_tail_state(length):
    def inspect(decoded, raw):
        arrays = [entry for entry in decoded["heap"] if entry["metadata"] == "0x46"
                  and entry["rank"] == 1 and entry["count"] == length]
        assert len(arrays) == 1 and arrays[0]["packedFloat"]
        expected = [int(value, 16) for value in fixture("packed-array-oracle")["hostOutput"]]
        expected.extend([0] * (length - 1024))
        actual = [int(value, 16) for value in arrays[0]["cells"]]
        assert len(actual) == length and actual == expected
        assert sum(value != 0 for value in actual) == 348
        assert fixture("float-tail-%d" % length)["tailLength"] == length
    return inspect


def identity_state(decoded, raw):
    main = {entry["fieldIndex"]: int(entry["packedValue"], 16) & 0xffffffff
            for entry in next(row for row in decoded["initialization"] if row["classIndex"] == 0)["staticValues"]}
    assert list(main) == list(range(10))
    values = [main[i] for i in range(10)]
    assert values[0] == 0 and values[1] != 0 and values[1] == values[2]
    assert values[3] != 0 and values[4] != 0 and values[4] == values[5]
    assert values[6] != 0 and values[6] == values[7] and values[8] != 0 and values[9] == 7
    identities = (values[1], values[3], values[4], values[6], values[8])
    assert len(set(identities)) == len(identities)
    heap = {entry["handle"]: entry for entry in decoded["heap"]}
    assert set(identities) <= set(heap)
    def object_handle(handle, class_index):
        row = heap[handle]
        assert int(row["metadata"], 16) >> 255 == 1 and row["classIndex"] == class_index
    object_handle(values[1], raw)
    object_handle(values[3], raw)
    assert int(heap[values[4]]["metadata"], 16) >> 255 == 0
    assert heap[values[4]]["rank"] == 1 and heap[values[4]]["classIndex"] == 0
    object_handle(values[6], raw + 39)
    object_handle(values[8], 1)


def sin_bounded_state(decoded, raw):
    main = next(row for row in decoded["initialization"] if row["classIndex"] == 0)
    vectors = fixture("math-sin-bounded-edges")["sinVectors"]
    values = {row["fieldIndex"]: int(row["packedValue"], 16) for row in main["staticValues"]}
    count = len(vectors)
    assert main["state"] == 2 and set(values) == set(range(2 * count + 1))
    ordered = lambda bits: (~bits & 0xffffffffffffffff) if bits >> 63 else bits | (1 << 63)
    for i, vector in enumerate(vectors):
        actual = values[i] & 0xffffffffffffffff
        expected = int(vector["javaDoubleRaw"], 16)
        assert abs(ordered(actual) - ordered(expected)) <= 1
        actual_float = values[count + i] & 0xffffffff
        expected_float = int(vector["javaFloatRaw"], 16)
        assert actual_float == expected_float
    assert values[2 * count] & 0xffffffff == 7


# Candidate q1/q7/direct terminal reopens cover every packed tail and the
# packed resume fixture. Large sparse and crossover heap controls run direct-only
# here to keep the complete ordinary-1B gate under the explicit wall-time bound.
equivalent_candidate("packed-array-oracle", packed_oracle_state)
equivalent_candidate("sparse-array-stress", sparse_array_state, (4096,))
equivalent_candidate("array-savings-boundary", savings_boundary_state, (4096,))
for length in (1024, 1025, 1031):
    equivalent_candidate("float-tail-%d" % length, packed_tail_state(length))
equivalent_candidate("retained-integer", quanta=(4096,))
equivalent_candidate("identity-hash", identity_state, (4096,))
equivalent_candidate("math-sqrt-binary64", quanta=(4096,))
equivalent_candidate("math-sin-bounded-edges", sin_bounded_state, (4096,))
equivalent_candidate("count-71")

# Parent-independent exact pre-scan P18 baseline comparison for generated packed/sparse/crossover and
# tail cases. Compare the full opaque MR01 suffix at direct quantum; q1/q7/direct
# candidate results above prove the same candidate bytes across continuation modes.
for label in ("packed-array-oracle", "sparse-array-stress", "array-savings-boundary",
              "float-tail-1024", "float-tail-1025", "float-tail-1031"):
    quantum = 4096
    candidate = results["candidate"][label]["direct"]
    inspect = (packed_oracle_state if label in ("packed-array-oracle", "float-tail-1024")
               else sparse_array_state if label == "sparse-array-stress"
               else savings_boundary_state if label == "array-savings-boundary"
               else packed_tail_state(int(label.rsplit("-", 1)[1])))
    reference = finish("baseline", label, quantum, inspect)
    candidate_cp = (out / candidate["world"] / "checkpoints" /
                    (candidate["checkpointSHA256"] + ".bin")).read_bytes()
    reference_cp = (out / reference["world"] / "checkpoints" /
                    (reference["checkpointSHA256"] + ".bin")).read_bytes()
    candidate_mr01 = candidate_cp[280:]
    reference_mr01 = reference_cp[280:]
    assert candidate_mr01 == reference_mr01, (label, quantum)
    results["sameP18BaselineMR01Equality"][label] = {
        "mr01Bytes": len(candidate_mr01),
        "candidateMR01SHA256": sha(candidate_mr01),
        "baselineMR01SHA256": sha(reference_mr01),
        "byteEquality": True,
        "candidateMachineRoot": candidate["machineRoot"],
        "baselineMachineRoot": reference["machineRoot"],
        "candidateGas": candidate["totalGas"],
        "baselineGas": reference["totalGas"],
        "gasSaved": reference["totalGas"] - candidate["totalGas"],
        "candidateSlices": candidate["sliceCount"],
        "baselineSlices": reference["sliceCount"],
    }

# At least the packed and crossover workload totals must demonstrate a strict
# ordinary-gas reduction; sparse remains the unchanged old wire control.
for label in ("packed-array-oracle", "array-savings-boundary"):
    assert results["sameP18BaselineMR01Equality"][label]["gasSaved"] > 0

# Re-root malformed MR01 checkpoints so failures reach EVM validation, then
# verify exact typed error and atomic root/Head/log preservation.
def rehash_checkpoint(path):
    helper = out / "tmp/rehash-checkpoint.js"
    helper.write_text(r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const p=process.argv[2],b=fs.readFileSync(p),schema=b.readUInt32BE(8),machine=b.subarray(280);
const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const domain=Buffer.from(keccak256("JVMEVM:MC-RANDOM-CLASS-P18:MACHINE:1"),"hex");
const root=keccak256(Buffer.concat([domain,word(schema),b.subarray(116,148),b.subarray(148,180),Buffer.from(keccak256(machine),"hex"),b.subarray(244,276)]));
b.write(root,180,"hex");b.writeUInt32BE(b.length-280,276);fs.writeFileSync(p,b);
''')
    env = {**os.environ, "NODE_PATH": str(node_modules)}
    subprocess.run(["node", helper, path], cwd=root, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def malformed_refusal(label, fixture_label, mutate, expected_code, packed=True, base_quantum=1):
    world = out / ("world-candidate-%s-q%d" % (fixture_label, base_quantum))
    head = json.loads((world / "durable-head.json").read_text())
    original = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    decoded = diagnostic.inspect(original)
    arrays = [row for row in decoded["heap"] if row["count"] == (1024 if packed else 65536)
              and (row["packedFloat"] if packed else row["sparse"])]
    assert arrays
    blob = bytearray(original)
    mutate(blob, arrays if not packed else arrays[0])
    path = out / "tmp" / (label + ".bin")
    path.write_bytes(blob)
    rehash_checkpoint(path)
    driver = build / "candidate-driver"
    coord = build / "candidate/coordinator/MCEntryCoordinator.json"
    engine = build / "candidate/engine/MCEntryInterpreter.json"
    run(label, [driver, "sparse-malformed", world, coord, engine,
                fixtures / (fixture_label + ".zip"), "1", path,
                str(expected_code), label], fixture_label)
    receipt = json.loads((report(world) / (label + ".json")).read_text())
    assert receipt["error"] == "LC0StateError" and receipt["code"] == expected_code
    assert receipt["rootUnchanged"] and receipt["headUnchanged"] and receipt["logsUnchanged"]
    results["malformedAtomicRefusals"][label] = {
        "code": receipt["code"], "rootUnchanged": receipt["rootUnchanged"],
        "headUnchanged": receipt["headUnchanged"], "logsUnchanged": receipt["logsUnchanged"],
    }
    return receipt


def both_flags(blob, row):
    at = row["countOffset"]
    blob[at:at + 4] = (row["wireCount"] | 0x80000000).to_bytes(4, "big")

def packed_truncation(blob, row):
    blob[row["countOffset"]:row["countOffset"] + 4] = (0x40000000 | 65536).to_bytes(4, "big")

def packed_high_bits_dense(blob, row):
    start, end, count = row["recordStart"], row["recordEnd"], row["count"]
    values = [int(cell["value"], 16) for cell in row["packedCells"]]
    payload = bytearray()
    for i, value in enumerate(values):
        if i == 0: value |= 1 << 32
        payload.extend(value.to_bytes(8, "big"))
    blob[start:end] = blob[start:start + 39] + count.to_bytes(4, "big") + payload

def packed_noncanonical(blob, row):
    for cell in row["packedCells"][1:]:
        at = cell["valueOffset"]
        blob[at:at + 4] = bytes(4)

def sparse_truncation(blob, rows):
    row = rows[0]
    blob[row["sparseCountOffset"]:row["sparseCountOffset"] + 4] = (1000).to_bytes(4, "big")

def sparse_noncanonical_dense(blob, rows):
    row = next(item for item in rows if item["sparseCount"] == 0)
    start, end, length = row["recordStart"], row["recordEnd"], row["count"]
    blob[start:end] = blob[start:start + 39] + length.to_bytes(4, "big") + bytes(length * 8)

malformed_refusal("packed-truncated-refusal", "packed-array-oracle", packed_truncation, 2)
malformed_refusal("packed-both-flags-refusal", "packed-array-oracle", both_flags, 6)
malformed_refusal("packed-high-bits-refusal", "packed-array-oracle", packed_high_bits_dense, 6)
malformed_refusal("packed-noncanonical-refusal", "packed-array-oracle", packed_noncanonical, 6)
malformed_refusal("sparse-truncated-refusal", "sparse-array-stress", sparse_truncation, 2,
                  packed=False, base_quantum=4096)
malformed_refusal("sparse-noncanonical-refusal", "sparse-array-stress", sparse_noncanonical_dense, 3,
                  packed=False, base_quantum=4096)

# A successful q1 resume must decode a previously committed packed MR01 record.
def packed_resume_receipt():
    world = out / "world-candidate-packed-array-oracle-q1"
    head = json.loads((world / "durable-head.json").read_text())
    receipts = report(world)
    for path in sorted(receipts.glob("slice-*.json")):
        row = json.loads(path.read_text())
        epoch = int(row["epoch"])
        checkpoint_path = world / "checkpoints" / (row["checkpointSHA256"] + ".bin")
        if not checkpoint_path.is_file() or epoch >= int(head["epoch"]):
            continue
        state = diagnostic.inspect(checkpoint_path.read_bytes())
        packed = [entry for entry in state["heap"] if entry["packedFloat"] and entry["count"] == 1024]
        if not packed:
            continue
        child = json.loads((receipts / ("slice-%020d.json" % (epoch + 1))).read_text())
        assert child["method"] == "resumeMain" and child["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
        assert child["suppliedGas"] == 1000000000 and child["gasUsed"] <= 1000000000
        return {"parentEpoch": epoch, "parentMR01SHA256": sha(checkpoint_path.read_bytes()[280:]),
                "childEpoch": child["epoch"], "childGas": child["gasUsed"],
                "packedArrays": len(packed)}
    raise AssertionError("no successful q1 resume decoded a packed checkpoint")

results["packedResume"] = packed_resume_receipt()

# Exact 471911-byte aggregate witness is generated input only. The 1B LOCAL
# probe retains its expected atomic engine-call refusal after all DI0 reads.
large_label = "count-71-471911"
large = fixture(large_label)
assert large["bindingCount"] == 71 and large["totalClassBytes"] == 471911
world = out / "world-candidate-byte-471911"
run("candidate-byte-471911", [build / "candidate-driver", "setup-chain", world,
    build / "candidate/coordinator/MCEntryCoordinator.json",
    build / "candidate/engine/MCEntryInterpreter.json",
    fixtures / (large_label + ".zip"), "4096"], large_label)
refusal = json.loads((report(world) / "start-refusal.json").read_text())
assert sum(refusal["actualDI0ReadSizes"]) == 471911
assert refusal["selector"] == "0x" and refusal["checkpointBytes"] == 0
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
assert refusal["suppliedGas"] == 1000000000 and refusal["gas"] <= 1000000000
results["raw71-byte471911"] = {
    "bindingCount": 71, "classBytesRead": sum(refusal["actualDI0ReadSizes"]),
    "expectedLocal1BAtomicRefusal": True, "rootUnchanged": refusal["rootUnchanged"],
    "checkpointBytes": refusal["checkpointBytes"],
}

# Independently verify every candidate public receipt/ABI/event/counter chain.
run("canonical-receipts", ["node", here.parent / "parent-e23eea569" / "verify_receipts.js", build, out,
    "1", *canonical], "retained-integer")
canonical_data = json.loads((out / "logs/canonical-receipts.log").read_text())
results["canonicalReceipts"] = canonical_data
elapsed = time.monotonic() - started
assert elapsed <= 1200, elapsed
summary = {
    "profile": "MC-RANDOM-CLASS-P18-PACKED-FLOAT-GROUPED-SCAN",
    "generatedOnly": True,
    "ordinaryExternalGas": 1000000000,
    "wholeGateSeconds": elapsed,
    "bootstrapCount": 97,
    "bootstrapRoot": pins["bootstrapRoot"],
    "engineBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": pins["runtimeCap"],
    "tailLengths": [1024, 1025, 1031],
    "rawLimits": [71, 471911],
    "results": results,
    "commands": commands,
    "limitations": "Generated fixture-only q1/q7/direct/reopen, packed/sparse/crossover byte-for-byte MR01 comparison to the exact pre-scan P18 baseline, malformed atomic refusal, and gas measurement. No original Java input or Minecraft replay.",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({
    "result": "PASS", "generatedOnly": True, "wholeGateSeconds": elapsed,
    "candidateCanonicalReceipts": canonical_data["verifiedReceipts"],
    "engineBytes": pins["engine"]["bytes"], "runtimeCapBytes": pins["runtimeCap"],
    "bootstrapRoot": pins["bootstrapRoot"],
    "candidateWorlds": len(canonical),
    "sameP18BaselineComparisons": len(results["sameP18BaselineMR01Equality"]),
    "gasSaved": {label: values["gasSaved"]
                  for label, values in results["sameP18BaselineMR01Equality"].items()},
}, indent=2))
