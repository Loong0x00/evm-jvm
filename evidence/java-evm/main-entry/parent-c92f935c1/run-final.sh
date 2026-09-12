#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?fresh ignored output prefix required}
case "$OUT" in "$ROOT"/build/java-diff-mc-main-entry-*) ;; *) exit 2;; esac
test ! -e "$OUT";mkdir -p "$OUT/tmp"
export TMPDIR="$OUT/tmp"
SRC="$ROOT/evidence/java-evm/main-entry/parent-c92f935c1"
cd "$ROOT"
make java-mc-cb0-check > "$OUT/artifact-check.log" 2>&1
bash "$SRC/reproduce.sh" "$OUT-main" > "$OUT/main.log" 2>&1
bash "$SRC/content/reproduce.sh" "$OUT-content" > "$OUT/content.log" 2>&1
python3 "$SRC/test_parent_verifier.py" "$OUT-main" "$OUT-verifier" > "$OUT/verifier-controls.json"
go test -count=1 -timeout=2m -run '^TestCB0Parent(GeneratedJavaPipeline|ActualNewProcesses|JavaPublicationFailures|ClassBoundaryAndJavaException|QuantumAndConcurrentCAS)$' ./jvmevm/localcontinuation/cb0 > "$OUT/cb0-regression.log" 2>&1
git diff 0fdb9dcf7 -- core params jvmevm Makefile > "$OUT/protected.diff"
test ! -s "$OUT/protected.diff"
echo 'PASS: fresh main-entry+UTF16 contents+strict verifier controls+artifact/regression/protected gates'
