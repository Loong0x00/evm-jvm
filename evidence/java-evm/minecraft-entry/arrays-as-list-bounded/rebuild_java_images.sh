#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:?pass a new, empty output directory under this candidate}
mkdir -p "$OUT"
/usr/lib/jvm/java-8-openjdk/bin/javac -version > "$OUT/javac-version.txt" 2>&1
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 \
  -bootclasspath /usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar \
  -d "$OUT" $(find "$ROOT/bootstrap/java/util" -name '*.java' -print | sort)
for pair in \
  'Arrays:java/util/Arrays.class' \
  'Arrays$ArrayList:java/util/Arrays$ArrayList.class' \
  'Arrays$ArrayIterator:java/util/Arrays$ArrayIterator.class'; do
  name=${pair%%:*}; rel=${pair#*:}
  cmp "$OUT/$rel" "$ROOT/build/classes-v3/$rel"
  printf '%s %s\n' "$name" "$(sha256sum "$OUT/$rel" | awk '{print $1}')"
done > "$OUT/verified-images.txt"
cat "$OUT/javac-version.txt" "$OUT/verified-images.txt"
