# Current focused subtype proof: the real method descriptor accepts OutputStream,
# and virtual dispatch reaches only PrintStream.write(int)'s bounded low-char sink.
def _outputstream_printstream_heap(checkpoint, raw_count):
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
    assert raw_count == 1
    probe = statics[0]
    assert set(probe) == {0, 1, 2, 3}
    stream, output, line, result = probe[0], probe[1], probe[2], probe[3]
    assert stream == output and stream >> 64 == line >> 64 == 2
    assert result == (1 << 64) | 7
    handle = stream & ((1 << 64) - 1)
    assert handle and handle in heap
    meta, class_index, rank, cells = heap[handle]
    assert meta >> 255 == 1 and class_index == raw_count + 83 and rank == 0 and len(cells) == 2
    assert cells[0] == line and cells[1] == (1 << 64) | 0x34
    return {"streamHandle": handle, "linePacked": hex(line), "lowByteCharPacked": hex(cells[1]),
            "printStreamClass": class_index, "outputStreamClass": raw_count + 35}

def outputstream_printstream_initialized(decoded):
    raw = fixture("printstream-outputstream")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 35]["state"] == states[raw + 83]["state"] == 2

def q_outputstream_printstream():
    spec = fixture("printstream-outputstream")
    assert spec["entries"] == ["PrintStreamOutputStreamMain.class"]
    assert spec["bindingCount"] == 1 and spec["bootstrapCount"] == 94 and spec["java8HostOracle"] is False
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish("printstream-outputstream", "printstream-outputstream", quantum,
                       outputstream_printstream_initialized)
        world = out / value["world"]
        head = json.loads((world / "durable-head.json").read_text())
        checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        value.update(_outputstream_printstream_heap(checkpoint, spec["bindingCount"]))
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None:
            baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
                        "streamHandle", "linePacked", "lowByteCharPacked", "printStreamClass",
                        "outputStreamClass"):
                assert value[key] == baseline[key], ("printstream-outputstream", key, value, baseline)
    rows["printstream-outputstream"] = row

q_outputstream_printstream()

# The explicit no-use control is direct/reopen only and must not initialize either
# side of the new direct superclass edge.
value = finish("printstream-outputstream-uninitialized", "printstream-outputstream-uninitialized", 4096)
world = out / value["world"]
_, _, decoded = terminal(world, fixture("printstream-outputstream-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("printstream-outputstream-uninitialized")["bindingCount"]
assert raw + 35 not in states and raw + 83 not in states
rows["printstream-outputstream-uninitialized"] = value
