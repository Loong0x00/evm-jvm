#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
JDK8=${JDK8:-/usr/lib/jvm/java-8-openjdk}
RT="$JDK8/jre/lib/rt.jar"
mkdir -p "$ROOT/bootstrap/classes" "$ROOT/tests/classes" "$ROOT/tests-src/fillers"
for i in $(seq 0 148); do
  name="EnumMapLinkFiller$(printf '%03d' "$i")"
  printf 'public final class %s {}\n' "$name" > "$ROOT/tests-src/fillers/$name.java"
done
"$JDK8/bin/javac" -source 8 -target 8 -bootclasspath "$RT" -d "$ROOT/bootstrap/classes" \
  "$ROOT/bootstrap/java/util/Map.java" "$ROOT/bootstrap/java/util/AbstractMap.java" \
  "$ROOT/bootstrap/java/util/EnumMap.java"
"$JDK8/bin/javac" -source 8 -target 8 -bootclasspath "$RT" -d "$ROOT/tests/classes" \
  "$ROOT/tests-src/EnumMapTypeLinkProbe.java" "$ROOT/tests-src/fillers/"*.java
"$JDK8/bin/java" -cp "$ROOT/tests/classes" EnumMapTypeLinkProbe
"$JDK8/bin/javap" -p -verbose "$ROOT/bootstrap/classes/java/util/EnumMap.class" > "$ROOT/tests/EnumMap.javap.txt"
"$JDK8/bin/javap" -classpath "$ROOT/tests/classes" -c -verbose EnumMapTypeLinkProbe > "$ROOT/tests/EnumMapTypeLinkProbe.javap.txt"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys, zipfile
root=Path(sys.argv[1]); names=['EnumMapTypeLinkProbe.class']+[f'EnumMapLinkFiller{i:03d}.class' for i in range(149)]
(root/'tests/bindings.txt').write_text(''.join(n+'\n' for n in names))
with zipfile.ZipFile(root/'tests/generated-probe.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for n in names:
        info=zipfile.ZipInfo(n,(2020,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16
        z.writestr(info,(root/'tests/classes'/n).read_bytes())
PY
