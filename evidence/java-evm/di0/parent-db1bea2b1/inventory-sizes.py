"""STATIC size-only inventory of the pinned JAR; never runtime/extraction authority."""
import hashlib
import json
import struct
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes()
digest = hashlib.sha256(raw).hexdigest()
if len(raw) != 30222121 or digest != "fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e":
    raise SystemExit("wrong static input transport pin")
eocd = len(raw) - 22
assert raw[eocd:eocd + 4] == b"PK\x05\x06"
count = struct.unpack_from("<H", raw, eocd + 10)[0]
size, at = struct.unpack_from("<II", raw, eocd + 12)
end = at + size
rows = []
for _ in range(count):
    assert raw[at:at + 4] == b"PK\x01\x02"
    compressed, plain = struct.unpack_from("<II", raw, at + 20)
    nl, xl, cl = struct.unpack_from("<HHH", raw, at + 28)
    name = raw[at + 46:at + 46 + nl].decode("utf-8")
    rows.append(dict(name=name, compressed=compressed, declaredPlain=plain, **{"class": name.endswith(".class")}))
    at += 46 + nl + xl + cl
assert at == end == eocd
classes = [r for r in rows if r["class"]]
print(json.dumps(dict(
    scope="STATIC CEN size inventory only, no extraction/inflation/Java execution or runtime catalogue authority",
    inputHostSHA256=digest, entries=count, classCount=len(classes),
    totalDeclaredPlain=sum(r["declaredPlain"] for r in rows),
    totalClassDeclaredPlain=sum(r["declaredPlain"] for r in classes),
    over65536=sum(r["declaredPlain"] > 65536 for r in rows),
    classOver65536=sum(r["declaredPlain"] > 65536 for r in classes),
    largest=sorted(rows, key=lambda r: r["declaredPlain"], reverse=True)[:12],
    largestClasses=sorted(classes, key=lambda r: r["declaredPlain"], reverse=True)[:12],
), indent=2))
