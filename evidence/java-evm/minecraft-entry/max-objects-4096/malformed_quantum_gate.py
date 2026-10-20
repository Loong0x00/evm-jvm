#!/usr/bin/env python3
"""Repeat retained malformed packed/sparse checkpoint refusals at q1/q7/direct."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
build, fixtures, retained, out = (Path(p).resolve() for p in sys.argv[1:5])
assert build.parent == fixtures.parent == retained.parent == out.parent == ROOT / "build"
assert build.name.startswith("java-diff-mc-max-objects-4096-build-")
assert fixtures.name.startswith("java-diff-mc-max-objects-4096-fixtures-")
assert retained.name.startswith("java-diff-mc-max-objects-4096-gate-")
assert out.name.startswith("java-diff-mc-max-objects-4096-malformed-") and not out.exists()
node_modules = ROOT / "jvmevm/runtime/node_modules"
pins = json.loads((build / "pins.json").read_text())
assert pins["domain"] == "MC-RANDOM-CLASS-P23"
out.mkdir(); (out / "tmp").mkdir(); (out / "logs").mkdir()
env0 = {**os.environ, "TMPDIR": str(out / "tmp"), "NODE_PATH": str(node_modules),
        "PYTHONDONTWRITEBYTECODE": "1", "GOPROXY": "off", "GOSUMDB": "off"}
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
spec = importlib.util.spec_from_file_location("max_arrays_4096_diagnostic", HERE / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
started = time.monotonic()


def rehash(path: Path) -> None:
    script = out / "tmp/rehash.js"
    script.write_text(r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const p=process.argv[2],b=fs.readFileSync(p),schema=b.readUInt32BE(8),machine=b.subarray(280);
const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");
const d=Buffer.from(keccak256(Buffer.from("JVMEVM:MC-RANDOM-CLASS-P23:MACHINE:1")),"hex");
const root=keccak256(Buffer.concat([d,word(schema),b.subarray(116,148),b.subarray(148,180),Buffer.from(keccak256(machine),"hex"),b.subarray(244,276)]));
b.write(root,180,"hex");b.writeUInt32BE(b.length-280,276);fs.writeFileSync(p,b);''')
    subprocess.run(["node", script, path], cwd=ROOT, env=env0, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(label: str, world: Path, archive: Path, fixture: dict, cp_path: Path, expected: int) -> dict:
    quantum = world.name.rsplit("q", 1)[1]
    args = [driver, "sparse-malformed", world, coordinator, engine, archive, quantum, cp_path, str(expected), label]
    env = dict(env0, MC_ENTRY_BINDINGS=",".join(fixture["entries"]))
    log = out / "logs" / (label + ".log"); began = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(list(map(str, args)), cwd=ROOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=1200)
    assert process.returncode == 0, (label, log)
    report = json.loads(((world.parent / "reports" / world.name) / (label + ".json")).read_text())
    assert report["error"] == "LC0StateError" and report["code"] == expected
    assert report["rootUnchanged"] and report["headUnchanged"] and report["logsUnchanged"]
    assert report["gas"] <= 1_000_000_000
    return {"label": label, "q": int(world.name.rsplit("q", 1)[1]),
            "expectedCode": expected, "gas": report["gas"],
            "elapsedSeconds": time.monotonic() - began,
            "validatedCheckpointSHA256": hashlib.sha256(cp_path.read_bytes()).hexdigest(),
            "selector": report["selector"], "rootUnchanged": report["rootUnchanged"],
            "headUnchanged": report["headUnchanged"], "logsUnchanged": report["logsUnchanged"]}


def sparse_cases(arrays):
    def zero(blob, rows):
        values = next(row for row in rows if row["sparseCells"])["sparseCells"]
        at = values[0]["valueOffset"]; blob[at:at + 8] = bytes(8)
    def duplicate(blob, rows):
        values = next(row for row in rows if len(row["sparseCells"]) >= 2)["sparseCells"]
        a, b = values[0]["indexOffset"], values[1]["indexOffset"]
        blob[b:b + 4] = blob[a:a + 4]
    def outside(blob, rows):
        row = next(row for row in rows if row["sparseCells"])
        at = row["sparseCells"][-1]["indexOffset"]; blob[at:at + 4] = row["count"].to_bytes(4, "big")
    def excessive(blob, rows):
        row = rows[0]; at = row["sparseCountOffset"]
        blob[at:at + 4] = (row["count"] + 1).to_bytes(4, "big")
    def undersized(blob, rows):
        row = rows[0]; at = row["countOffset"]
        blob[at:at + 4] = (0x80000000 | 1023).to_bytes(4, "big")
    def truncated(blob, rows):
        row = rows[0]; at = row["sparseCountOffset"]
        blob[at:at + 4] = (1000).to_bytes(4, "big")
    def noncanonical_dense(blob, rows):
        row = next(row for row in rows if row["sparseCount"] == 0)
        start, end, length = row["recordStart"], row["recordEnd"], row["count"]
        blob[start:end] = blob[start:start + 39] + length.to_bytes(4, "big") + bytes(length * 8)
    return [("zero-value", zero, 6), ("duplicate-index", duplicate, 6),
            ("out-of-range-index", outside, 6), ("excessive-count", excessive, 6),
            ("undersized-array", undersized, 6), ("truncated-pairs", truncated, 2),
            ("noncanonical-dense", noncanonical_dense, 3)]


def packed_cases():
    def both(blob, row):
        at = row["countOffset"]; blob[at:at + 4] = (row["wireCount"] | 0x80000000).to_bytes(4, "big")
    def wrong_rank(blob, row): blob[row["recordStart"] + 38] = 2
    def wrong_type(blob, row): blob[row["recordStart"] + 4:row["recordStart"] + 36] = (0x49).to_bytes(32, "big")
    def bad_profit(blob, row):
        for cell in row["packedCells"][1:]: blob[cell["valueOffset"]:cell["valueOffset"] + 4] = bytes(4)
    def bad_count(blob, row):
        at = row["countOffset"]; blob[at:at + 4] = (0x40000000 | 1023).to_bytes(4, "big")
    def truncated(blob, row):
        at = row["countOffset"]; blob[at:at + 4] = (0x40000000 | 65536).to_bytes(4, "big")
    def dense_high(blob, row):
        start, end, count = row["recordStart"], row["recordEnd"], row["count"]
        payload = bytearray()
        for i, cell in enumerate(row["packedCells"]):
            value = int(cell["value"], 16) | ((1 << 32) if i == 0 else 0)
            payload.extend(value.to_bytes(8, "big"))
        blob[start:end] = blob[start:start + 39] + count.to_bytes(4, "big") + payload
    return [("both-flags", both, 6), ("wrong-rank", wrong_rank, 6),
            ("wrong-type", wrong_type, 6), ("noncanonical-density", bad_profit, 6),
            ("bad-count", bad_count, 6), ("truncated-payload", truncated, 2),
            ("dense-high-bits", dense_high, 6)]


results = []
for quantum in (1, 7, 4096):
    for family, fixture_name, cases in (
        ("sparse", "sparse-array-stress", sparse_cases),
        ("packed", "packed-array-oracle", packed_cases),
    ):
        label_base = fixture_name
        source_world = retained / ("world-" + label_base + "-q" + str(quantum))
        world = out / ("world-" + family + "-q" + str(quantum))
        assert not world.exists()
        shutil.copytree(source_world, world)
        head = json.loads((world / "durable-head.json").read_text())
        source_cp = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
        blob = source_cp.read_bytes()
        decoded = diagnostic.inspect(blob)
        if family == "sparse":
            arrays = [row for row in decoded["heap"] if row["count"] == 65536 and row["sparse"]]
            assert len(arrays) == 3
            selected_cases = cases(arrays)
        else:
            arrays = [row for row in decoded["heap"] if row["packedFloat"] and row["count"] == 1024]
            assert len(arrays) == 1
            selected_cases = cases()
        fixture = json.loads((fixtures / (fixture_name + ".json")).read_text())
        archive = fixtures / (fixture_name + ".zip")
        for case_name, mutate, expected in selected_cases:
            bad = bytearray(blob)
            mutate(bad, arrays if family == "sparse" else arrays[0])
            mutated = out / "tmp" / (family + "-q%d-%s.bin" % (quantum, case_name))
            mutated.write_bytes(bad); rehash(mutated)
            label = "%s-%s-q%d" % (family, case_name, quantum)
            row = run(label, world, archive, fixture, mutated, expected)
            row["sourceCheckpointSHA256"] = head["checkpointSHA256"]
            results.append(row)

elapsed = time.monotonic() - started
assert len(results) == 42 and elapsed <= 1200
summary = {
    "schema": 1,
    "profile": "MC-RANDOM-CLASS-P23-MAX-OBJECTS-4096-worker-candidate",
    "generatedOnly": True,
    "quantums": [1, 7, 4096],
    "families": {"sparse": 7, "packed": 7},
    "cases": len(results),
    "allRefusalsPreserveHeadRootAndLogs": True,
    "maxGas": max(row["gas"] for row in results),
    "elapsedSeconds": elapsed,
    "results": results,
    "limitations": "Generated malformed checkpoint probes only; no original Minecraft data or Done claim.",
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"cases": len(results), "maxGas": summary["maxGas"],
                  "elapsedSeconds": elapsed, "summary": str(out / "summary.json")}, indent=2))
