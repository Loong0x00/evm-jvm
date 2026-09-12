#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=${1:?fresh ignored output path required}
case "$OUT" in "$ROOT"/build/java-diff-mc-main-entry-*) ;; *) exit 2;; esac
test ! -e "$OUT";mkdir -p "$OUT/tmp" "$OUT/results"
export TMPDIR="$OUT/tmp"
SRC="$ROOT/evidence/java-evm/main-entry/parent-c92f935c1"
python3 "$SRC/content/generate_fixture.py" "$OUT/fixture"
python3 "$SRC/repair_driver.py" "$OUT/main.go"
gofmt -w "$OUT/main.go"
(cd "$ROOT";go build -o "$OUT/driver" "$OUT/main.go";go vet "$OUT/main.go")
length=$(wc -c < "$OUT/fixture/main-entry-generated.zip")
for label in mode0-direct mode1-direct mode2-direct mode2-q7 mode3-null; do
 case "$label" in mode0*) mode=0;;mode1*)mode=1;;mode2*)mode=2;;mode3*)mode=3;;esac
 q=4096;test "$label" != mode2-q7 || q=7
 "$OUT/driver" -command setup -dir "$OUT/world-$label" -zip "$OUT/fixture/main-entry-generated.zip" -bad-package > "$OUT/results/$label-setup.json"
 for n in $(seq 1 256); do
  "$OUT/driver" -command slice -dir "$OUT/world-$label" -length "$length" -mode "$mode" -quantum "$q" > "$OUT/results/$label-$n.json"
  life=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["lifecycle"])' "$OUT/results/$label-$n.json")
  if test "$life" != 1;then break;fi
  test "$n" != 256
 done
 "$OUT/driver" -command terminal -dir "$OUT/world-$label" -length "$length" > "$OUT/results/$label-terminal.json"
done
python3 "$SRC/content/verify.py" "$OUT" > "$OUT/report.json"
cat "$OUT/report.json"
