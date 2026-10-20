#!/usr/bin/env python3
"""Read-only MR01 wire diagnostics; no checkpoint output is execution authority."""
import hashlib
import json
import sys
from pathlib import Path

SPARSE = 1 << 31
PACKED_FLOAT = 1 << 30
COUNT_MASK = (1 << 30) - 1


def inspect(blob):
    assert 280 < len(blob) <= 1048576
    at = 280

    def data(n):
        nonlocal at
        assert 0 <= n <= len(blob) - at
        out = blob[at:at+n]
        at += n
        return out

    def u(n):
        return int.from_bytes(data(n), "big")

    assert data(4) == b"MR01"
    lifecycle, result, kind, ref = u(1), u(4), u(1), u(4)
    jvm, internal, root_kind = u(8), u(8), u(1)
    assert root_kind == 1
    commitment = data(32).hex()
    entry_class = data(u(2)).decode()
    method = data(u(2)).decode()
    argc = u(1)
    assert argc == 0
    classes = u(2)
    assert classes <= 170
    states = []
    for i in range(classes):
        state, started, n = u(1), u(1), u(2)
        values = [{"fieldIndex": u(2), "packedValue": hex(u(32))} for _ in range(n)]
        if state or started:
            states.append({"classIndex": i, "state": state, "initializerStarted": started,
                           "staticFields": n, "staticValues": values})
    depth = u(2)
    assert depth <= 128
    frames = []
    for _ in range(depth):
        c, m, pc, callpc = u(2), u(2), u(4), u(32)
        flags, receiver, sp = u(1), u(4), u(2)
        data(sp * 32)
        locals_count = u(2)
        data((locals_count + 7) // 8 + locals_count * 32)
        frames.append({"classIndex": c, "methodIndex": m, "pc": pc, "callPC": hex(callpc),
                       "flags": flags, "receiver": receiver, "stackSize": sp, "locals": locals_count})
    next_handle = u(4)
    ordinary_objects, ordinary_arrays = u(2), u(2)
    array_elements, ordinary_fields, emergency = u(4), u(4), u(4)
    exception_objects, exception_fields = u(2), u(4)
    heap = []
    for expected in range(1, next_handle + 1):
        record_start = at
        ordinal, metadata, class_index, rank = u(4), u(32), u(2), u(1)
        count_offset = at
        wire_count = u(4)
        assert ordinal == expected
        is_object = (metadata >> 255) != 0
        sparse = not is_object and (wire_count & SPARSE) != 0
        packed_float = not is_object and (wire_count & PACKED_FLOAT) != 0
        assert not (sparse and packed_float)
        count = (wire_count & COUNT_MASK) if (sparse or packed_float) else wire_count
        sparse_count = 0
        sparse_count_offset = None
        sparse_cells = []
        packed_cells = []
        if sparse:
            sparse_count_offset = at
            sparse_count = u(4)
            for _ in range(sparse_count):
                index_offset = at
                index = u(4)
                value_offset = at
                value = u(8)
                sparse_cells.append({"index": index, "value": hex(value),
                                     "indexOffset": index_offset, "valueOffset": value_offset})
            cells = []
        elif packed_float:
            cells = []
            for index in range(count):
                value_offset = at
                value = u(4)
                cell = {"index": index, "value": hex(value), "valueOffset": value_offset}
                packed_cells.append(cell)
                cells.append(hex(value))
        else:
            width = 32 if is_object else 8
            cells = [hex(u(width)) for _ in range(count)]
        heap.append({"handle": ordinal, "metadata": hex(metadata), "classIndex": class_index,
                     "rank": rank, "count": count, "cells": cells, "sparse": sparse,
                     "packedFloat": packed_float, "sparseCount": sparse_count,
                     "sparseCountOffset": sparse_count_offset, "sparseCells": sparse_cells,
                     "packedCells": packed_cells, "recordStart": record_start,
                     "countOffset": count_offset, "wireCount": wire_count, "recordEnd": at})
    return {"checkpointSHA256": hashlib.sha256(blob).hexdigest(), "lifecycle": lifecycle,
            "result": result, "javaKind": kind, "javaRef": ref, "javaSteps": jvm,
            "internalSteps": internal, "rootKind": root_kind, "argsCommitment": commitment,
            "entryClass": entry_class, "entryMethod": method, "classCount": classes,
            "initialization": states, "frames": frames, "nextHandle": next_handle,
            "heap": heap, "heapCounts": {"ordinaryObjects": ordinary_objects,
            "ordinaryArrays": ordinary_arrays, "arrayElements": array_elements,
            "ordinaryFields": ordinary_fields, "emergency": emergency,
            "exceptionObjects": exception_objects, "exceptionFields": exception_fields},
            "scope": "diagnostic transport metadata only; no execution authority or evaluation"}


if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()), indent=2))
