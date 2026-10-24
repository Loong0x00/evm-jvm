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
for name in ('ArrayList.class','ArrayList$Itr.class'):
 raw=(out/'java/util'/name).read_bytes()
 assert raw[:8]==bytes.fromhex('cafebabe00000034')
 if name=='ArrayList.class': (root/'ArrayList.class.hex').write_text(raw.hex()+'\n')
 print(f'{name}: bytes={len(raw)} sha256={hashlib.sha256(raw).hexdigest()}')
PY
javap -c -p "$OUT/java/util/ArrayList.class" > "$ROOT/build/ArrayList.javap.txt"
javap -c -p "$OUT/java/util/ArrayList\$Itr.class" > "$ROOT/build/ArrayList-Itr.javap.txt"
