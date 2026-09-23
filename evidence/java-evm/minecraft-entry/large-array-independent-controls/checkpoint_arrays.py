#!/usr/bin/env python3
"""Read-only MR01 heap array summary; output is never execution/continuation input.

Understands the existing dense _encodeMachine array records only. It does not
parse/evaluate Java classfiles or ZIPs, reconstruct a machine, or validate the
remaining VFS/checkpoint suffix. A changed/unknown transport layout must be
reviewed and this diagnostic updated separately; malformed data is refused.
"""
import argparse
import hashlib
import json
from pathlib import Path

HEADER_BYTES = 280
MAX_CHECKPOINT_BYTES = 1_048_576
MAX_CLASSES = 256
MAX_FRAMES = 128
MAX_HANDLES = 4096
MAX_ARRAY_LENGTH = 65_536
FLOAT_LEAF = 0x46


class FormatError(ValueError):
    pass


class Reader:
    def __init__(self, blob):
        self.blob = blob
        self.at = HEADER_BYTES

    def take(self, size, label):
        if size < 0 or size > len(self.blob) - self.at:
            raise FormatError("truncated/unsupported MR01 transport at %s (offset %d)" % (label, self.at))
        start = self.at
        self.at += size
        return self.blob[start:self.at]

    def uint(self, size, label):
        return int.from_bytes(self.take(size, label), "big")

    def skip(self, size, label):
        self.take(size, label)


def inspect(blob, nonzero_limit=256):
    if len(blob) <= HEADER_BYTES or len(blob) > MAX_CHECKPOINT_BYTES:
        raise FormatError("checkpoint length outside supported MR01 bounds")
    r = Reader(blob)
    if r.take(4, "magic") != b"MR01":
        raise FormatError("unknown machine transport magic; only dense MR01 is supported")
    lifecycle = r.uint(1, "lifecycle")
    result = r.uint(4, "result")
    java_kind = r.uint(1, "java kind")
    java_ref = r.uint(4, "java ref")
    java_steps = r.uint(8, "Java steps")
    internal_steps = r.uint(8, "internal steps")
    root_kind = r.uint(1, "root kind")
    commitment = r.take(32, "argument commitment").hex()
    entry_len = r.uint(2, "entry class length")
    entry_class = r.take(entry_len, "entry class").decode("ascii")
    method_len = r.uint(2, "entry method length")
    entry_method = r.take(method_len, "entry method").decode("ascii")
    argc = r.uint(1, "argument count")
    if argc > 8:
        raise FormatError("argument count exceeds diagnostic bound")
    r.skip(argc * 4, "int arguments")

    class_count = r.uint(2, "class count")
    if class_count > MAX_CLASSES:
        raise FormatError("class count exceeds diagnostic bound")
    for class_no in range(class_count):
        r.skip(2, "class state %d" % class_no)
        statics = r.uint(2, "static count %d" % class_no)
        r.skip(statics * 34, "static values %d" % class_no)

    frame_count = r.uint(2, "frame count")
    if frame_count > MAX_FRAMES:
        raise FormatError("frame count exceeds diagnostic bound")
    for frame_no in range(frame_count):
        # class, method, PC, call PC, flags and receiver occupy 45 bytes;
        # the following uint16 is the operand-stack word count.
        r.skip(45, "frame header %d" % frame_no)
        stack_words = r.uint(2, "frame stack count %d" % frame_no)
        r.skip(stack_words * 32, "frame stack %d" % frame_no)
        local_count = r.uint(2, "frame local count %d" % frame_no)
        r.skip((local_count + 7) // 8 + local_count * 32, "frame locals %d" % frame_no)

    next_handle = r.uint(4, "next handle")
    if next_handle > MAX_HANDLES:
        raise FormatError("handle count exceeds diagnostic bound")
    heap_counts = {
        "ordinaryObjects": r.uint(2, "ordinary object count"),
        "ordinaryArrays": r.uint(2, "ordinary array count"),
        "arrayElements": r.uint(4, "array element count"),
        "ordinaryFields": r.uint(4, "ordinary field count"),
        "emergencyHandle": r.uint(4, "emergency handle"),
        "exceptionObjects": r.uint(2, "exception object count"),
        "exceptionFields": r.uint(4, "exception field count"),
    }
    arrays = []
    total_nonzero = 0
    for expected_handle in range(1, next_handle + 1):
        handle = r.uint(4, "heap handle")
        metadata = r.uint(32, "heap metadata")
        class_index = r.uint(2, "heap class index")
        rank = r.uint(1, "heap array rank")
        length = r.uint(4, "heap cell count")
        if handle != expected_handle:
            raise FormatError("noncanonical heap ordinal at handle %d" % expected_handle)
        # Object metadata has bit 255 set and fields are 32-byte cells. Arrays
        # have that bit clear and store each ordinary cell as a uint64.
        is_array = (metadata >> 255) == 0
        if is_array:
            if metadata == 0 or rank == 0 or length > MAX_ARRAY_LENGTH:
                raise FormatError("invalid array metadata/length at handle %d" % handle)
            leaf = metadata
            nonzero = []
            count_nonzero = 0
            for index in range(length):
                cell = r.uint(8, "array cell handle %d index %d" % (handle, index))
                if cell != 0:
                    count_nonzero += 1
                    if len(nonzero) < nonzero_limit:
                        nonzero.append({"index": index, "rawCell": "0x%016x" % cell})
            total_nonzero += count_nonzero
            arrays.append({
                "handle": handle,
                "rank": rank,
                "leafMetadata": "0x%x" % leaf,
                "leafKind": "float" if rank == 1 and leaf == FLOAT_LEAF else None,
                "classIndex": class_index,
                "length": length,
                "nonzeroCount": count_nonzero,
                "nonzeroPositionsTruncated": count_nonzero > len(nonzero),
                "nonzero": nonzero,
            })
        else:
            r.skip(length * 32, "object fields handle %d" % handle)

    return {
        "checkpointSHA256": hashlib.sha256(blob).hexdigest(),
        "checkpointBytes": len(blob),
        "transport": "MR01 dense array record diagnostic",
        "lifecycle": lifecycle,
        "result": result,
        "javaKind": java_kind,
        "javaRef": java_ref,
        "javaSteps": java_steps,
        "internalSteps": internal_steps,
        "rootKind": root_kind,
        "argsCommitment": commitment,
        "entryClass": entry_class,
        "entryMethod": entry_method,
        "classCount": class_count,
        "nextHandle": next_handle,
        "heapCounts": heap_counts,
        "arrayCount": len(arrays),
        "totalNonzeroArrayCells": total_nonzero,
        "arrays": arrays,
        "scope": "read-only partial transport diagnostics through heap records; not canonicality validation, guest execution, authority, or continuation input",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="an existing opaque public checkpoint blob")
    parser.add_argument("--max-nonzero", type=int, default=256,
                        help="maximum positions emitted per array (default: 256)")
    args = parser.parse_args()
    if args.max_nonzero < 0 or args.max_nonzero > MAX_ARRAY_LENGTH:
        parser.error("--max-nonzero must be in 0..65536")
    size = args.checkpoint.stat().st_size
    if size <= HEADER_BYTES or size > MAX_CHECKPOINT_BYTES:
        parser.error("input file size outside supported MR01 checkpoint bounds")
    blob = args.checkpoint.read_bytes()
    try:
        report = inspect(blob, args.max_nonzero)
    except (FormatError, UnicodeDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
