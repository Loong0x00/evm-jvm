#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?fresh ignored build/java-diff-mc-capacity-* prefix required}
case "$OUT" in "$ROOT"/build/java-diff-mc-capacity-*) ;; *) exit 2;; esac
test ! -e "$OUT";mkdir -p "$OUT/tmp"
export TMPDIR="$OUT/tmp" NODE_PATH="$ROOT/jvmevm/runtime/node_modules"
SRC="$ROOT/evidence/java-evm/capacity-baseline/parent-97a926123"
cd "$ROOT"
python3 "$SRC/reconstruct.py" "$OUT-proto" > "$OUT/reconstruction.log" 2>&1
python3 "$SRC/probe_warm.py" "$OUT-warm-original" "$OUT-proto" > "$OUT/warm-original.log" 2>&1
python3 "$SRC/repair_copy.py" "$OUT-proto" > "$OUT/repair.json"
gofmt -w "$OUT-proto/capacitycb0"/*.go
node "$OUT-proto/capacitycb0/runtime/build.js" > "$OUT/coordinator-exact-bound.log" 2>&1
python3 "$SRC/build_drivers.py" "$OUT-proto" > "$OUT/driver-build.log" 2>&1
python3 evidence/java-evm/capacity-baseline/fixture-completion/generate.py "$OUT-fixtures" > "$OUT/fixtures.log" 2>&1
python3 evidence/java-evm/capacity-baseline/fixture-completion/generate.py --verify "$OUT-fixtures" >> "$OUT/fixtures.log" 2>&1
python3 "$SRC/replay.py" "$OUT-proto" "$OUT-fixtures" "$OUT-matrix" > "$OUT/replay.log" 2>&1
python3 "$SRC/verify.py" "$OUT-fixtures" "$OUT-matrix" > "$OUT/report.json"
python3 "$SRC/density_probe.py" "$OUT-proto" "$OUT-density" > "$OUT/density.log" 2>&1
python3 "$SRC/verify_density.py" "$OUT-density" > "$OUT/density-report.json"
go test -count=1 -timeout=18m ./jvmevm/localcontinuation/cb0/... > "$OUT/accepted-cb0.log" 2>&1
git diff 7b46769c5 -- core params jvmevm Makefile > "$OUT/protected.diff"
test ! -s "$OUT/protected.diff"
echo 'PASS: fresh bounded COPY-only reconstruction, warm failure/repair,24 worlds/read tracing/boundaries, density ordinary failures/explicit1B, accepted CB0 regression'
