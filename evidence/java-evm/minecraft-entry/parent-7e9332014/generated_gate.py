#!/usr/bin/env python3
"""Generated-only gate for canonical System.setOut(PrintStream).

The setOut identity/out/null/reset/subclass witness runs q1/q7/direct/reopen.
Retained controls run direct/reopen only; no original artifact, resource, network,
world, EULA, or Done marker is read or claimed.
"""
from pathlib import Path
import base64
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
retained_fixtures = Path(sys.argv[2]).resolve()
focused_fixtures = Path(sys.argv[3]).resolve()
out = Path(sys.argv[4]).resolve()
assert build.parent == root / "build" and retained_fixtures.parent == root / "build" and focused_fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-setout-parent-")
assert retained_fixtures.name.startswith("java-diff-mc-system-set-out-retained-fixtures-")
assert focused_fixtures.name.startswith("java-diff-mc-system-set-out-fixtures-")
assert out.name.startswith("java-diff-mc-setout-parent-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 94 and pins["rawLimits"] == [52, 329162]
assert pins["diagnosticClassBound"] == 146 and pins["engine"]["bytes"] <= 393216
assert pins["globalNativeBindings"] == 16 and pins["exceptionKinds"] == 14
assert pins["bootstrapSHA256"] == {
    "String": "04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231",
    "System": "5cab6f9c8389590025f923fcee698a5ed6797ad86f40bfd2fc7fab2529dcb3a4",
    "PrintStream": "cd053e0847ae7c3a740a54e246fbc3dd3c42635bb44bf6fcdc317004b411a41c",
}
assert pins["bootstrapRoot"] == "d9b2bc4f1e8799d1df1e981a5ea03016c1d80e5801ba72aef6dd8be8677f0235"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
# Overlay only trusted generated Java-8 ZIP/JSON inputs. No original artifact,
# JAR, resource, or world is linked or read.
fixtures = out / "fixtures"; fixtures.mkdir()
for source in (retained_fixtures, focused_fixtures):
    for entry in sorted(source.glob("*.json")) + sorted(source.glob("*.zip")):
        target = fixtures / entry.name
        if target.exists():
            assert entry.name in ("summary.json", "raw-throwable.json", "raw-throwable.zip"), entry
            continue
        target.symlink_to(entry)
assert (fixtures / "summary.json").is_symlink()
assert (fixtures / "system-out.zip").is_symlink() and (fixtures / "guest-stack.zip").is_symlink()
started = time.monotonic()
commands = []

def fixture(label):
    return json.loads((fixtures / (label + ".json")).read_text())

def bindings(label):
    return ",".join(fixture(label)["entries"])

def report(world):
    return world.parent / "reports" / world.name

def failure(world, name):
    return json.loads((report(world) / name).read_text())

def words(value):
    return list(map(str, value["uint256Words"]))

def run(label, args, fixture_label=None, expect=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    if fixture_label is not None:
        spec = fixture(fixture_label)
        env["MC_ENTRY_BINDINGS"] = bindings(fixture_label)
        selected = spec.get("selectedResource")
        if selected is not None: env["MC_ENTRY_SELECTED_RESOURCE"] = selected
        else: env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log")
    before = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": proc.returncode, "elapsedSeconds": time.monotonic() - before}
    commands.append(row)
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert proc.returncode == expect, (label, proc.returncode, log)

spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
rows = {}
canonical_labels = []

def terminal(world, raw_count, bootstrap_count=94):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 329162
    assert head.get("selectedResourceSize", 0) <= 4096
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + bootstrap_count
    return head, checkpoint, decoded

def finish(label, fixture_label, quantum, inspect_fn=None):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    spec = fixture(fixture_label)
    head, checkpoint, decoded = terminal(world, spec["bindingCount"], spec["bootstrapCount"])
    if inspect_fn is not None: inspect_fn(decoded)
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest()}

def q_equivalent(label, fixture_label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish(label, fixture_label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def q7_direct(label, fixture_label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (7, 4096):
        value = finish(label, fixture_label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q7"] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def retained(label, fixture_label, inspect_fn=None):
    # Accepted-parent controls are rerun direct/reopen. Repeating every inherited
    # q1 corpus would exceed the fixed 20-minute whole-gate limit; the newly
    # measured append(int) witnesses retain complete q1/q7/direct equivalence.
    rows[label] = {"direct": finish(label, fixture_label, 4096, inspect_fn)}

def _printstream_heap(checkpoint, raw_count, char=False):
    # Read-only decoding of the fixed _encodeMachine payload.  This is diagnostic
    # evidence only: normal resume remains the opaque EVM checkpoint ABI.
    data = checkpoint[280:]
    assert data[:4] == b"MR01"
    at = 4
    def take(n):
        nonlocal at
        assert 0 <= n <= len(data) - at
        value = data[at:at + n]
        at += n
        return value
    def u(n): return int.from_bytes(take(n), "big")
    take(1 + 4 + 1 + 4 + 8 + 8 + 1 + 32)
    take(u(2)); take(u(2))
    take(u(1) * 4)
    classes = u(2)
    assert classes == raw_count + 94
    statics = {}
    for ci in range(classes):
        take(1); take(1)
        fields = {}
        for _ in range(u(2)):
            index = u(2)
            fields[index] = u(32)
        statics[ci] = fields
    for _ in range(u(2)):
        take(2 + 2 + 4 + 32 + 1 + 4)
        take(u(2) * 32)
        locals_count = u(2)
        take((locals_count + 7) // 8 + locals_count * 32)
    handles = u(4)
    take(2 + 2 + 4 + 4 + 4 + 2 + 4)
    heap = {}
    for _ in range(handles):
        handle = u(4)
        meta = u(32)
        class_index = u(2)
        rank = u(1)
        count = u(4)
        cells = [u(8 if meta >> 255 == 0 else 32) for _ in range(count)]
        heap[handle] = (meta, class_index, rank, cells)
    assert raw_count == 1
    sink = statics[0][0]
    expected = statics[0][1]
    assert sink >> 64 == 2
    assert expected >> 64 == (1 if char else 2)
    sink_handle = sink & ((1 << 64) - 1)
    assert sink_handle != 0 and sink_handle in heap
    meta, class_index, rank, fields = heap[sink_handle]
    assert meta >> 255 == 1 and class_index == raw_count + 83 and rank == 0 and len(fields) == 2
    # Field0 is the retained println(String) reference; field1 is the char cell.
    if char:
        assert fields[1] == expected
    else:
        assert fields[0] == expected
    return {"lastLinePacked": hex(fields[0]), "lastCharPacked": hex(fields[1]),
            "sinkHandle": sink_handle, "printStreamClass": class_index}

def printstream_finish(label, fixture_label, quantum, inspect_fn=None):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    spec = fixture(fixture_label)
    head, checkpoint, decoded = terminal(world, spec["bindingCount"], spec["bootstrapCount"])
    if inspect_fn is not None: inspect_fn(decoded)
    heap = _printstream_heap(checkpoint, spec["bindingCount"], char=False)
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(), **heap}

def q_printstream(label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = printstream_finish(label, label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
                        "lastLinePacked", "printStreamClass"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def printstream_char_finish(label, quantum):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], label)
    spec = fixture(label)
    head, checkpoint, decoded = terminal(world, spec["bindingCount"], spec["bootstrapCount"])
    heap = _printstream_heap(checkpoint, spec["bindingCount"], char=True)
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(), **heap}

def q_printstream_char(label):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = printstream_char_finish(label, quantum)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
                        "lastCharPacked", "printStreamClass"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def _system_out_heap(checkpoint, raw_count):
    # Read-only decode of the opaque EVM checkpoint. Ordinary resume/reopen
    # remains the engine's encoded checkpoint ABI.
    data = checkpoint[280:]
    assert data[:4] == b"MR01"
    at = 4
    def take(n):
        nonlocal at
        assert 0 <= n <= len(data) - at
        value = data[at:at + n]
        at += n
        return value
    def u(n): return int.from_bytes(take(n), "big")
    take(1 + 4 + 1 + 4 + 8 + 8 + 1 + 32)
    take(u(2)); take(u(2)); take(u(1) * 4)
    classes = u(2)
    assert classes == raw_count + 94
    statics = {}
    for ci in range(classes):
        take(1); take(1)
        values = {}
        for _ in range(u(2)):
            index = u(2)
            values[index] = u(32)
        statics[ci] = values
    for _ in range(u(2)):
        take(2 + 2 + 4 + 32 + 1 + 4)
        take(u(2) * 32)
        locals_count = u(2)
        take((locals_count + 7) // 8 + locals_count * 32)
    handles = u(4)
    take(2 + 2 + 4 + 4 + 4 + 2 + 4)
    heap = {}
    for _ in range(handles):
        handle = u(4); meta = u(32); class_index = u(2); rank = u(1); count = u(4)
        heap[handle] = (meta, class_index, rank, [u(8 if meta >> 255 == 0 else 32) for _ in range(count)])
    assert raw_count == 2 and set(statics[0]) == set(range(7))
    probe = statics[0]
    system = statics[raw_count + 44]
    assert set(system) == {0, 1, 2, 3}
    out_value, err_value = system[3], system[2]
    assert out_value == probe[0] and err_value == probe[1]
    assert out_value >> 64 == err_value >> 64 == 2
    out_handle, err_handle = out_value & ((1 << 64) - 1), err_value & ((1 << 64) - 1)
    assert out_handle and err_handle and out_handle != err_handle
    for handle, line, char in ((out_handle, probe[2], probe[4]), (err_handle, probe[3], probe[5])):
        assert line >> 64 == 2 and char >> 64 == 1
        meta, class_index, rank, cells = heap[handle]
        assert meta >> 255 == 1 and class_index == raw_count + 83 and rank == 0 and len(cells) == 2
        assert cells == [line, char]
    assert probe[6] >> 64 == 1 and (probe[6] & ((1 << 64) - 1)) == 7
    return {"outHandle": out_handle, "errHandle": err_handle,
            "outLinePacked": hex(probe[2]), "errLinePacked": hex(probe[3]),
            "outCharPacked": hex(probe[4]), "errCharPacked": hex(probe[5]),
            "printStreamClass": raw_count + 83}

def system_out_initialized(decoded):
    raw = fixture("system-out")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2

def q_system_out():
    spec = fixture("system-out")
    assert spec["entries"] == ["SystemOutProbe.class", "SystemOutProbe$Handoff.class"]
    assert spec["bindingCount"] == 2 and spec["bootstrapCount"] == 94 and spec["java8HostOracle"] is False
    assert spec["classBytes"] == {"SystemOutProbe.class": 976, "SystemOutProbe$Handoff.class": 280}
    assert spec["classSHA256"] == {"SystemOutProbe.class": "4f037e6c3b02b5cd9c2d3d8d774c952f50fae719ebc6a33735a28ccffcacab0f", "SystemOutProbe$Handoff.class": "1babbe63df35139d66b5be05fbce73b8df7dad794bfeaea418b7df9c6482daaa"}
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish("system-out", "system-out", quantum, system_out_initialized)
        world = out / value["world"]
        head = json.loads((world / "durable-head.json").read_text())
        checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        value.update(_system_out_heap(checkpoint, fixture("system-out")["bindingCount"]))
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None:
            baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
                        "outHandle", "errHandle", "outLinePacked", "errLinePacked",
                        "outCharPacked", "errCharPacked", "printStreamClass"):
                assert value[key] == baseline[key], ("system-out", key, value, baseline)
    rows["system-out"] = row

# System.out is retained direct/reopen; the new direct superclass focus follows.
retained("system-out", "system-out", system_out_initialized)

# Current focused proof: only public PrintStream(OutputStream) is added. The
# supplied guest OutputStream is validated for null, but no FilterOutputStream
# state or forwarding is fabricated; the retained PrintStream line/char sinks
# remain private fields 0/1.
def _constructor_heap(checkpoint, raw_count):
    data = checkpoint[280:]
    assert data[:4] == b"MR01"
    at = 4
    def take(n):
        nonlocal at
        assert 0 <= n <= len(data) - at
        value = data[at:at + n]
        at += n
        return value
    def u(n): return int.from_bytes(take(n), "big")
    take(1 + 4 + 1 + 4 + 8 + 8 + 1 + 32)
    take(u(2)); take(u(2)); take(u(1) * 4)
    classes = u(2)
    assert classes == raw_count + 94
    statics = {}
    for ci in range(classes):
        take(1); take(1)
        values = {}
        for _ in range(u(2)):
            index = u(2)
            values[index] = u(32)
        statics[ci] = values
    for _ in range(u(2)):
        take(2 + 2 + 4 + 32 + 1 + 4)
        take(u(2) * 32)
        locals_count = u(2)
        take((locals_count + 7) // 8 + locals_count * 32)
    handles = u(4)
    take(2 + 2 + 4 + 4 + 4 + 2 + 4)
    heap = {}
    for _ in range(handles):
        handle = u(4); meta = u(32); class_index = u(2); rank = u(1); count = u(4)
        heap[handle] = (meta, class_index, rank, [u(8 if meta >> 255 == 0 else 32) for _ in range(count)])
    assert raw_count == 3
    probe = statics[0]
    assert set(probe) == set(range(7))
    direct, child, sink, direct_line, child_line, forwarded, result = [probe[i] for i in range(7)]
    assert direct >> 64 == child >> 64 == sink >> 64 == direct_line >> 64 == child_line >> 64 == 2
    assert forwarded == (1 << 64) and result == (1 << 64) | 7
    direct_handle, child_handle, sink_handle = [value & ((1 << 64) - 1) for value in (direct, child, sink)]
    assert direct_handle and child_handle and sink_handle and len({direct_handle, child_handle, sink_handle}) == 3
    direct_meta, direct_class, direct_rank, direct_cells = heap[direct_handle]
    child_meta, child_class, child_rank, child_cells = heap[child_handle]
    sink_meta, sink_class, sink_rank, sink_cells = heap[sink_handle]
    assert direct_meta >> 255 == child_meta >> 255 == sink_meta >> 255 == 1
    assert direct_class == raw_count + 83 and child_class < raw_count and sink_class < raw_count
    assert direct_rank == child_rank == sink_rank == 0 and len(direct_cells) == len(child_cells) == 2 and sink_cells == []
    assert direct_cells == [direct_line, (1 << 64) | ord("D")]
    assert child_cells == [child_line, (1 << 64) | 0x34]
    return {"directHandle": direct_handle, "childHandle": child_handle, "sinkHandle": sink_handle,
            "directLinePacked": hex(direct_line), "childLinePacked": hex(child_line),
            "directCharPacked": hex(direct_cells[1]), "childCharPacked": hex(child_cells[1]),
            "printStreamClass": direct_class, "childClass": child_class, "sinkClass": sink_class}

def constructor_initialized(decoded):
    raw = fixture("printstream-outputstream-constructor")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 35]["state"] == states[raw + 83]["state"] == 2

def q_constructor():
    spec = fixture("printstream-outputstream-constructor")
    assert spec["entries"] == ["PrintStreamOutputStreamConstructorMain.class", "PrintStreamOutputStreamConstructorMain$Child.class", "PrintStreamOutputStreamConstructorMain$Sink.class"]
    assert spec["bindingCount"] == 3 and spec["bootstrapCount"] == 94 and spec["java8HostOracle"] is False
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish("printstream-outputstream-constructor", "printstream-outputstream-constructor", quantum, constructor_initialized)
        world = out / value["world"]
        head = json.loads((world / "durable-head.json").read_text())
        checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        value.update(_constructor_heap(checkpoint, spec["bindingCount"]))
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None:
            baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "directHandle", "childHandle", "sinkHandle", "directLinePacked", "childLinePacked", "directCharPacked", "childCharPacked", "printStreamClass", "childClass", "sinkClass"):
                assert value[key] == baseline[key], ("printstream-outputstream-constructor", key, value, baseline)
    rows["printstream-outputstream-constructor"] = row

q_constructor()

# Binding16 mutates exactly System.out after ordinary invokestatic resolution,
# System initialization, and PrintStream assignability. The guest sequence
# observes direct replacement, a PrintStream subtype, null, and reset; this
# read-only checkpoint decoder then proves the final System.out slot is the
# original reference while System.err is still its exact original reference.
def _system_set_out_heap(checkpoint, raw_count):
    data = checkpoint[280:]
    assert data[:4] == b"MR01"
    at = 4
    def take(n):
        nonlocal at
        assert 0 <= n <= len(data) - at
        value = data[at:at + n]; at += n
        return value
    def u(n): return int.from_bytes(take(n), "big")
    take(1 + 4 + 1 + 4 + 8 + 8 + 1 + 32)
    take(u(2)); take(u(2)); take(u(1) * 4)
    classes = u(2); assert classes == raw_count + 94
    statics = {}
    for ci in range(classes):
        take(1); take(1); values = {}
        for _ in range(u(2)):
            index = u(2); values[index] = u(32)
        statics[ci] = values
    for _ in range(u(2)):
        take(2 + 2 + 4 + 32 + 1 + 4)
        take(u(2) * 32)
        locals_count = u(2)
        take((locals_count + 7) // 8 + locals_count * 32)
    handles = u(4)
    take(2 + 2 + 4 + 4 + 4 + 2 + 4)
    heap = {}
    for _ in range(handles):
        handle = u(4); meta = u(32); class_index = u(2); rank = u(1); count = u(4)
        heap[handle] = (meta, class_index, rank, [u(8 if meta >> 255 == 0 else 32) for _ in range(count)])
    assert raw_count == 3
    probe = statics[0]; system = statics[raw_count + 44]
    assert set(probe) == set(range(6)) and set(system) == {0, 1, 2, 3}
    original, err, direct, child, sink, result = [probe[i] for i in range(6)]
    assert result == (1 << 64) | 7
    assert original >> 64 == err >> 64 == direct >> 64 == child >> 64 == sink >> 64 == 2
    assert system[3] == original and system[2] == err and original != err
    handles = [value & ((1 << 64) - 1) for value in (original, err, direct, child, sink)]
    assert all(handles) and len(set(handles)) == 5
    assert heap[handles[2]][1] == raw_count + 83
    assert heap[handles[3]][1] == 1  # raw Child follows the entry root
    assert heap[handles[4]][1] == 2  # raw Sink is the final supplied entry
    return {"originalOutHandle": handles[0], "errHandle": handles[1],
            "directHandle": handles[2], "childHandle": handles[3],
            "sinkHandle": handles[4], "systemOutPacked": hex(system[3]),
            "systemErrPacked": hex(system[2]), "printStreamClass": raw_count + 83}

def system_set_out_initialized(decoded):
    raw = fixture("system-setout")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2

def q_system_set_out():
    spec = fixture("system-setout")
    assert spec["entries"] == ["SystemSetOutMain.class", "SystemSetOutMain$Child.class", "SystemSetOutMain$Sink.class"]
    assert spec["bindingCount"] == 3 and spec["bootstrapCount"] == 94 and spec["java8HostOracle"] is False
    baseline = None; row = {}
    for quantum in (1, 7, 4096):
        value = finish("system-setout", "system-setout", quantum, system_set_out_initialized)
        world = out / value["world"]
        head = json.loads((world / "durable-head.json").read_text())
        checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        value.update(_system_set_out_heap(checkpoint, spec["bindingCount"]))
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
                        "originalOutHandle", "errHandle", "directHandle", "childHandle", "sinkHandle",
                        "systemOutPacked", "systemErrPacked", "printStreamClass"):
                assert value[key] == baseline[key], ("system-setout", key, value, baseline)
    rows["system-setout"] = row

q_system_set_out()

# Null is caught as canonical guest NPE after OutputStream construction and
# before a terminal result. The Java fixture itself rejects any no-throw path.
def constructor_null_initialized(decoded):
    raw = fixture("printstream-outputstream-constructor-null")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 35]["state"] == states[raw + 83]["state"] == 2
    values = {entry["fieldIndex"]: int(entry["packedValue"], 16) for entry in states[0]["staticValues"]}
    assert values[0] == (2 << 64) and values[1] == (1 << 64) | 1 and values[2] == (1 << 64) | 7

q_equivalent("printstream-outputstream-constructor-null", "printstream-outputstream-constructor-null", constructor_null_initialized)

# No direct class use: the constructor addition cannot initialize OutputStream
# or PrintStream. Raw PrintStream replacement remains an inherited direct/reopen
# atomic rejection below.
value = finish("printstream-outputstream-constructor-uninitialized", "printstream-outputstream-constructor-uninitialized", 4096)
world = out / value["world"]
_, _, decoded = terminal(world, fixture("printstream-outputstream-constructor-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("printstream-outputstream-constructor-uninitialized")["bindingCount"]
assert raw + 35 not in states and raw + 83 not in states
rows["printstream-outputstream-constructor-uninitialized"] = value

# Current focus: binding14 snapshots actual active interpreter frames into fresh
# top-first elements. The trusted fixtures index ReflectionUtil-shaped results,
# verify dotted class/method names, false native flags, and repeat-call identity.
# q1/q7/direct each reopen a canonical terminal checkpoint before retained runs.
def guest_stack_initialized(decoded):
    raw = decoded["classCount"] - 94
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 5]["state"] == 2
    assert raw + 90 not in states
retained("guest-stack", "guest-stack", guest_stack_initialized)
retained("guest-stack-two", "guest-stack-two", guest_stack_initialized)

def thread_unchanged_initialized(decoded):
    raw = decoded["classCount"] - 94
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 50]["state"] == 2 and raw + 90 not in states
retained("thread-empty", "thread-empty", thread_unchanged_initialized)

# Both changed leaves remain dormant in a no-use root.
current_noinit = finish("guest-stack-uninitialized", "uninitialized", 4096)
world = out / current_noinit["world"]
_, _, decoded = terminal(world, fixture("uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert 1 + 5 not in states and 1 + 90 not in states
rows["guest-stack-uninitialized"] = current_noinit

# Current focus: exact one-argument String.substring. Each normal generated
# result executes with q1/q7/direct and reopens its terminal durable checkpoint.
# The direct equality witnesses cover ASCII, UTF-16 surrogate units, begin-zero
# identity, repeated nonzero freshness, empty receiver, and a copied empty tail.
def substring_no_clinit(decoded):
    # Native String methods operate on already-owned literal/heap objects and
    # must not fabricate active use of the no-<clinit> bootstrap image.
    raw = decoded["classCount"] - 94
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 26 not in states
for label in (
    "substring-utf16", "substring-ascii-empty", "substring-identity-fresh",
    "substring-empty-receiver",
):
    retained(label, label, substring_no_clinit)

# Both invalid begin forms reach the same explicit profile boundary without
# publishing a Head. The exact PC is fixture bytecode metadata, while reason=1
# is the stable no-String-bounds-exception profile contract.
for label in ("substring-invalid-negative", "substring-invalid-past-end"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x32e310eb" and words(refusal)[0] == "1" and refusal["rootUnchanged"]
    rows[label] = refusal

# This slice exposes no substring(int,int). The established String fallback is
# also a profile refusal, not a silent implementation of a second overload.
world = out / "world-substring-twoarg-omitted"
run("substring-twoarg-omitted-refusal", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "substring-twoarg-omitted.zip", "4096"], "substring-twoarg-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x32e310eb" and words(refusal)[0] == "1" and refusal["rootUnchanged"]
rows["substring-twoarg-omitted"] = refusal

# The bounded allocator reserves the char[] and String before publishing either
# handle. The guest catch sees the existing OOME, retains the final complete
# suffix, and stores the exact count (1022) in its only raw static field.
def substring_oom_atomic(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    raw = states[0]
    assert raw["state"] == 2 and len(raw["staticValues"]) == 1
    value = int(raw["staticValues"][0]["packedValue"], 16)
    assert value >> 64 == 1 and (value & ((1 << 64) - 1)) == 1022
rows["substring-oom-atomic"] = {"direct": finish(
    "substring-oom-atomic", "substring-oom-atomic", 4096, substring_oom_atomic
)}

# The append-owned StackTraceElement raw-name rejection is current-stage input;
# the pre-existing raw Throwable-family control is retained below.
world = out / "world-raw-stack-trace-element"
run("raw-stack-trace-element-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-stack-trace-element.zip", "4096"], "raw-stack-trace-element")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-stack-trace-element"] = refusal

# Object.getClass binding13 resolves through Object but returns the receiver's
# dynamic subclass mirror. The guest check proves literal/repeated/two-instance
# identity, and q1/q7/direct/reopen prove its canonical checkpoint encoding.
def object_getclass_initialized(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[2]["state"] == 2  # raw Child is initialized by real new.
retained("object-getclass", "object-getclass", object_getclass_initialized)

# The mirror target in this test is Dormant raw class index1. Its literal and
# Object.getClass result are legal without active use; a failing <clinit> must
# remain absent after every complete/reopened chain.
def object_getclass_noinit(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert 1 not in states, states
retained("object-getclass-noinit", "object-getclass-noinit", object_getclass_noinit)

# Null is raised by the ordinary invokevirtual receiver check before native code.
retained("object-getclass-null", "object-getclass-null")

# A raw Object remains ordinary user Code, rather than acquiring binding13 from
# its name/descriptor. This control returns its authored null under all quanta.
retained("raw-object-getclass", "raw-object-getclass")

# The shared mirror allocator preserves its pre-allocation quota check: OOM is
# catchable with no partial loader/name/mirror state. The retained general OOM
# gate keeps its full q1/q7/direct sweep; this 1023-object allocator boundary is
# exercised direct/reopen so its checkpoint corpus stays finite.
rows["object-getclass-oom"] = finish("object-getclass-oom", "object-getclass-oom", 4096)

# The single generated deflated ZIP resource is read by AS0/ZI0/DI0 into the
# initial readonly VFS before Java starts. The guest then creates the canonical
# raw mirror/loader needed by the pre-existing enumeration surface, obtains its
# URL, uses ordinary URL.openStream -> File -> FileInputStream, reads exact bytes
# and EOF, verifies close, and proves a FileOutputStream cannot mutate /ro.
def url_openstream_seed(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    # URL (raw+62), FileInputStream (raw+36), and FileOutputStream (raw+37)
    # were all genuinely initialized by the guest path.
    assert states[63]["state"] == 2 and states[37]["state"] == 2 and states[38]["state"] == 2

def url_openstream_finish(label, fixture_label, quantum):
    value = finish(label, fixture_label, quantum, url_openstream_seed)
    world = out / value["world"]
    head = json.loads((world / "durable-head.json").read_text())
    spec = fixture(fixture_label)
    assert head["selectedResourceName"] == __import__("base64").b64encode(spec["selectedResource"].encode()).decode()
    assert head["selectedResourceSize"] == spec["selectedResourceBytes"]
    assert head["selectedResourceRoot"] != "0x" + "00" * 32
    start = json.loads((report(world) / "start.json").read_text())
    selected = start["selectedResource"]
    assert selected["name"] == spec["selectedResource"] and selected["size"] == spec["selectedResourceBytes"]
    seed_address = selected["decoder"].lower()
    hashes = {key.lower(): value for key, value in start["resourceReadHashes"].items()}
    assert hashes[seed_address] == spec["selectedResourceSHA256"]
    return value

base = None
url_row = {}
for quantum in (4096,):
    value = url_openstream_finish("url-openstream", "url-openstream", quantum)
    url_row["direct" if quantum == 4096 else "q" + str(quantum)] = value
    if base is None: base = value
    else:
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
            assert value[key] == base[key], ("url-openstream", key, value, base)
rows["url-openstream"] = url_row

# Absent lookup remains empty through the real ZI0-backed enumeration and a
# direct URL cannot fabricate content: FileInputStream raises guest FNF.
retained("url-openstream-absent", "url-openstream-absent")

# Properties.load is an accepted parent control. Retain its complete direct/
# reopen path and its actual guest initialization, but reserve q1/q7/direct
# equivalence in this bounded whole gate for the newly added startsWith surface.
def properties_load_initialized(decoded):
    raw = fixture("properties-load")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 47]["state"] == 2  # Properties
    assert states[raw + 62]["state"] == 2  # URL
    assert states[raw + 36]["state"] == 2  # FileInputStream
retained("properties-load", "properties-load", properties_load_initialized)

# Parent null/escape controls remain direct/reopen; no parser behavior changes.
retained("properties-load-null", "properties-load-null")
retained("properties-load-escape", "properties-load-escape")

# Exactly4096 property units fit the parser and selected-resource caps. A custom
# generated InputStream separately proves the first 4097th unit raises guest
# IOException; these long loop boundaries use q4096/reopen only.
line4096 = finish("properties-load-line-4096", "properties-load-line-4096", 4096)
rows["properties-load-line-4096"] = line4096
line4097 = finish("properties-load-line-4097", "properties-load-line-4097", 4096)
rows["properties-load-line-4097"] = line4097

# The scalar constructor resource slot accepts exactly one 4096-byte decoder
# output. 4097 is decoded by DI0 but rejected atomically by coordinator policy.
resource4096 = finish("url-resource-4096", "url-resource-4096", 4096)
world = out / resource4096["world"]
head = json.loads((world / "durable-head.json").read_text())
assert head["selectedResourceSize"] == 4096
rows["url-resource-4096"] = resource4096
world = out / "world-url-resource-4097"
run("url-resource-4097-boundary", [driver, "boundary-create", world, coordinator, engine,
    fixtures / "url-resource-4097.zip", "4096"], "url-resource-4097")
refusal = failure(world, "boundary-refusal.json")
assert refusal["rootUnchanged"] and words(refusal) == ["27"], refusal
rows["url-resource-4097"] = refusal

# The explicit generated fixture interface refuses two names before any world,
# and coordinator constructor checks both a wrong committed resource root and a
# wrong decoder address after EVM AS0/ZI0/DI0 preparation without publishing a Head.
world = out / "world-url-resource-count2"
args = [driver, "setup-chain", world, coordinator, engine, fixtures / "url-openstream.zip", "4096"]
env = dict(os.environ, MC_ENTRY_BINDINGS=bindings("url-openstream"), MC_ENTRY_SELECTED_RESOURCE="generated/url.bin,generated/other.bin", TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
log = out / "logs/url-resource-count2.log"
with log.open("w") as stream:
    proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
commands.append({"label": "url-resource-count2", "command": list(map(str, args)), "exit": proc.returncode})
assert proc.returncode == 2 and not world.exists()
rows["url-resource-count2"] = {"worldExists": False}
for mode, expected in (("resource-root-tamper", ["26"]), ("resource-address-tamper", ["25"])):
    world = out / ("world-url-" + mode)
    run("url-" + mode, [driver, mode, world, coordinator, engine,
        fixtures / "url-openstream.zip", "4096"], "url-openstream")
    refusal = failure(world, "resource-tamper-refusal.json")
    assert refusal["rootUnchanged"] and words(refusal) == expected, refusal
    rows[mode] = refusal

# Arrays, primitive literals and forged Class objects remain narrow hard
# refusals. They publish no Head and cannot fabricate a generic reflection path.
for label, expected_selector, expected_code in (
    ("object-getclass-array", "0xd631c3a4", "4"),
    ("object-getclass-primitive", None, None),
    ("object-getclass-forged-mirror", None, None),
):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["rootUnchanged"], refusal
    if expected_selector is not None:
        assert refusal["selector"] == expected_selector and words(refusal)[0] == expected_code, refusal
    rows[label] = refusal

# The focused ordinary Java-8 interface signature dispatches to the replaced
# ReentrantLock image. Three successful acquisitions and matching unlocks run
# entirely as guest field mutation; no interrupt state, blocking, or scheduler
# behavior is asserted.
def lock_interruptibly_initialized(decoded):
    raw = fixture("lock-interruptibly")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 77]["state"] == 2
retained("lock-interruptibly", "lock-interruptibly", lock_interruptibly_initialized)

# A null Lock receiver reaches the existing catchable NPE path even though the
# Java declaration carries InterruptedException.
retained("lock-interruptibly-null", "lock-interruptibly-null")

# Neither replacement is initialized by a root that contains no lock symbol.
lock_noinit = finish("lock-interruptibly-uninitialized", "lock-interruptibly-uninitialized", 4096)
world = out / lock_noinit["world"]
_, _, decoded = terminal(world, fixture("lock-interruptibly-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("lock-interruptibly-uninitialized")["bindingCount"]
assert raw + 75 not in states and raw + 77 not in states
rows["lock-interruptibly-uninitialized"] = lock_noinit

# StringBuilder is a real guest class: non-null chained append must preserve
# receiver identity/order, while toString creates independent guest String copies.
def stringbuilder_initialized(decoded):
    raw = fixture("stringbuilder")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
retained("stringbuilder", "stringbuilder", stringbuilder_initialized)

# The documented null bound is a catchable guest NPE before append allocates.
retained("stringbuilder-null", "stringbuilder-null")

# Image84 retains its narrow zero reset, then adds only the String-backed
# CharSequence range signature. Valid empty/middle/full ranges and every
# documented IAE rejection execute in ordinary guest bytecode under q1/q7/direct
# plus reopen, while all prior StringBuilder controls remain retained.
def stringbuilder_charsequence_initialized(decoded):
    raw = decoded["classCount"] - 94
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
retained("stringbuilder-setlength-zero", "stringbuilder-setlength-zero", stringbuilder_charsequence_initialized)
retained("stringbuilder-setlength-nonzero", "stringbuilder-setlength-nonzero", stringbuilder_charsequence_initialized)
retained("stringbuilder-charsequence-range", "stringbuilder-charsequence-range", stringbuilder_charsequence_initialized)
retained("stringbuilder-charsequence-refusal", "stringbuilder-charsequence-refusal", stringbuilder_charsequence_initialized)

# Accepted lastIndexOf witnesses remain direct/reopen parent controls. They
# demonstrate that replacing slot26 did not drop or reorder the prior method.
for label in (
    "last-index-suffix", "last-index-middle", "last-index-prefix", "last-index-overlap",
    "last-index-repeated", "last-index-absent", "last-index-empty-target",
    "last-index-empty-receiver", "last-index-longer-target", "last-index-utf16",
    "last-index-surrogate", "last-index-null",
):
    retained(label, label)

# The focused new Java-8 offset-zero startsWith(String) cases each require q1,
# q7, direct, reopen, canonical terminal state and exact UTF-16 code-unit
# comparison. No offset overload, native binding, or host comparison is used.
for label in (
    "starts-empty-prefix", "starts-longer-prefix", "starts-exact", "starts-prefix",
    "starts-absent", "starts-empty-receiver", "starts-empty-receiver-nonempty",
    "starts-utf16", "starts-surrogate-pair", "starts-high-surrogate", "starts-null",
):
    retained(label, label)

# A String[] main signature alone must not initialize the String bootstrap.
string_uninitialized = finish("string-uninitialized", "string-uninitialized", 4096)
world = out / string_uninitialized["world"]
_, _, decoded = terminal(world, fixture("string-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("string-uninitialized")["bindingCount"] + 26 not in states
rows["string-uninitialized"] = string_uninitialized

# A no-use root must leave the appended bootstrap uninitialized.
stringbuilder_uninitialized = finish("stringbuilder-uninitialized", "stringbuilder-uninitialized", 4096)
world = out / stringbuilder_uninitialized["world"]
_, _, decoded = terminal(world, fixture("stringbuilder-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("stringbuilder-uninitialized")["bindingCount"] + 84 not in states
rows["stringbuilder-uninitialized"] = stringbuilder_uninitialized

# TreeMap retains its ordinary guest construction and identity properties. This
# retained probe uses no Map mutation, ordering, comparator, view, or extra API.
def treemap_initialized(decoded):
    raw = fixture("treemap")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 85]["state"] == 2
a = retained("treemap", "treemap", treemap_initialized)
assert a is None

# The focused positive is the sole new semantic surface: a fresh TreeMap passes
# the SortedMap receiver type-link and its concrete isEmpty() returns true.
# q1/q7/direct/reopen must preserve its terminal machine and opaque payload.
def treemap_sorted_empty_initialized(decoded):
    raw = fixture("treemap-sorted-empty")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 85]["state"] == 2
retained("treemap-sorted-empty", "treemap-sorted-empty", treemap_sorted_empty_initialized)

# A no-use root leaves the bounded TreeMap image uninitialized.
treemap_uninitialized = finish("treemap-uninitialized", "treemap-uninitialized", 4096)
world = out / treemap_uninitialized["world"]
_, _, decoded = terminal(world, fixture("treemap-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("treemap-uninitialized")["bindingCount"] + 85 not in states
rows["treemap-uninitialized"] = treemap_uninitialized

# The generated quota witness allocates two 65536-char guest arrays before its
# second append reaches array-element OOM. Those live arrays cannot fit the fixed
# 1MiB checkpoint, so the pinned engine must refuse publication honestly and
# atomically rather than fabricate a catchable terminal result. The retained
# small field-arena OOM below continues to prove catchable guest OOM semantics.
world = out / "world-stringbuilder-oom-infeasible"
run("stringbuilder-oom-infeasible", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "stringbuilder-oom.zip", "4096"], "stringbuilder-oom")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["stringbuilder-oom-infeasible"] = refusal

# Image84 retains the ordinary no-argument constructor, append(String), and
# toString. Its new (I)V constructor uses the accepted exact-content model:
# 0, 1, and 255 all start logically empty, then append from index0. A negative
# argument takes ordinary guest newarray and is caught as NegativeArraySizeException.
def stringbuilder_capacity_initialized(decoded):
    raw = fixture("stringbuilder-capacity-0")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
for label in ("stringbuilder-capacity-0", "stringbuilder-capacity-1", "stringbuilder-capacity-255",
              "stringbuilder-capacity-negative"):
    retained(label, label, stringbuilder_capacity_initialized)

# No capacity inspection/growth, general resizing, or primitive append is
# fabricated. Each omitted member form resolves before any Head exists.
for label in ("stringbuilder-capacity-omitted", "stringbuilder-ensurecapacity-omitted",
              "stringbuilder-append-long-omitted", "stringbuilder-append-object-omitted",
              "stringbuilder-append-charsequence-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# System.err: raw field resolution triggers real System <clinit>; the generated
# constructor handoff checks type assignment and identity without output APIs.
def system_initialized(decoded):
    raw = fixture("system-err")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    system = states[raw + 44]; stream = states[raw + 83]
    assert system["state"] == stream["state"] == 2
    fields = {entry["fieldIndex"]: int(entry["packedValue"], 16) for entry in system["staticValues"]}
    assert fields[2] != 0 and fields[3] != 0 and fields[2] != fields[3], fields  # security, properties, err, out.
retained("system-err", "system-err", system_initialized)

# currentTimeMillis is ordinary Java 8 bytecode in image44: its static active
# use initializes the pre-existing System/PrintStream state, then lconst_0 /
# lreturn supply a stable LOCAL replay epoch. No host, block, or wall-clock
# input is available to this fixture.
def system_current_time_millis_initialized(decoded):
    raw = fixture("system-current-time-millis")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2
retained("system-current-time-millis", "system-current-time-millis", system_current_time_millis_initialized)

# monitorenter/monitorexit have no scheduling or contention state in the bounded
# single-guest-thread profile.  This generated root executes nested reentry,
# both ordinary exits, and a caught null monitorenter.  q1/q7/direct/reopen
# therefore cover each opcode's reference pop and guest-NPE path.
retained("monitor-enter-exit", "monitor-enter-exit")

# append(char) is ordinary Java bytecode in only image84. The focused root
# exercises retained String-prefix copying plus NUL, ASCII, and surrogate UTF-16
# units, same-builder return identity, independent toString copies, q1/q7/direct,
# and each durable reopen.
retained("stringbuilder-append-char", "stringbuilder-append-char")

# Image83 is ordinary Java Code, not host output.  The four non-null lines
# cover empty, ASCII, UTF-16 surrogate pair, and replacement of a prior line.
# The read-only heap decoder proves its private sole field equals the exact static
# guest String reference supplied to println after every q1/q7/direct/reopen run.
for label in ("printstream-empty", "printstream-ascii", "printstream-surrogate",
              "printstream-replacement", "printstream-null"):
    rows[label] = {"direct": printstream_finish(label, label, 4096)}
# print(char) writes exactly its final UTF-16 code unit into field1. NUL uses a
# prior nonzero char so the read-only checkpoint proof covers an actual zero overwrite.
for label in ("printstream-char-nul", "printstream-char-ascii", "printstream-char-surrogate",
              "printstream-char-replacement"):
    rows[label] = {"direct": printstream_char_finish(label, 4096)}

# Throwable image5 directly calls the retained PrintStream.println(String)
# member only when its ordinary detailMessage is non-null. The checkpoint sink
# field must therefore become the exact message handle for non-null and retain
# the prior handle for null, including a null PrintStream argument.
def throwable_print_initialized(decoded):
    raw = decoded["classCount"] - 94
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 5]["state"] == 2
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2
for label in ("throwable-print-nonnull", "throwable-print-null"):
    rows[label] = {"direct": printstream_finish(label, label, 4096, throwable_print_initialized)}

# All non-String print/println forms are absent from image83 and fail before a
# Head exists; the null member call above instead takes ordinary guest NPE.
for label in ("printstream-println-empty-omitted", "printstream-println-int-omitted",
              "printstream-print-string-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# A separate no-use root proves neither image is fabricated/preinitialized.
noinit = finish("system-uninitialized", "system-uninitialized", 4096)
world = out / noinit["world"]
_, _, decoded = terminal(world, fixture("system-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("system-uninitialized")["bindingCount"]
assert raw + 44 not in states and raw + 83 not in states
rows["system-uninitialized"] = noinit

# Retain catchable generic failed-initialization behavior while System remains
# untouched; inducing a failing System initializer would broaden the profile.
def failed_control(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[1]["state"] == 3
    assert 46 not in states and 85 not in states
retained("failed-init", "failed-init", failed_control)

# Both owned images reject raw replacement before any guest instruction executes.
for label in ("raw-string", "raw-system", "raw-system-setout", "raw-printstream", "raw-stringbuilder", "raw-treemap", "raw-lock-interruptibly-lock", "raw-lock-interruptibly-reentrant"):
    world = out / ("world-" + label)
    run(label + "-replacement", [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
    rows[label] = refusal

# Throwable remains in the pre-existing raw-only canonical family; its specific
# LinkError precedence is retained rather than relabeling it as the later
# bootstrap-profile replacement family.
world = out / "world-raw-throwable"
run("raw-throwable-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-throwable.zip", "4096"], "raw-throwable")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["6", "1"] and refusal["rootUnchanged"]
rows["raw-throwable"] = refusal

# TreeMap deliberately declares no put. Once its exact SortedMap edge is linked,
# Java virtual/interface resolution reaches retained abstract Map.put and produces
# the existing catchable AbstractMethodError kind11. This is the measured honest
# unsupported mutation outcome: neither call returns a map value or creates a
# fake mutation, and no EVM method implementation is added.
def omitted_abstract_method(label):
    world = out / ("world-" + label)
    run(label + "-unsupported", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    started = failure(world, "start.json")
    terminal = started["slice"]
    assert terminal["lifecycle"] == terminal["outcome"] == 3
    assert terminal["javaKind"] == 11 and terminal["javaRef"] == 8
    assert terminal["totalJvmSteps"] == 12 and terminal["totalInternalSteps"] == 3
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 3
    assert head["javaKind"] == 11 and head["javaRef"] == 8
    assert head["jvmSteps"] == 12 and head["internalSteps"] == 3
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == fixture(label)["bindingCount"] + 94
    assert decoded["javaKind"] == 11 and decoded["javaRef"] == 8
    run(label + "-reopen", [driver, "verify", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    rows[label] = {"unsupportedJavaKind": head["javaKind"],
                   "unsupportedJavaRef": head["javaRef"],
                   "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
                   "checkpointSHA256": head["checkpointSHA256"]}
omitted_abstract_method("treemap-mutation-omitted")
omitted_abstract_method("treemap-sortedmap-omitted")

# The only new positive surface is class linkage. A null checkcast resolves the
# empty SortedMap->Map edge while leaving the interface uninitialized; q1/q7/
# direct/reopen must retain the same complete checkpoint payload.
def sortedmap_link_uninitialized(decoded):
    raw = fixture("sortedmap-link-null")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 91 not in states
retained("sortedmap-link-null", "sortedmap-link-null", sortedmap_link_uninitialized)

# A raw class cannot replace the owned link-only interface.
world = out / "world-raw-sortedmap"
run("raw-sortedmap-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-sortedmap.zip", "4096"], "raw-sortedmap")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-sortedmap"] = refusal

# The new ordinary Java-8 valueOf(int) surface calls the preserved public
# constructor. q1/q7/direct each reopen a canonical terminal checkpoint; the
# guest fixture covers -1, zero, min, max, equality/value/hash and distinct
# allocations without a cache identity claim.
def integer_valueof_initialized(decoded):
    raw = fixture("integer-valueof")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 70]["state"] == 2
retained("integer-valueof", "integer-valueof", integer_valueof_initialized)

# A no-use root must not initialize the replacement bootstrap.
integer_valueof_noinit = finish("integer-valueof-uninitialized", "integer-valueof-uninitialized", 4096)
world = out / integer_valueof_noinit["world"]
_, _, decoded = terminal(world, fixture("integer-valueof-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("integer-valueof-uninitialized")["bindingCount"] + 70 not in states
rows["integer-valueof-uninitialized"] = integer_valueof_noinit

# A raw java/lang/Integer cannot replace the fixed bootstrap image.
world = out / "world-raw-integer-valueof"
run("raw-integer-valueof-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-integer-valueof.zip", "4096"], "raw-integer-valueof")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-integer-valueof"] = refusal

# The one-argument String overload is ordinary Java-8 guest Code: it invokes
# the preserved decimal parseInt, then the public int constructor. Every valid,
# invalid, null, and overflow witness runs q1/q7/direct/reopen and must retain
# one canonical terminal machine/checkpoint payload across quanta.
def integer_valueof_string_initialized(decoded):
    raw = fixture("integer-valueof-string-valid")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 70]["state"] == 2
for label in (
    "integer-valueof-string-valid", "integer-valueof-string-invalid",
    "integer-valueof-string-null", "integer-valueof-string-overflow",
):
    retained(label, label, integer_valueof_string_initialized)

# Java 8's two-argument radix overload remains absent. It must be an atomic
# EVM member-resolution refusal, not a host radix parser or cache fallback.
world = out / "world-integer-valueof-string-radix-omitted"
run("integer-valueof-string-radix-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "integer-valueof-string-radix-omitted.zip", "4096"], "integer-valueof-string-radix-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["integer-valueof-string-radix-omitted"] = refusal

# Image70 adds exactly Integer.toString(int). All signed boundaries and an
# ordinary positive value run q1/q7/direct/reopen. Fixtures verify exact decimal
# contents and fresh String identity from independent calls.
def integer_to_string_initialized(decoded):
    raw = fixture("integer-to-string-min")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 70]["state"] == 2
for label in (
    "integer-to-string-min", "integer-to-string-negative-one",
    "integer-to-string-zero", "integer-to-string-positive",
    "integer-to-string-max",
):
    retained(label, label, integer_to_string_initialized)

integer_to_string_noinit = finish("integer-to-string-uninitialized", "integer-to-string-uninitialized", 4096)
world = out / integer_to_string_noinit["world"]
_, _, decoded = terminal(world, fixture("integer-to-string-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("integer-to-string-uninitialized")["bindingCount"] + 70 not in states
rows["integer-to-string-uninitialized"] = integer_to_string_noinit

# Radix and unsigned formatting are still absent. Both are valid Java-8 source
# spellings and must stop at ordinary member resolution before any fake result.
for label in ("integer-to-string-radix-omitted", "integer-to-string-unsigned-omitted"):
    world = out / ("world-" + label)
    run(label, [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
    rows[label] = refusal

# The appended Java-8 direct Object subclass has only its constructor and get.
# q1/q7/direct/reopen prove strong referent identity and null retention through
# the ordinary guest field load/store path; no GC clearing is modeled.
def weak_reference_initialized(decoded):
    raw = fixture("weak-reference")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 86]["state"] == 2
retained("weak-reference", "weak-reference", weak_reference_initialized)

# A root with no WeakReference symbol must leave image87 uninitialized.
weak_reference_noinit = finish("weak-reference-uninitialized", "weak-reference-uninitialized", 4096)
world = out / weak_reference_noinit["world"]
_, _, decoded = terminal(world, fixture("weak-reference-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("weak-reference-uninitialized")["bindingCount"] + 86 not in states
rows["weak-reference-uninitialized"] = weak_reference_noinit

# A raw java/lang/ref/WeakReference cannot replace the owned appended image.
world = out / "world-raw-weak-reference"
run("raw-weak-reference-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-weak-reference.zip", "4096"], "raw-weak-reference")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-weak-reference"] = refusal

# The bounded image intentionally omits clear and every Reference API beyond get.
world = out / "world-weak-reference-clear-omitted"
run("weak-reference-clear-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "weak-reference-clear-omitted.zip", "4096"], "weak-reference-clear-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["weak-reference-clear-omitted"] = refusal

# The only new linkage surface is Collection extends Iterable. The focused
# generated root exercises return assignment, identity, and iterator dispatch;
# q1/q7/direct/reopen must share every terminal machine/opaque payload field.
def iterable_link_initialized(decoded):
    raw = fixture("iterable-link")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 57]["state"] == 2  # HashSet uses its existing iterator.
retained("iterable-link", "iterable-link", iterable_link_initialized)
retained("iterable-null", "iterable-null")

# An unrelated root cannot initialize the append-only Iterable image merely by
# having the image present in the canonical bootstrap tail.
iterable_noinit = finish("iterable-uninitialized", "iterable-uninitialized", 4096)
world = out / iterable_noinit["world"]
_, _, decoded = terminal(world, fixture("iterable-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("iterable-uninitialized")["bindingCount"] + 87 not in states
rows["iterable-uninitialized"] = iterable_noinit

# The append and replaced hierarchy names remain bootstrap-owned. A raw image
# cannot change Collection's new edge or substitute a different Iterable API.
for label in ("raw-iterable", "raw-collection"):
    world = out / ("world-" + label)
    run(label + "-replacement", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
    rows[label] = refusal

# forEach and spliterator are deliberately absent. Each Java-8 call site must
# refuse before a Head exists; the source verifier separately proves neither
# default method nor its Consumer/Spliterator type is in either added image.
for label in ("iterable-foreach-omitted", "iterable-spliterator-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["rootUnchanged"], refusal
    rows[label] = refusal

# The final image supports only directly-created ThreadLocal instances. Its one
# Object field provides the bounded single-guest-thread value semantics; all
# focused set/default-null/replace/null/identity observations must survive q1,
# q7, direct, and reopened execution with identical terminal checkpoints.
def threadlocal_set_initialized(decoded):
    raw = fixture("threadlocal-set")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 88]["state"] == 2
retained("threadlocal-set", "threadlocal-set", threadlocal_set_initialized)

# Retain allocation/identity coverage under the single field image.
retained("threadlocal-constructor", "threadlocal-constructor", threadlocal_set_initialized)

# Presence of image89 does not actively initialize it before a real new.
threadlocal_noinit = finish("threadlocal-uninitialized", "threadlocal-uninitialized", 4096)
world = out / threadlocal_noinit["world"]
_, _, decoded = terminal(world, fixture("threadlocal-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("threadlocal-uninitialized")["bindingCount"] + 88 not in states
rows["threadlocal-uninitialized"] = threadlocal_noinit

# A raw java/lang/ThreadLocal cannot replace the owned image89.
world = out / "world-raw-threadlocal"
run("raw-threadlocal-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-threadlocal.zip", "4096"], "raw-threadlocal")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-threadlocal"] = refusal

# remove/withInitial and a second guest thread remain absent paths. Each must
# refuse atomically before a Head exists; no map, default factory, or thread
# scheduler is fabricated.
for label in ("threadlocal-remove-omitted", "threadlocal-withinitial-omitted", "threadlocal-multithread-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# A final owned image refuses subclass initialValue declarations/overrides during
# normal hierarchy validation, independently of the field's null sentinel.
for label in ("threadlocal-initialvalue-omitted", "threadlocal-overridden-initialvalue-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xa52e829f" and words(refusal) == ["3", "1"] and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# The new image is Java 8 Math with only ordinary static (II)I min/max.
# q1/q7/direct/reopen must agree at equal, sign-crossing, and int32 extremes;
# class initialization is real active use even though the utility has no <clinit>.
def math_initialized(decoded):
    raw = fixture("math-int-min-max")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 89]["state"] == 2
retained("math-int-min-max", "math-int-min-max", math_initialized)

# An unrelated root leaves the append-only Math class absent from initialization.
math_noinit = finish("math-uninitialized", "math-uninitialized", 4096)
world = out / math_noinit["world"]
_, _, decoded = terminal(world, fixture("math-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("math-uninitialized")["bindingCount"] + 89 not in states
rows["math-uninitialized"] = math_noinit

# A raw Math cannot replace the owned bootstrap before any checkpoint exists.
world = out / "world-raw-math"
run("raw-math-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-math.zip", "4096"], "raw-math")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-math"] = refusal

# abs(int) and addExact(int,int) have supported operand descriptors but no
# appended members, so both remain atomic resolution refusals.
for label in ("math-abs-omitted", "math-addexact-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# Thread.getStackTrace returns a fresh, non-null guest array with exactly zero
# entries.  Thread itself initializes through currentThread; array allocation
# resolves the canonical StackTraceElement leaf without initializing it.
def thread_empty_stack_trace_initialized(decoded):
    raw = fixture("thread-empty-stack-trace")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 50]["state"] == 2
    assert raw + 90 not in states
retained("thread-empty-stack-trace", "thread-empty-stack-trace", thread_empty_stack_trace_initialized)

# A no-use root preserves accepted Thread and the new leaf as dormant classes.
thread_empty_noinit = finish("thread-empty-stack-trace-uninitialized", "thread-empty-stack-trace-uninitialized", 4096)
world = out / thread_empty_noinit["world"]
_, _, decoded = terminal(world, fixture("thread-empty-stack-trace-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("thread-empty-stack-trace-uninitialized")["bindingCount"]
assert raw + 50 not in states and raw + 90 not in states
rows["thread-empty-stack-trace-uninitialized"] = thread_empty_noinit

# Bootstrap ownership and the historical four-argument Java SE constructor
# remain absent. The old getClassName omission is intentionally superseded by the
# focused real-element checks above rather than being mislabeled a retained check.
world = out / "world-raw-stacktraceelement"
run("raw-stacktraceelement-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-stacktraceelement.zip", "4096"], "raw-stacktraceelement")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-stacktraceelement"] = refusal
label = "stacktraceelement-constructor-omitted"
world = out / ("world-" + label)
run(label, [driver, "setup-chain", world, coordinator, engine,
    fixtures / (label + ".zip"), "4096"], label)
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows[label] = refusal

# String slot26 adds exactly equalsIgnoreCase(String). Each result has its own
# q1/q7/direct/reopen chain and uses ordinary guest String.length/charAt code:
# exact UTF-16 equality, ASCII lower/upper folding, content/length mismatch,
# null false, and the explicit non-ASCII exact/no-general-fold control.
for label in (
    "string-equals-ignore-case-exact", "string-equals-ignore-case-lower-upper",
    "string-equals-ignore-case-mismatch", "string-equals-ignore-case-length",
    "string-equals-ignore-case-null", "string-equals-ignore-case-non-ascii-exact",
):
    retained(label, label)

# The generated CP descriptor mutation names equalsIgnoreCase(Object), which
# must remain the existing String-profile rejection, never an accidental overload
# or broad Object/String dispatch. The invoke bytecode begins at PC4.
world = out / "world-string-equals-ignore-case-object-omitted"
run("string-equals-ignore-case-object-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "string-equals-ignore-case-object-omitted.zip", "4096"], "string-equals-ignore-case-object-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x32e310eb" and words(refusal) == ["1", "4"] and refusal["rootUnchanged"]
rows["string-equals-ignore-case-object-omitted"] = refusal

# Image93 has only Objects.requireNonNull(Object,String).  The generated
# positive root compares the returned reference to the original guest object;
# q1/q7/direct/reopen must preserve exact identity and full checkpoint payload.
def objects_require_non_null_initialized(decoded, label):
    raw = fixture(label)["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 92]["state"] == 2
retained("objects-require-non-null", "objects-require-non-null",
             lambda decoded: objects_require_non_null_initialized(decoded, "objects-require-non-null"))

# The null path catches only guest NullPointerException.  It deliberately does
# not invoke a message getter or a String-taking NPE constructor, and makes no
# message-retention assertion.
retained("objects-require-non-null-null", "objects-require-non-null-null",
             lambda decoded: objects_require_non_null_initialized(decoded, "objects-require-non-null-null"))

# A no-use root keeps the new tail image uninitialized.
objects_noinit = finish("objects-require-non-null-uninitialized", "objects-require-non-null-uninitialized", 4096)
world = out / objects_noinit["world"]
_, _, decoded = terminal(world, fixture("objects-require-non-null-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("objects-require-non-null-uninitialized")["bindingCount"] + 92 not in states
rows["objects-require-non-null-uninitialized"] = objects_noinit

# Bootstrap ownership rejects a raw Objects image before instruction execution.
world = out / "world-raw-objects"
run("raw-objects-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-objects.zip", "4096"], "raw-objects")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-objects"] = refusal

# The one-argument overload is not part of image93 and must resolve to the
# ordinary missing-member refusal, never an expanded Objects API.
world = out / "world-objects-require-non-null-onearg-omitted"
run("objects-require-non-null-onearg-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "objects-require-non-null-onearg-omitted.zip", "4096"], "objects-require-non-null-onearg-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal) == ["3", "7"] and refusal["rootUnchanged"]
rows["objects-require-non-null-onearg-omitted"] = refusal

# Image94 contains only public Object-chaining construction.  The ordinary
# generated root verifies fresh identity and concrete Object/checkcast type-link;
# q1/q7/direct/reopen must agree on full terminal state.
def security_manager_initialized(decoded, label):
    raw = fixture(label)["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 93]["state"] == 2
retained("security-manager-construction", "security-manager-construction",
             lambda decoded: security_manager_initialized(decoded, "security-manager-construction"))

# A root without the name must leave the append-only image dormant.
security_manager_noinit = finish("security-manager-uninitialized", "security-manager-uninitialized", 4096)
world = out / security_manager_noinit["world"]
_, _, decoded = terminal(world, fixture("security-manager-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("security-manager-uninitialized")["bindingCount"] + 93 not in states
rows["security-manager-uninitialized"] = security_manager_noinit

# Raw replacement is refused before any guest instruction or checkpoint.
world = out / "world-raw-security-manager"
run("raw-security-manager-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-security-manager.zip", "4096"], "raw-security-manager")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-security-manager"] = refusal

# The representative inherited Java SE method is absent: this must be ordinary
# missing-member resolution, never a fabricated policy/context/security API.
world = out / "world-security-manager-api-omitted"
run("security-manager-api-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "security-manager-api-omitted.zip", "4096"], "security-manager-api-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["security-manager-api-omitted"] = refusal

# The accepted parent StringBuilder.append(int) witnesses remain generated
# direct/reopen controls. Complete q1/q7/direct focus is reserved below for the
# one new Integer.toString(int) image change.
def stringbuilder_append_int_initialized(decoded):
    raw = fixture("stringbuilder-append-int-min")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
for label in (
    "stringbuilder-append-int-min", "stringbuilder-append-int-negative-one",
    "stringbuilder-append-int-zero", "stringbuilder-append-int-positive",
    "stringbuilder-append-int-max", "stringbuilder-append-int-existing-prefix",
):
    retained(label, label, stringbuilder_append_int_initialized)

# The parent no-use and raw-Throwable ownership controls remain valid. The old
# empty-array positive is deliberately replaced by the focused frame snapshots.
throwable_get_stack_trace_noinit = finish("throwable-get-stack-trace-uninitialized", "throwable-get-stack-trace-uninitialized", 4096)
world = out / throwable_get_stack_trace_noinit["world"]
_, _, decoded = terminal(world, fixture("throwable-get-stack-trace-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("throwable-get-stack-trace-uninitialized")["bindingCount"] + 5 not in states
rows["throwable-get-stack-trace-uninitialized"] = throwable_get_stack_trace_noinit

world = out / "world-raw-throwable-get-stack-trace"
run("raw-throwable-get-stack-trace-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-throwable-get-stack-trace.zip", "4096"], "raw-throwable-get-stack-trace")
refusal = failure(world, "start-refusal.json")
# Throwable is already an old raw-only canonical family, so retain its earlier
# ClassError(6,1) precedence rather than relabeling it as a later append-family
# LinkError.
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["6", "1"] and refusal["rootUnchanged"]
rows["raw-throwable-get-stack-trace"] = refusal

# Exact raw52 is the focused capacity witness: all q1/q7/direct/reopen
# chains agree. Raw53 is independently refused before mutation by the product
# driver, coordinator, and engine. Disposable widenings affect only the one
# preceding layer.
q_equivalent("raw52", "count-52")
world = out / "world-raw53-driver"
run("raw53-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-53.zip", "4096"], "count-53", expect=2)
assert not world.exists(); rows["raw53-driver"] = {"worldExists": False}

def disposable_driver(label, coordinator_keccak, coordinator_bytes):
    source = (build / "main.go").read_text()
    assert source.count("len(m.Decoders) > 52") == 1 and source.count("len(parts) > 52") == 1
    source = (source.replace("len(m.Decoders) > 52", "len(m.Decoders) > 53")
                    .replace("len(parts) > 52", "len(parts) > 53"))
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

coordinator_driver = disposable_driver("raw53-coordinator-driver", pins["coordinator"]["runtimeKeccak256"], pins["coordinator"]["bytes"])
world = out / "world-raw53-coordinator"
run("raw53-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-53.zip", "4096"], "count-53")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
rows["raw53-coordinator"] = refusal

probe = out / "raw53-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[52]") == 4 and text.count("n > 52") == 1
probe_source.write_text(text.replace("[52]", "[53]").replace("n > 52", "n > 53"))
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
with (out / "logs/raw53-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_keccak = json.loads(probe_artifact.read_text())["codeHashes"]["runtimeKeccak256"]
engine_driver = disposable_driver("raw53-engine-driver", probe_keccak, len(json.loads(probe_artifact.read_text())["deployedBytecode"]) // 2)
world = out / "world-raw53-engine"
run("raw53-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-53.zip", "4096"], "count-53")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "53"] and refusal["rootUnchanged"]
rows["raw53-engine"] = refusal

# Both aggregate witnesses remain legal individual DI0 inputs; the test reaches
# the raw-package guard rather than an unrelated per-class transport refusal.
for label, total in (("count-52-329162", 329162), ("count-52-329163", 329163)):
    spec = fixture(label)
    assert spec["bindingCount"] == 52 and spec["totalClassBytes"] == total
    assert max(spec["classBytes"].values()) <= 262144

# Exactly 329162 raw bytes is admitted by the coordinator and reaches the
# engine's ordinary parser. The retained engine-side gas/reserve refusal proves
# only that this giant generated package cannot finish this bounded call; it is
# not a coordinator byte-limit refusal. 329163 is rejected atomically there.
world = out / "world-byte-329162"
run("byte-329162", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-52-329162.zip", "4096"], "count-52-329162")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["byte-329162"] = {"coordinatorAccepted": True, "engineRefusal": refusal}
world = out / "world-byte-329163"
run("byte-329163", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-52-329163.zip", "4096"], "count-52-329163")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
rows["byte-329163"] = refusal

# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.
assert fixture("enumset")["focusLevelAccessFlags"] & 0x4000
for label in ("enumset", "enumset-errors", "enumset-failed"):
    retained(label, label)
world = out / "world-enumset-uninitialized"
run("enumset-uninitialized", [driver, "setup-chain", world, coordinator, engine, fixtures / "enumset-uninitialized.zip", "4096"], "enumset-uninitialized")
refusal = failure(world, "start-refusal.json")
assert refusal["rootUnchanged"]
rows["enumset-uninitialized"] = refusal
finish("queue", "queue", 4096)
rows["queue"] = {"retained": True}
retained("oom", "oom")

# The exact new constructors preserve the caller-owned guest String in
# Throwable.detailMessage. All three caught forms run q1/q7/direct/reopen and
# must retain one terminal machine/checkpoint payload across quanta.
def index_out_of_bounds_string_initialized(decoded):
    raw = fixture("index-out-of-bounds-string-empty")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 16]["state"] == 2
    assert states[raw + 22]["state"] == 2
for label in (
    "index-out-of-bounds-string-empty", "index-out-of-bounds-string-ascii",
    "index-out-of-bounds-string-null",
):
    retained(label, label, index_out_of_bounds_string_initialized)

# A root that never names either changed class must not initialize RuntimeException
# or IndexOutOfBoundsException merely because their fixed leaves are present.
ioob_noinit = finish("index-out-of-bounds-string-uninitialized", "index-out-of-bounds-string-uninitialized", 4096)
world = out / ioob_noinit["world"]
_, _, decoded = terminal(world, fixture("index-out-of-bounds-string-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("index-out-of-bounds-string-uninitialized")["bindingCount"]
assert raw + 16 not in states and raw + 22 not in states
rows["index-out-of-bounds-string-uninitialized"] = ioob_noinit

# The uncaught guest object reaches a normal terminal checkpoint with the exact
# dynamic class name. This is only constructor/unwind evidence, not stack trace
# or reflection work. q1/q7/direct plus reopen preserve the terminal payload.
def finish_uncaught(label, fixture_label, quantum):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    head = json.loads((world / "durable-head.json").read_text())
    spec = fixture(fixture_label)
    assert head["lifecycle"] == head["outcome"] == 3 and head["javaKind"] == 0 and head["javaRef"] != 0
    assert base64.b64decode(head["javaClass"]) == b"java/lang/IndexOutOfBoundsException"
    assert len(head["decoders"]) == spec["bindingCount"] and head["totalClassBytes"] <= 329162
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == spec["bindingCount"] + 94
    assert decoded["lifecycle"] == 3 and decoded["javaKind"] == 0 and decoded["javaRef"] == head["javaRef"]
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
            "javaClass": "java/lang/IndexOutOfBoundsException"}
uncaught_baseline = None
uncaught_row = {}
for quantum in (4096,):
    value = finish_uncaught("index-out-of-bounds-string-uncaught", "index-out-of-bounds-string-uncaught", quantum)
    uncaught_row["direct" if quantum == 4096 else "q" + str(quantum)] = value
    if uncaught_baseline is None:
        uncaught_baseline = value
    else:
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps", "javaClass"):
            assert value[key] == uncaught_baseline[key], ("index-out-of-bounds-string-uncaught", key, value, uncaught_baseline)
rows["index-out-of-bounds-string-uncaught"] = uncaught_row

# No Throwable/cause overloads are added. These Java-8-valid RuntimeException
# constructors must remain ordinary atomic member-resolution refusals.
for label in ("runtime-exception-throwable-omitted", "runtime-exception-message-throwable-omitted"):
    world = out / ("world-" + label)
    run(label, [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
    rows[label] = refusal

# Canonically re-encode every successful EVM public receipt (including reopen
# chains); this independent Node verifier has no Java or artifact authority.
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels])
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
whole_gate_seconds = time.monotonic() - started
assert whole_gate_seconds <= 1200, whole_gate_seconds
summary = {"profile": "MC-SYSTEM-SET-OUT-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only canonical bootstrap image44 changes. Binding16 resolves exactly public static native System.setOut(PrintStream), then mutates canonical initialized System.out only; System.err and every other static remain unchanged. No SecurityManager permission, host stdout/stderr, forwarding, console, file, or provider behavior exists. Raw52/329162, diagnostic146, 94 images, native16, String-local11, exception14, frame/checkpoint/selected-resource limits, toolchain, and runtime-derived ordered-root rules remain pinned. The setOut identity/err/null/reset/subclass witness runs q1/q7/direct/reopen; retained generated controls run direct/reopen under the fixed 1200-second whole-gate bound. No original artifact/JAR/resource, world, EULA, or Done input or claim exists. Parent replay remains deferred."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
