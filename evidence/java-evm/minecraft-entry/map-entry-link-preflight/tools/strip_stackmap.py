#!/usr/bin/env python3
"""Remove only Code-local StackMapTable attributes from a generated classfile.

The bounded EVM class parser never reads StackMapTable.  This preserves every
constant-pool item, field, method header, Code byte, exception table, and every
other attribute while reclaiming the measured bootstrap-image space required by
the append(char) method.  It accepts only the trusted generated StringBuilder
source emitted by this stage's pinned Java 8 compiler.
"""
from pathlib import Path
import hashlib
import json
import sys


def _u2(data, offset):
    return int.from_bytes(data[offset:offset + 2], "big")


def _u4(data, offset):
    return int.from_bytes(data[offset:offset + 4], "big")


def strip_stackmap(data):
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a classfile")
    pos = 8
    count = _u2(data, pos)
    pos += 2
    cp = [None] * count
    index = 1
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = _u2(data, pos)
            pos += 2
            cp[index] = data[pos:pos + size].decode("utf-8")
            pos += size
        elif tag in (3, 4):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            pos += 2
        elif tag in (9, 10, 11, 12, 18):
            pos += 4
        elif tag == 15:
            pos += 3
        else:
            raise ValueError("unsupported constant-pool tag %d" % tag)
        index += 1

    # Retain class header, interfaces, and fields byte-for-byte.
    pos += 6
    interfaces = _u2(data, pos)
    pos += 2 + 2 * interfaces
    fields = _u2(data, pos)
    pos += 2
    for _ in range(fields):
        pos += 6
        attributes = _u2(data, pos)
        pos += 2
        for _ in range(attributes):
            pos += 6 + _u4(data, pos + 2)

    methods_count_at = pos
    methods = _u2(data, pos)
    pos += 2
    rewritten = []
    removed = 0
    for _ in range(methods):
        header = data[pos:pos + 6]
        pos += 6
        attributes = _u2(data, pos)
        pos += 2
        kept = []
        for _ in range(attributes):
            name_index = _u2(data, pos)
            length = _u4(data, pos + 2)
            body = data[pos + 6:pos + 6 + length]
            pos += 6 + length
            if cp[name_index] != "Code":
                kept.append((name_index, body))
                continue
            code_length = _u4(body, 4)
            cursor = 8 + code_length
            exceptions = _u2(body, cursor)
            cursor += 2 + 8 * exceptions
            nested = _u2(body, cursor)
            cursor += 2
            nested_kept = []
            for _ in range(nested):
                nested_name = _u2(body, cursor)
                nested_length = _u4(body, cursor + 2)
                nested_body = body[cursor + 6:cursor + 6 + nested_length]
                cursor += 6 + nested_length
                if cp[nested_name] == "StackMapTable":
                    removed += 6 + nested_length
                else:
                    nested_kept.append((nested_name, nested_body))
            if cursor != len(body):
                raise ValueError("malformed Code attribute")
            prefix = body[:8 + code_length + 2 + 8 * exceptions]
            body = prefix + len(nested_kept).to_bytes(2, "big") + b"".join(
                name.to_bytes(2, "big") + len(item).to_bytes(4, "big") + item
                for name, item in nested_kept
            )
            kept.append((name_index, body))
        rewritten.append((header, kept))

    result = data[:methods_count_at + 2] + b"".join(
        header + len(attributes).to_bytes(2, "big") + b"".join(
            name.to_bytes(2, "big") + len(body).to_bytes(4, "big") + body
            for name, body in attributes
        )
        for header, attributes in rewritten
    ) + data[pos:]
    return result, removed


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: strip_stackmap.py INPUT.class OUTPUT.class")
    source = Path(sys.argv[1]).read_bytes()
    cleaned, removed = strip_stackmap(source)
    Path(sys.argv[2]).write_bytes(cleaned)
    print(json.dumps({
        "inputBytes": len(source), "outputBytes": len(cleaned), "removedBytes": removed,
        "inputSHA256": hashlib.sha256(source).hexdigest(),
        "outputSHA256": hashlib.sha256(cleaned).hexdigest(),
    }, indent=2))
