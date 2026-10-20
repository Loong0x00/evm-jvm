#!/usr/bin/env python3
"""Generate Java-8 classfile-only fixtures for raw73/516040 gates.

The host invokes javac but never runs a generated guest class. Exact byte-boundary
witnesses are valid unknown attributes added to generated classfiles; their zero
payload is parsed only by the guest EVM.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-raw73-byte516040-fixtures-")
assert not OUT.exists(), "fixture outputs are append-only"

SOURCE = STAGE / "fixtures/java/generated"
CLASSES = OUT / "classes"
CLASSES.mkdir(parents=True)
SOURCES = sorted(SOURCE.glob("*.java"))
aux = []
for i in range(73):
    p = OUT / "generated-sources" / f"Raw73Aux{i:02d}.java"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"package generated; public final class Raw73Aux{i:02d} {{}}\n")
    aux.append(p)
subprocess.run(["javac", "--release", "8", "-g:none", "-d", str(CLASSES),
                *map(str, SOURCES), *map(str, aux)], cwd=ROOT, check=True)


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def classfile_cp_end(blob: bytes) -> tuple[int, int]:
    if blob[:4] != bytes.fromhex("cafebabe"):
        raise ValueError("bad class magic")
    cp_count = int.from_bytes(blob[8:10], "big")
    at, i = 10, 1
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
    for _ in range(2):
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
    attr_name = b"Raw73Padding"
    cp_entry = b"\x01" + len(attr_name).to_bytes(2, "big") + attr_name
    extra = target_size - len(blob)
    payload_len = extra - len(cp_entry) - 6
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


names = ["generated/Raw72Main.class"] + [f"generated/Raw73Aux{i:02d}.class" for i in range(73)]
classes = {name: (CLASSES / name).read_bytes() for name in names}
bundles = {n: dict(list(classes.items())[:n]) for n in (71, 72, 73, 74)}
for count, entries in bundles.items():
    write_zip(OUT / f"raw{count}.zip", entries)

loop_name = "generated/QuantumLoop.class"
loop = {loop_name: (CLASSES / loop_name).read_bytes()}
write_zip(OUT / "quantum-loop.zip", loop)

byte_witnesses = {}
base_total = sum(map(len, bundles[73].values()))
for target in (516040, 516041):
    padded = dict(bundles[73])
    delta = target - base_total
    if delta <= 0:
        raise ValueError("generated base bundle unexpectedly exceeds boundary")
    for name in names[1:73]:
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
    label = f"raw73-{target}"
    write_zip(OUT / f"{label}.zip", padded)
    byte_witnesses[str(target)] = {
        "zip": f"{label}.zip", "entryClass": "generated/Raw72Main", "bindingCount": 73,
        "totalClassBytes": sum(map(len, padded.values())),
        "classBytes": {name: len(data) for name, data in padded.items()},
        "classSHA256": {name: sha(data) for name, data in padded.items()},
        "zipSHA256": sha((OUT / f"{label}.zip").read_bytes()),
        "padding": "valid generated class-level Raw73Padding attribute with zero payload",
        "hostExecution": False,
    }

fixtures = {
    "schema": 1,
    "compiler": "javac --release 8 -g:none",
    "hostGuestExecution": False,
    **{
        f"raw{count}": {
            "zip": f"raw{count}.zip", "entryClass": "generated/Raw72Main", "bindingCount": count,
            "totalClassBytes": sum(map(len, entries.values())),
            "classBytes": {name: len(data) for name, data in entries.items()},
            "classSHA256": {name: sha(data) for name, data in entries.items()},
            "zipSHA256": sha((OUT / f"raw{count}.zip").read_bytes()),
        }
        for count, entries in bundles.items()
    },
    "quantumLoop": {
        "zip": "quantum-loop.zip", "entryClass": "generated/QuantumLoop", "bindingCount": 1,
        "totalClassBytes": len(loop[loop_name]), "classBytes": {loop_name: len(loop[loop_name])},
        "classSHA256": {loop_name: sha(loop[loop_name])},
        "zipSHA256": sha((OUT / "quantum-loop.zip").read_bytes()), "iterations": 819,
        "sourceSHA256": sha((SOURCE / "QuantumLoop.java").read_bytes()),
    },
    "byteWitnesses": byte_witnesses,
}
(OUT / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
for count, entries in bundles.items():
    (OUT / f"bindings-raw{count}.txt").write_text(",".join(entries) + "\n")
(OUT / "bindings-quantum-loop.txt").write_text(loop_name + "\n")
print(json.dumps({"generatedOnly": True, "fixtures": fixtures}, indent=2))
