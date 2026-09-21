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
