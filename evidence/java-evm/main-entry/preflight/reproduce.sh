#!/bin/sh
# Fresh-output-only replay; all transient compiler/temp files remain under ignored build/.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
OUT=${1:?usage: reproduce.sh NEW-ignored-output-dir}
case "$OUT" in "$ROOT"/build/java-diff-mc-main-entry-*) ;; *) echo "OUT must be a fresh ignored build/java-diff-mc-main-entry-* path" >&2; exit 2;; esac
[ ! -e "$OUT" ] || { echo "refusing existing output: $OUT" >&2; exit 2; }
mkdir -p "$OUT/tmp" "$OUT/results"
export TMPDIR="$OUT/tmp"
python3 "$ROOT/evidence/java-evm/main-entry/preflight/generate_fixture.py" "$OUT/fixture" >"$OUT/generate.log" 2>&1
cp "$ROOT/evidence/java-evm/main-entry/preflight/driver.go.txt" "$OUT/main.go"
gofmt -w "$OUT/main.go"
(cd "$ROOT" && go build -o "$OUT/driver" "$OUT/main.go")
LENGTH=$(wc -c < "$OUT/fixture/main-entry-generated.zip" | tr -d ' ')
run_world() {
  label=$1 mode=$2 quantum=$3
  world="$OUT/world-$label"
  "$OUT/driver" -dir "$world" -zip "$OUT/fixture/main-entry-generated.zip" -command setup >"$OUT/results/$label-setup.json"
  n=0
  while :; do
    n=$((n+1)); [ "$n" -le 256 ] || { echo "slice bound exceeded" >&2; exit 1; }
    "$OUT/driver" -dir "$world" -length "$LENGTH" -command slice -mode "$mode" -quantum "$quantum" >"$OUT/results/$label-$n.json"
    life=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lifecycle"])' "$OUT/results/$label-$n.json")
    [ "$life" = 1 ] || break
  done
  "$OUT/driver" -dir "$world" -length "$LENGTH" -command terminal >"$OUT/results/$label-terminal.json"
}
# Same input under direct/q7/q1; every call after setup is a true fresh process.
run_world mode1-direct 1 4096
run_world mode1-q7 1 7
run_world mode1-q1 1 1
# Empty and Unicode arrays plus an ordinary guest null-array NPE.
run_world mode0-direct 0 4096
run_world mode2-direct 2 4096
run_world mode3-null 3 4096
python3 "$ROOT/evidence/java-evm/main-entry/preflight/verify.py" "$OUT" >"$OUT/report.json"
cat "$OUT/report.json"
