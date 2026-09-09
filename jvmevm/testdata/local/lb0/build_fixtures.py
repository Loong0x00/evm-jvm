#!/usr/bin/env python3
"""Rebuild the trusted MC-LB0 class images with javac 21 --release 8.

The two field-owner images are bounded raw fixtures. They preserve javac's
ConstantValue attribute while changing only the field access flags. Consumers
were compiled independently against the resulting static/non-static shape.
"""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "classes"

version = subprocess.run(["javac", "-version"], check=True, capture_output=True, text=True).stdout.strip()
if version != "javac 21.0.9":
    raise SystemExit(f"fixture rebuild requires javac 21.0.9, got {version!r}")


def run_javac(out, paths):
    subprocess.run(["javac", "-J-Xmx64m", "--release", "8", "-g:none", "-d", str(out), *map(str, paths)], check=True)


def cp_end(data):
    pos = 10
    count = struct.unpack_from(">H", data, 8)[0]
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = struct.unpack_from(">H", data, pos)[0]
            pos += 2 + size
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        else:
            raise ValueError(f"unexpected CP tag {tag} at {pos - 1}")
        i += 1
    return pos


def mutate_only_field_flags(path, clear):
    data = bytearray(path.read_bytes())
    pos = cp_end(data) + 6
    interfaces = struct.unpack_from(">H", data, pos)[0]
    pos += 2 + 2 * interfaces
    fields = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    if fields != 1:
        raise ValueError(f"{path}: got {fields} fields, want one")
    flags = struct.unpack_from(">H", data, pos)[0]
    struct.pack_into(">H", data, pos, flags & ~clear)
    return bytes(data)


with tempfile.TemporaryDirectory(prefix="mclb0-") as tmp:
    tmp = Path(tmp)
    core = tmp / "core"
    core.mkdir()
    run_javac(core, sorted((ROOT / "src").glob("*.java")))

    sf, sc, inf, inc = (tmp / n for n in ("sf", "sc", "inf", "inc"))
    for directory in (sf, sc, inf, inc):
        directory.mkdir()
    run_javac(sf, [ROOT / "raw-src/static-final/MCLB0RawStatic.java"])
    run_javac(sc, sorted((ROOT / "raw-src/static-compile").glob("*.java")))
    run_javac(inf, [ROOT / "raw-src/instance-final/MCLB0RawInstance.java"])
    run_javac(inc, sorted((ROOT / "raw-src/instance-compile").glob("*.java")))

    images = {p.name: p.read_bytes() for p in core.glob("*.class")}
    images["MCLB0RawStatic.class"] = mutate_only_field_flags(sf / "MCLB0RawStatic.class", 0x0010)
    images["MCLB0RawStaticConsumer.class"] = (sc / "MCLB0RawStaticConsumer.class").read_bytes()
    images["MCLB0RawInstance.class"] = mutate_only_field_flags(inf / "MCLB0RawInstance.class", 0x0018)
    images["MCLB0RawInstanceConsumer.class"] = (inc / "MCLB0RawInstanceConsumer.class").read_bytes()

    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.class.hex"):
        old.unlink()
    for name, data in sorted(images.items()):
        (OUT / f"{name}.hex").write_text(data.hex() + "\n")
