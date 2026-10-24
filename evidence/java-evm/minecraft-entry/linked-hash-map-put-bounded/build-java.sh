#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?Pass a fresh output directory; historical builds are never overwritten}"
test ! -e "$OUT"
mkdir -p "$OUT/context/java/util" "$OUT/classes"
cp "$ROOT"/bootstrap/java/util/*.java "$OUT/context/java/util/"
# Compile context only. Existing images are never embedded from these outputs.
# Drop annotations requiring unadmitted Map defaults, not privacy/finality or method declarations.
python3 - "$OUT/context/java/util/HashMap.java" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);p.write_text(p.read_text().replace('@Override',''))
PY
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 \
  -d "$OUT/classes" "$OUT"/context/java/util/*.java
python3 - "$ROOT" "$OUT" <<'PY'
from pathlib import Path
import sys,hashlib
root,out=map(Path,sys.argv[1:])
for n in ('LinkedHashMap','LinkedHashMapEntry','LinkedHashMapEntrySet','LinkedHashMapEntryIterator'):
 b=(out/'classes/java/util'/(n+'.class')).read_bytes()
 assert b.hex()==(root/'bootstrap/java/util'/(n+'.class.hex')).read_text().strip(),n
 print(n,len(b),hashlib.sha256(b).hexdigest())
PY
