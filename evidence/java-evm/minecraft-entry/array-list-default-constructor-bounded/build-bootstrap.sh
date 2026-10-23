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
python3 - "$OUT/java/util/ArrayList.class" "$ROOT/ArrayList.class.hex" <<'PY'
import hashlib,pathlib,sys
raw=pathlib.Path(sys.argv[1]).read_bytes()
assert raw[:8] == bytes.fromhex('cafebabe00000034'), raw[:8].hex()
pathlib.Path(sys.argv[2]).write_text(raw.hex()+'\n')
print(f'Java8 class bytes={len(raw)} sha256={hashlib.sha256(raw).hexdigest()}')
PY
javap -c -p "$OUT/java/util/ArrayList.class" > "$ROOT/build/repro-javap.txt"
