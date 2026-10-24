#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVAC=/usr/lib/jvm/java-8-openjdk/bin/javac
OUT="$ROOT/build/repro-classes"
mkdir -p "$OUT"
"$JAVAC" -source 8 -target 8 -g:none -d "$OUT" \
  "$ROOT"/compiler-support/java/util/*.java \
  "$ROOT/bootstrap/java/util/AbstractCollection.java" \
  "$ROOT/bootstrap/java/util/AbstractList.java" \
  "$ROOT/bootstrap/java/util/ArrayList.java"
python3 - "$OUT" "$ROOT" <<'PY'
import hashlib,pathlib,sys
out,root=map(pathlib.Path,sys.argv[1:])
p=out/'java/util/ArrayList.class'; b=p.read_bytes()
assert b[:8]==bytes.fromhex('cafebabe00000034')
(root/'ArrayList.class.hex').write_text(b.hex()+'\n')
print(f'ArrayList.class: bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}')
PY
javap -c -p -s "$OUT/java/util/ArrayList.class" > "$ROOT/build/ArrayList.javap.txt"
chmod 0644 "$ROOT/ArrayList.class.hex" "$ROOT/build/ArrayList.javap.txt"
