#!/usr/bin/env python3
"""Generate Java-8 classfile-only fixtures for the raw72/q65536 gates.

The host invokes javac but never runs a generated guest class. Padding witnesses
are valid unknown class attributes on generated classfiles; their contents are
opaque zeros and are consumed only by the EVM classfile parser.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-raw72-q65536-fixtures-")
assert not OUT.exists(), "fixture outputs are append-only"

SOURCE = STAGE / "fixtures/java/generated"
CLASSES = OUT / "classes"
CLASSES.mkdir(parents=True)
SOURCES = sorted(SOURCE.glob("*.java"))
aux = []
for i in range(72):
    p = OUT / "generated-sources" / f"Raw72Aux{i:02d}.java"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"package generated; public final class Raw72Aux{i:02d} {{}}\n")
    aux.append(p)
cmd = ["javac", "--release", "8", "-g:none", "-d", str(CLASSES), *map(str, SOURCES), *map(str, aux)]
subprocess.run(cmd, cwd=ROOT, check=True)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


def classfile_cp_end(blob: bytes) -> tuple[int, int]:
    if blob[:4] != bytes.fromhex("cafebabe"):
        raise ValueError("bad class magic")
    cp_count = int.from_bytes(blob[8:10], "big")
    at = 10
    i = 1
    while i < cp_count:
        tag = blob[at]
        at += 1
        if tag == 1:
            n = int.from_bytes(blob[at:at + 2], "big")
            at += 2 + n
        elif tag in (3, 4):
            at += 4
        elif tag in (5, 6):
            at += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            at += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            at += 4
        elif tag == 15:
            at += 3
        else:
            raise ValueError(f"unsupported fixture CP tag {tag}")
        i += 1
    if at > len(blob):
        raise ValueError("truncated constant pool")
    return cp_count, at


def skip_attributes(blob: bytes, at: int) -> int:
    n = int.from_bytes(blob[at:at + 2], "big")
    at += 2
    for _ in range(n):
        length = int.from_bytes(blob[at + 2:at + 6], "big")
        at += 6 + length
        if at > len(blob):
            raise ValueError("truncated member attribute")
    return at


def class_attribute_count_offset(blob: bytes, cp_end: int) -> int:
    at = cp_end + 6
    interfaces = int.from_bytes(blob[at:at + 2], "big")
    at += 2 + 2 * interfaces
    for _ in range(2):  # fields, methods
        n = int.from_bytes(blob[at:at + 2], "big")
        at += 2
        for _ in range(n):
            at += 6
            at = skip_attributes(blob, at)
    return at


def pad_class(blob: bytes, target_size: int) -> bytes:
    if target_size < len(blob):
        raise ValueError("padding target below input")
    cp_count, cp_end = classfile_cp_end(blob)
    attr_name = b"Raw72Padding"
    cp_entry = b"\x01" + len(attr_name).to_bytes(2, "big") + attr_name
    attr_overhead = 6
    extra = target_size - len(blob)
    payload_len = extra - len(cp_entry) - attr_overhead
    if payload_len < 0:
        raise ValueError("target too small for padding attribute")
    rest = bytearray(blob[cp_end:])
    count_at = class_attribute_count_offset(blob, cp_end) - cp_end
    count = int.from_bytes(rest[count_at:count_at + 2], "big")
    if count == 65535:
        raise ValueError("class attribute count overflow")
    rest[count_at:count_at + 2] = (count + 1).to_bytes(2, "big")
    attr = cp_count.to_bytes(2, "big") + payload_len.to_bytes(4, "big") + bytes(payload_len)
    out = blob[:8] + (cp_count + 1).to_bytes(2, "big") + blob[10:cp_end] + cp_entry + rest + attr
    assert len(out) == target_size
    return out


names = ["generated/Raw72Main.class"] + [f"generated/Raw72Aux{i:02d}.class" for i in range(72)]
raw73 = {name: (CLASSES / name).read_bytes() for name in names}
raw72_names = names[:72]
raw71_names = names[:71]
raw72 = {name: raw73[name] for name in raw72_names}
raw71 = {name: raw73[name] for name in raw71_names}
write_zip(OUT / "raw73.zip", raw73)
write_zip(OUT / "raw72.zip", raw72)
write_zip(OUT / "raw71.zip", raw71)

loop_name = "generated/QuantumLoop.class"
loop = {loop_name: (CLASSES / loop_name).read_bytes()}
write_zip(OUT / "quantum-loop.zip", loop)

base_total = sum(map(len, raw72.values()))
byte_witnesses = {}
for target in (513384, 513385):
    padded = dict(raw72)
    delta = target - base_total
    if delta <= 0:
        raise ValueError("generated base bundle unexpectedly exceeds boundary")
    # Keep Raw72Main untouched; distribute opaque padding over unused classes.
    for name in names[1:]:
        if delta == 0:
            break
        room = 262144 - len(padded[name])
        add = min(delta, room)
        if add:
            padded[name] = pad_class(padded[name], len(padded[name]) + add)
            delta -= add
    if delta:
        raise ValueError(f"could not distribute exact byte witness; remaining={delta}")
    assert sum(map(len, padded.values())) == target
    assert all(0 < len(data) <= 262144 for data in padded.values())
    label = f"raw72-{target}"
    write_zip(OUT / f"{label}.zip", padded)
    byte_witnesses[str(target)] = {
        "zip": f"{label}.zip",
        "entryClass": "generated/Raw72Main",
        "bindingCount": 72,
        "totalClassBytes": sum(map(len, padded.values())),
        "classBytes": {name: len(data) for name, data in padded.items()},
        "classSHA256": {name: sha(data) for name, data in padded.items()},
        "zipSHA256": sha((OUT / f"{label}.zip").read_bytes()),
        "padding": "valid generated class-level Raw72Padding attribute with zero payload",
        "hostExecution": False,
    }

fixtures = {
    "schema": 1,
    "compiler": "javac --release 8 -g:none",
    "hostGuestExecution": False,
    "raw71": {
        "zip": "raw71.zip", "entryClass": "generated/Raw72Main", "bindingCount": 71,
        "totalClassBytes": sum(map(len, raw71.values())),
        "classBytes": {name: len(data) for name, data in raw71.items()},
        "classSHA256": {name: sha(data) for name, data in raw71.items()},
        "zipSHA256": sha((OUT / "raw71.zip").read_bytes()),
    },
    "raw72": {
        "zip": "raw72.zip", "entryClass": "generated/Raw72Main", "bindingCount": 72,
        "totalClassBytes": base_total,
        "classBytes": {name: len(data) for name, data in raw72.items()},
        "classSHA256": {name: sha(data) for name, data in raw72.items()},
        "zipSHA256": sha((OUT / "raw72.zip").read_bytes()),
    },
    "raw73": {
        "zip": "raw73.zip", "entryClass": "generated/Raw72Main", "bindingCount": 73,
        "totalClassBytes": sum(map(len, raw73.values())),
        "classBytes": {name: len(data) for name, data in raw73.items()},
        "classSHA256": {name: sha(data) for name, data in raw73.items()},
        "zipSHA256": sha((OUT / "raw73.zip").read_bytes()),
    },
    "quantumLoop": {
        "zip": "quantum-loop.zip", "entryClass": "generated/QuantumLoop", "bindingCount": 1,
        "totalClassBytes": len(loop[loop_name]), "classBytes": {loop_name: len(loop[loop_name])},
        "classSHA256": {loop_name: sha(loop[loop_name])},
        "zipSHA256": sha((OUT / "quantum-loop.zip").read_bytes()),
        "iterations": 819,
        "sourceSHA256": sha((SOURCE / "QuantumLoop.java").read_bytes()),
    },
    "byteWitnesses": byte_witnesses,
}
(OUT / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
(OUT / "bindings-raw71.txt").write_text(",".join(raw71_names) + "\n")
(OUT / "bindings-raw72.txt").write_text(",".join(raw72_names) + "\n")
(OUT / "bindings-raw73.txt").write_text(",".join(names) + "\n")
(OUT / "bindings-quantum-loop.txt").write_text(loop_name + "\n")
print(json.dumps({"generatedOnly": True, "fixtures": fixtures}, indent=2))
