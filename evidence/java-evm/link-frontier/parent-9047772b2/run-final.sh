#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?fresh ignored output required}
case "$OUT" in "$ROOT"/build/java-diff-mc-link-frontier-*) ;; *) exit 2;; esac
test ! -e "$OUT";mkdir -p "$OUT/tmp"
export TMPDIR="$OUT/tmp"
cd "$ROOT"
make java-mc-cb0-check > "$OUT/artifact-check.log" 2>&1
bash evidence/java-evm/link-frontier/parent-9047772b2/reproduce.sh "$OUT-replay" > "$OUT/replay.log" 2>&1
go test -count=1 -timeout=2m -run '^TestCB0Parent(GeneratedJavaPipeline|ActualNewProcesses|JavaPublicationFailures|ClassBoundaryAndJavaException|QuantumAndConcurrentCAS)$' ./jvmevm/localcontinuation/cb0 > "$OUT/regression.log" 2>&1
git diff 0fdb9dcf7 -- core params jvmevm Makefile > "$OUT/protected.diff"
test ! -s "$OUT/protected.diff"
echo 'PASS: fresh link/cast/eager controls; exact public refusal/checkpoint/root checks; unchanged production'
