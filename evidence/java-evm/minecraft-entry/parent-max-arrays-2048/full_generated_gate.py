#!/usr/bin/env python3
"""Generated sparse-array checkpoint gate plus retained Random/raw71 controls."""
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
stage = here
root = here.parents[3]
build, fixtures, out = map(Path, sys.argv[1:4])
build = build.resolve(); fixtures = fixtures.resolve(); out = out.resolve()
assert build.parent == fixtures.parent == out.parent == root / "build"
assert build.name.startswith("java-diff-mc-max-arrays-2048-build-")
assert fixtures.name.startswith("java-diff-mc-max-arrays-2048-fixtures-")
assert out.name.startswith("java-diff-mc-max-arrays-2048-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 97 and pins["rawLimits"] == [71, 471911]
assert pins["diagnosticClassBound"] == 168 and pins["globalNativeBindings"] == 21 and pins["stringLocalBinding"] == 12
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["bootstrapRoot"] == "845e0c87e52b163b246228ebf4400237953dfac4aa70d5b3fd4217c1dca7dee4"
assert pins["math"]["keccak256"] == pins["expectedMathKeccak256"]
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic(); commands = []; results = {}; canonical = []
model = subprocess.run([sys.executable, here / "full_verify_q120.py"], cwd=root, text=True,
                       capture_output=True, check=True, timeout=120)
q120_report = json.loads(model.stdout)
assert q120_report["gridInputs"] == 65536 and q120_report["maxBinary64ULPDistanceFromJava8"] <= 1
assert q120_report["floatCastBitMismatchCount"] == 0
(out / "q120-test-only-model.json").write_text(json.dumps(q120_report, indent=2) + "\n")


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

# Binding18 retains binary64 sqrt. Binding19 executes the measured nonzero argument,
# signed zeros, subnormal/normal boundaries, near-pi/2/pi/two-pi values and mirrored
# samples from the generated grid. Every EVM output is compared with Java8 raw bits;
# double distance is <=1 ULP, while every selected float cast must be bit-exact.
q_equivalent("math-sqrt-binary64")

def sin_bounded_state(decoded, raw, label):
    main = next(row for row in decoded["initialization"] if row["classIndex"] == 0)
    vectors = fixture(label)["sinVectors"]
    values = {row["fieldIndex"]: int(row["packedValue"], 16) for row in main["staticValues"]}
    count = len(vectors)
    assert main["state"] == 2 and set(values) == set(range(2 * count + 1))
    ordered = lambda bits: (~bits & 0xffffffffffffffff) if bits >> 63 else bits | (1 << 63)
    for i, vector in enumerate(vectors):
        actual = values[i] & 0xffffffffffffffff
        expected = int(vector["javaDoubleRaw"], 16)
        distance = abs(ordered(actual) - ordered(expected))
        assert distance <= 1, (label, vector["name"], hex(actual), hex(expected), distance)
        actual_float = values[count + i] & 0xffffffff
        expected_float = int(vector["javaFloatRaw"], 16)
        assert actual_float == expected_float, (label, vector["name"], hex(actual_float), hex(expected_float))
        if vector["name"] in ("positive-zero", "negative-zero"):
            assert actual == expected
        if vector["name"] == "measured-positive":
            assert int(vector["inputRaw"], 16) == 0x3f1921fb54442d18
            assert actual == 0x3f1921fb539ecf31 and actual_float == 0x38c90fdb
    assert values[2 * count] & 0xffffffff == 7
    assert fixture(label)["java8HostOracle"] is True

q_equivalent("math-sin-bounded-edges", inspect=lambda decoded, raw: sin_bounded_state(decoded, raw, "math-sin-bounded-edges"))
q_equivalent("math-sin-bounded-grid", inspect=lambda decoded, raw: sin_bounded_state(decoded, raw, "math-sin-bounded-grid"))


def random_construction_state(decoded, raw):
    main = next(row for row in decoded["initialization"] if row["classIndex"] == 0)
    assert len(main["staticValues"]) == 1
    result = main["staticValues"][0]
    assert result["fieldIndex"] == 0 and (int(result["packedValue"], 16) & 0xffffffff) == 7
    instances = [entry for entry in decoded["heap"]
                 if int(entry["metadata"], 16) >> 255 == 1 and entry["classIndex"] == raw + 96]
    assert len(instances) == 2, instances
    assert instances[0]["handle"] != instances[1]["handle"]


def sparse_array_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["metadata"] != "0x0" and entry["rank"] == 1]
    large = [entry for entry in arrays if entry["count"] == 65536]
    assert len(large) == 3, large
    by_leaf = {entry["metadata"]: entry for entry in large if entry["sparse"]}
    assert set(by_leaf) == {"0x46", "0x49", "0x44"}, by_leaf
    assert by_leaf["0x46"]["sparseCount"] == 0 and by_leaf["0x46"]["sparseCells"] == []
    assert [(cell["index"], int(cell["value"], 16) & 0xffffffff) for cell in by_leaf["0x49"]["sparseCells"]] == [(65535, 5)]
    assert [(cell["index"], int(cell["value"], 16)) for cell in by_leaf["0x44"]["sparseCells"]] == [(0, 0x3ff4000000000000), (32768, 0xc004000000000000), (65535, 0x400e000000000000)]
    small = [entry for entry in arrays if entry["count"] == 2 and entry["metadata"] == "0x46"]
    assert len(small) == 1 and not small[0]["sparse"] and len(small[0]["cells"]) == 2
    refs = [entry for entry in arrays if entry["count"] == 1024]
    assert len(refs) == 1 and not refs[0]["sparse"] and len(refs[0]["cells"]) == 1024
    assert int(refs[0]["cells"][511], 16) != 0


q_equivalent("random-construction", inspect=random_construction_state)
q_equivalent("sparse-array-stress", inspect=sparse_array_state)


def savings_boundary_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["rank"] == 1 and entry["metadata"] == "0x46"]
    tied = [entry for entry in arrays if entry["count"] == 1024 and entry["sparse"]]
    packed = [entry for entry in arrays if entry["count"] == 1024 and entry["packedFloat"]]
    assert len(tied) == 1 and len(packed) == 1, (len(tied), len(packed))
    assert tied[0]["sparseCount"] == 341 and len(tied[0]["sparseCells"]) == 341
    assert len(packed[0]["cells"]) == 1024
    assert all(int(cell["value"], 16) == 0x40000000 for cell in tied[0]["sparseCells"])
    assert all(int(cell, 16) == 0x3f800000 for cell in packed[0]["cells"][:342])
    assert all(int(cell, 16) == 0 for cell in packed[0]["cells"][342:])


def packed_float_oracle_state(decoded, raw):
    arrays = [entry for entry in decoded["heap"] if entry["rank"] == 1
              and entry["metadata"] == "0x46" and entry["count"] == 1024]
    assert len(arrays) == 1 and arrays[0]["packedFloat"]
    expected = [int(value, 16) for value in fixture("packed-array-oracle")["hostOutput"]]
    actual = [int(value, 16) for value in arrays[0]["cells"]]
    assert len(expected) == len(actual) == 1024
    assert actual == expected, "entire eager guest float heap differs from Java-8 raw-bit oracle"
    assert sum(value != 0 for value in actual) == 348
    assert [actual[i] for i in (0, 500, 501, 502, 503, 504, 505)] == [
        0x7fc12345, 0x80000000, 0x7f800000, 0xff800000,
        0x00000001, 0x80000001, 0x7f7fffff,
    ]
    main = next(row for row in decoded["initialization"] if row["classIndex"] == 0)
    fields = {row["fieldIndex"]: int(row["packedValue"], 16) for row in main["staticValues"]}
    assert (fields[0] & 0xffffffff) == 7


# The strict equality crossover and a repeated-density, Java-8-oracle float array.
boundary = q_equivalent("array-savings-boundary", inspect=savings_boundary_state)
q_equivalent("packed-array-oracle", inspect=packed_float_oracle_state)


def q1_sparse_resume_receipt():
    world = out / "world-sparse-array-stress-q1"
    head = json.loads((world / "durable-head.json").read_text())
    reports = report(world)
    checkpoints = world / "checkpoints"
    candidate = None
    for receipt_path in sorted(reports.glob("slice-*.json")):
        receipt = json.loads(receipt_path.read_text())
        epoch = int(receipt["epoch"])
        digest = receipt["checkpointSHA256"]
        cp_path = checkpoints / (digest + ".bin")
        if not cp_path.is_file():
            continue
        state = diagnostic.inspect(cp_path.read_bytes())
        present = [item for item in state["heap"] if item["count"] == 65536 and item["sparse"]]
        if not present or epoch >= int(head["epoch"]):
            continue
        child_path = reports / ("slice-%020d.json" % (epoch + 1))
        child = json.loads(child_path.read_text())
        assert child["method"] == "resumeMain"
        assert child["suppliedGas"] == 1000000000 and child["executionBudget"] == "LOCAL1B-USER-AUTHORIZED" and child["gasUsed"] <= 1000000000
        assert child["elapsedMS"] <= 30000, child
        candidate = {"parentEpoch": epoch, "parentCheckpointSHA256": digest,
                     "parentCheckpointBytes": len(cp_path.read_bytes()),
                     "largePrimitiveArrays": len(present), "childEpoch": epoch + 1,
                     "childGasUsed": child["gasUsed"], "childElapsedMS": child["elapsedMS"],
                     "childCheckpointSHA256": child["checkpointSHA256"]}
        break
    assert candidate is not None, "q1 never committed a resume from a successful 65536-cell sparse-array checkpoint"
    return candidate


q1_commit = q1_sparse_resume_receipt()
results["q1-sparse-resume-from-successful-large-array-head"] = q1_commit


def q1_packed_resume_receipt():
    world = out / "world-packed-array-oracle-q1"
    head = json.loads((world / "durable-head.json").read_text())
    reports = report(world)
    checkpoints = world / "checkpoints"
    candidate = None
    for receipt_path in sorted(reports.glob("slice-*.json")):
        receipt = json.loads(receipt_path.read_text())
        epoch = int(receipt["epoch"])
        digest = receipt["checkpointSHA256"]
        cp_path = checkpoints / (digest + ".bin")
        if not cp_path.is_file() or epoch >= int(head["epoch"]):
            continue
        state = diagnostic.inspect(cp_path.read_bytes())
        packed = [item for item in state["heap"] if item["packedFloat"] and item["count"] == 1024]
        if not packed:
            continue
        child = json.loads((reports / ("slice-%020d.json" % (epoch + 1))).read_text())
        assert child["method"] == "resumeMain" and child["suppliedGas"] == 1000000000
        assert child["gasUsed"] <= 1000000000 and child["elapsedMS"] <= 30000
        candidate = {"parentEpoch": epoch, "parentCheckpointSHA256": digest,
                     "parentCheckpointBytes": len(cp_path.read_bytes()), "packedFloatArrays": len(packed),
                     "childEpoch": epoch + 1, "childGasUsed": child["gasUsed"],
                     "childElapsedMS": child["elapsedMS"], "childCheckpointSHA256": child["checkpointSHA256"]}
        break
    assert candidate is not None, "q1 never successfully resumed a checkpoint containing a packed float array"
    return candidate


results["q1-packed-resume-from-successful-array-head"] = q1_packed_resume_receipt()


def capacity_boundary_state(decoded, target, expected_arrays, expect_oom):
    counts = decoded["heapCounts"]
    arrays = [row for row in decoded["heap"]
              if row["rank"] == 1 and row["metadata"] != "0x0"]
    assert counts["ordinaryArrays"] == expected_arrays, (target, counts)
    assert len(arrays) == expected_arrays, (target, len(arrays), counts)
    assert counts["arrayElements"] == 0
    assert all(row["count"] == 0 for row in arrays)
    if expect_oom:
        assert decoded["lifecycle"] == 3 and decoded["javaKind"] == 7
        assert decoded["javaRef"] != 0
    else:
        assert decoded["lifecycle"] == 2 and decoded["javaKind"] == decoded["javaRef"] == 0
    return {"targetOrdinaryArrays": target, "actualOrdinaryArrays": counts["ordinaryArrays"],
            "ordinaryObjects": counts["ordinaryObjects"], "arrayElements": counts["arrayElements"],
            "heapRecords": len(decoded["heap"]), "nextHandle": decoded["nextHandle"],
            "lifecycle": decoded["lifecycle"], "javaKind": decoded["javaKind"],
            "javaRef": decoded["javaRef"], "oom": expect_oom}


def direct_capacity_boundary(target, expect_oom=False):
    label = "array-capacity-%d" % target
    quantum = 4096
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q4096-start", [driver, "setup-chain", *args], label)
    run(label + "-q4096-finish", [driver, "finish", *args], label)
    run(label + "-q4096-reopen", [driver, "verify", *args], label)
    java_kind = 7 if expect_oom else 0
    head, checkpoint, decoded = terminal(world, 1, java_kind)
    expected = min(target, 2048)
    row = capacity_boundary_state(decoded, target, expected, expect_oom)
    assert head["epoch"] > 0 and len(checkpoint) <= 1048576
    assert head["quantum"] == quantum
    if expect_oom:
        # Kind 7 is the engine's fixed OutOfMemoryError registry entry. The
        # typed terminal carries javaRef/kind, while javaClass is intentionally
        # empty for this canonical bootstrap exception.
        exception = next(row for row in decoded["heap"] if row["handle"] == decoded["javaRef"])
        assert decoded["javaKind"] == 7
        assert int(exception["metadata"], 16) >> 255 == 1
        assert exception["classIndex"] == 10 and exception["rank"] == 0
        row["exceptionClassIndex"] = exception["classIndex"]
        row["exceptionHeapHandle"] = exception["handle"]
        row["exceptionFields"] = decoded["heapCounts"]["exceptionFields"]
        assert head.get("javaClass") in (None, "")
    else:
        assert head.get("javaClass") in (None, "")
    canonical.append(world.name)
    return {"world": world.name, "quantum": quantum, "requestedAllocations": fixture(label)["requestedAllocations"],
            "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
            "checkpointSHA256": head["checkpointSHA256"], "checkpointBytes": len(checkpoint),
            **row}


capacity_results = {}
for target in (1024, 1025, 2048):
    capacity_results[str(target)] = direct_capacity_boundary(target)
capacity_results["2049"] = direct_capacity_boundary(2049, expect_oom=True)
results["ordinary-array-capacity-boundaries-q4096"] = capacity_results


def checkpoint_rehash(path):
    script = out / "tmp/rehash-checkpoint.js"
    script.write_text(r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const p=process.argv[2],b=fs.readFileSync(p),schema=b.readUInt32BE(8),machine=b.subarray(280);
const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const d=Buffer.from(keccak256(Buffer.from("JVMEVM:MC-RANDOM-CLASS-P20:MACHINE:1")),"hex");
const root=keccak256(Buffer.concat([d,word(schema),b.subarray(116,148),b.subarray(148,180),Buffer.from(keccak256(machine),"hex"),b.subarray(244,276)]));
b.write(root,180,"hex");b.writeUInt32BE(b.length-280,276);fs.writeFileSync(p,b);
''')
    env = {**os.environ, "NODE_PATH": str(node_modules), "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run(["node", script, path], cwd=root, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sparse_refusal(label, mutate, want_code):
    world = out / "world-sparse-array-stress-q1"
    head = json.loads((world / "durable-head.json").read_text())
    cp = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    view = diagnostic.inspect(cp)
    sparse = [row for row in view["heap"] if row["count"] == 65536 and row["sparse"]]
    assert len(sparse) == 3
    blob = bytearray(cp)
    mutate(blob, sparse)
    path = out / "tmp" / (label + ".bin")
    path.write_bytes(blob)
    checkpoint_rehash(path)
    run(label, [driver, "sparse-malformed", world, coordinator, engine,
                fixtures / "sparse-array-stress.zip", "1", path, str(want_code), label],
        "sparse-array-stress")
    receipt = json.loads((report(world) / (label + ".json")).read_text())
    assert receipt["error"] == "LC0StateError" and receipt["code"] == want_code
    assert receipt["rootUnchanged"] and receipt["headUnchanged"] and receipt["logsUnchanged"]
    return receipt


# Every malformed sparse record is re-rooted so the EVM reaches sparse decoding,
# rather than merely failing the outer commitment check.
malformed = {}

def zero_sparse_value(blob, arrays):
    values = next(row for row in arrays if len(row["sparseCells"]) >= 1)["sparseCells"]
    at = values[0]["valueOffset"]
    blob[at:at+8] = bytes(8)

def duplicate_sparse_index(blob, arrays):
    values = next(row for row in arrays if len(row["sparseCells"]) >= 2)["sparseCells"]
    blob[values[1]["indexOffset"]:values[1]["indexOffset"]+4] = blob[values[0]["indexOffset"]:values[0]["indexOffset"]+4]

def out_of_range_sparse_index(blob, arrays):
    row = next(row for row in arrays if row["sparseCells"])
    at = row["sparseCells"][-1]["indexOffset"]
    blob[at:at+4] = (row["count"]).to_bytes(4, "big")

def excessive_sparse_count(blob, arrays):
    row = arrays[0]; at = row["sparseCountOffset"]
    blob[at:at+4] = (row["count"] + 1).to_bytes(4, "big")

def undersized_sparse_array(blob, arrays):
    row = arrays[0]; at = row["countOffset"]
    blob[at:at+4] = (0x80000000 | 1023).to_bytes(4, "big")

def truncated_sparse_pairs(blob, arrays):
    # A valid sparse count under the canonical saving threshold whose pair bytes
    # exceed all remaining machine data exercises the bounded short-read guard.
    row = arrays[0]; at = row["sparseCountOffset"]
    blob[at:at+4] = (1000).to_bytes(4, "big")

for label, mutation, code in (("sparse-zero-value-refusal", zero_sparse_value, 6),
                              ("sparse-duplicate-index-refusal", duplicate_sparse_index, 6),
                              ("sparse-out-of-range-refusal", out_of_range_sparse_index, 6),
                              ("sparse-excessive-count-refusal", excessive_sparse_count, 6),
                              ("sparse-undersized-array-refusal", undersized_sparse_array, 6),
                              ("sparse-truncated-pairs-refusal", truncated_sparse_pairs, 2)):
    malformed[label] = sparse_refusal(label, mutation, code)

# Convert one valid all-zero sparse record to its old dense wire spelling. It is
# structurally readable but must fail canonical re-encode validation (code 3).
def dense_legacy_spelling(blob, arrays):
    row = next(row for row in arrays if row["sparseCount"] == 0)
    start, end, length = row["recordStart"], row["recordEnd"], row["count"]
    dense = blob[start:start+39] + length.to_bytes(4, "big") + bytes(length * 8)
    blob[start:end] = dense

dense_refusal = sparse_refusal("sparse-noncanonical-dense-refusal", dense_legacy_spelling, 3)
malformed["sparse-noncanonical-dense-refusal"] = dense_refusal
results["sparse-malformed-refusals"] = malformed


def packed_refusal(label, mutate, want_code):
    world = out / "world-packed-array-oracle-q1"
    head = json.loads((world / "durable-head.json").read_text())
    cp = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    view = diagnostic.inspect(cp)
    packed = [row for row in view["heap"] if row["packedFloat"] and row["count"] == 1024]
    assert len(packed) == 1
    blob = bytearray(cp)
    mutate(blob, packed[0])
    path = out / "tmp" / (label + ".bin")
    path.write_bytes(blob)
    checkpoint_rehash(path)
    run(label, [driver, "sparse-malformed", world, coordinator, engine,
                fixtures / "packed-array-oracle.zip", "1", path, str(want_code), label],
        "packed-array-oracle")
    receipt = json.loads((report(world) / (label + ".json")).read_text())
    assert receipt["error"] == "LC0StateError" and receipt["code"] == want_code
    assert receipt["rootUnchanged"] and receipt["headUnchanged"] and receipt["logsUnchanged"]
    return receipt


def both_array_flags(blob, row):
    at = row["countOffset"]
    blob[at:at+4] = (row["wireCount"] | 0x80000000).to_bytes(4, "big")


def packed_wrong_rank(blob, row):
    blob[row["recordStart"] + 38] = 2


def packed_wrong_type(blob, row):
    at = row["recordStart"] + 4
    blob[at:at+32] = (0x49).to_bytes(32, "big")


def packed_bad_profitability(blob, row):
    for cell in row["packedCells"][1:]:
        at = cell["valueOffset"]
        blob[at:at+4] = bytes(4)


def packed_bad_count(blob, row):
    at = row["countOffset"]
    blob[at:at+4] = (0x40000000 | 1023).to_bytes(4, "big")


def packed_truncation(blob, row):
    at = row["countOffset"]
    blob[at:at+4] = (0x40000000 | 65536).to_bytes(4, "big")


def dense_float_high_bits(blob, row):
    start, end, count = row["recordStart"], row["recordEnd"], row["count"]
    cells = [int(cell["value"], 16) for cell in row["packedCells"]]
    payload = bytearray()
    for i, value in enumerate(cells):
        if i == 0:
            value |= 1 << 32
        payload.extend(value.to_bytes(8, "big"))
    dense = blob[start:start+39] + count.to_bytes(4, "big") + payload
    blob[start:end] = dense


packed_malformed = {}
for label, mutate, code in (
    ("packed-both-flags-refusal", both_array_flags, 6),
    ("packed-wrong-rank-refusal", packed_wrong_rank, 6),
    ("packed-wrong-type-refusal", packed_wrong_type, 6),
    ("packed-bad-count-refusal", packed_bad_count, 6),
    ("packed-noncanonical-density-refusal", packed_bad_profitability, 6),
    ("packed-truncated-payload-refusal", packed_truncation, 2),
    ("float-dense-high-bits-refusal", dense_float_high_bits, 6),
):
    packed_malformed[label] = packed_refusal(label, mutate, code)
results["packed-malformed-refusals"] = packed_malformed


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
    normalized = []
    offsets = {"recordStart", "countOffset", "recordEnd", "sparseCountOffset"}
    for entry in heap:
        row = {key: value for key, value in entry.items() if key not in offsets}
        if entry["metadata"] == "0x43":
            row["cells"] = []
            row["sparseCells"] = []
        else:
            row["sparseCells"] = [{"index": cell["index"], "value": cell["value"]}
                                  for cell in entry["sparseCells"]]
        normalized.append(row)
    return normalized
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
# P16 exposes Object.hashCode; the prior P5 omission control is a positive inherited call here.
q_equivalent("object-hashcode-omitted")
execution_refusal("system-general-omitted", "0xd631c3a4", "3", atomic=True)


def math_sin_refusal(label):
    values = {}
    for quantum in (1, 7, 4096):
        world = out / ("world-" + label + "-q" + str(quantum))
        archive = fixtures / (label + ".zip")
        args = [world, coordinator, engine, archive, str(quantum)]
        run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
        reports = report(world)
        start_refusal = reports / "start-refusal.json"
        head_path = world / "durable-head.json"
        if start_refusal.exists():
            refusal_path = start_refusal
            refusal = json.loads(refusal_path.read_text())
            assert refusal["durableHeadUnchanged"]
            assert refusal["durableHeadSHA256Before"] == refusal["durableHeadSHA256After"]
            assert refusal["durableHeadEpochBefore"] == refusal["durableHeadEpochAfter"] == 0
            assert head_path.is_file()
            initial_head = json.loads(head_path.read_bytes())
            assert initial_head["epoch"] == initial_head["lifecycle"] == 0
            assert not list((world / "checkpoints").glob("*.bin"))
            assert not list(reports.glob("slice-*.json"))
            head_preserved = refusal["durableHeadSHA256Before"]
        else:
            assert head_path.is_file(), (label, quantum, "start succeeded without durable Head")
            run(label + "-q%d-finish-refusal" % quantum, [driver, "finish", *args], label)
            refusal_path = reports / "resume-refusal.json"
            refusal = json.loads(refusal_path.read_text())
            assert refusal["durableHeadUnchanged"]
            assert refusal["durableHeadSHA256Before"] == refusal["durableHeadSHA256After"]
            assert refusal["durableHeadEpochBefore"] == refusal["durableHeadEpochAfter"]
            assert head_path.is_file()
            after_slices = sorted(reports.glob("slice-*.json"))
            head_after = json.loads(head_path.read_bytes())
            assert len(after_slices) == head_after["epoch"]
            cp_path = world / "checkpoints" / (head_after["checkpointSHA256"] + ".bin")
            assert hashlib.sha256(cp_path.read_bytes()).hexdigest() == head_after["checkpointSHA256"]
            head_preserved = refusal["durableHeadSHA256Before"]
        refusal = json.loads(refusal_path.read_text())
        assert refusal["selector"] == "0x3a439c67" and words(refusal)[:1] == ["1"]
        assert len(words(refusal)) == 2 and int(words(refusal)[1]) > 0
        assert refusal["rootUnchanged"] and refusal["checkpointBytes"] == 0
        assert refusal["candidateHead"] == refusal["candidateCheckpoint"] == refusal["candidateRoot"] == ""
        assert refusal["suppliedGas"] == 1000000000 and refusal["gas"] <= 1000000000
        values["direct" if quantum == 4096 else "q" + str(quantum)] = {
            "selector": refusal["selector"], "uint256Words": words(refusal),
            "rootUnchanged": refusal["rootUnchanged"], "checkpointBytes": refusal["checkpointBytes"],
            "headPreserved": head_preserved, "execution": "atomic-refusal-no-continuation",
        }
    results[label] = values


for label in ("math-sin-above-bound-refusal", "math-sin-below-negative-bound-refusal",
              "math-sin-nan-refusal", "math-sin-positive-infinity-refusal",
              "math-sin-negative-infinity-refusal"):
    math_sin_refusal(label)


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
# The current authorized ordinary LOCAL call ceiling is 1B, below the historical
# 4.2B checkpoint-cap measurement. Preserve this as an explicit NON-ACCEPTANCE:
# every class byte was read, but OOG occurred before the checkpoint-cap selector.
assert refusal["selector"] == "0x" and refusal["checkpointBytes"] == 0
assert refusal["rootUnchanged"] and refusal["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
assert refusal["suppliedGas"] == 1000000000 and refusal["gas"] <= 1000000000
results["byte-471911"] = {"coordinatorAccepted": True,
                          "classification": "EXPECTED_LOCAL1B_OUT_OF_GAS_NOT_CHECKPOINT_CAP_ACCEPTANCE",
                          "allClassBytesRead": True, "localCeilingProbe": refusal}

world = out / "world-byte-471912"
run("byte-471912", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-71-471912.zip", "4096"], "count-71-471912")
refusal = json.loads((report(world) / "boundary-refusal.json").read_text())
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
results["byte-471912"] = refusal

run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical], "lower-ascii")
canonical_receipts = json.loads((out / "logs/canonical-receipts.log").read_text())
elapsed = time.monotonic() - started; assert elapsed <= 1200, elapsed
summary = {
    "profile": "MC-RANDOM-CLASS-P20-MAX-ARRAYS-2048",
    "generatedOnly": True,
    "bootstrapCount": 97,
    "bootstrapRoot": pins["bootstrapRoot"],
    "maxArrays": pins["maxArrays"],
    "maxHandles": pins["maxHandles"],
    "runtimeBytes": pins["engine"]["bytes"],
    "runtimeCapBytes": 393216,
    "rawLimits": [71, 471911],
    "diagnosticClassBound": 168,
    "globalNativeBindings": 21,
    "stringLocalBinding": 12,
    "sparseWire": pins["sparseWire"],
    "packedFloatWire": pins["packedFloatWire"],
    "externalLocalGas": pins["externalLocalGas"],
    "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
    "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
    "coordinatorRuntimeSHA256": pins["coordinator"]["runtimeSHA256"],
    "coordinatorRuntimeKeccak256": pins["coordinator"]["runtimeKeccak256"],
    "results": results,
    "canonicalReceipts": canonical_receipts,
    "commands": commands,
    "wholeGateSeconds": elapsed,
    "capacityQuantum": 4096,
    "capacityQuantumCaveat": "The 1024..2049 high-count worlds were run only at the normal direct quantum 4096 and each was reopened; high-count q1/q7 were not attempted because they imply thousands of full-heap checkpoint/revalidation slices under the ordinary 1B-per-call ceiling. This is a bounded generated capacity proof, not evidence that q1/q7 are semantically different or impossible.",
    "limitations": "The only production-source change is MAX_ARRAYS 1024->2048; MAX_HANDLES remains derived, and other caps, image leaves, bootstrap root, checkpoint wire, ABI/storage layout, coordinator authorization, and host limits are unchanged. Capacity fixtures allocate zero-length int[] values and check exact ordinary-array counters, element count, terminal lifecycle, typed OutOfMemoryError, public receipt chains, and reopen. Retained generated packed/sparse/malformed/Integer/Object/Math/raw71 controls remain part of this ordinary-1B gate. No original Minecraft replay, EULA, world, Done, or readiness claim is made here."
}

(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
