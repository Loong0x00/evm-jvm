#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVA8_HOME=${JAVA8_HOME:-/usr/lib/jvm/java-8-openjdk}
OUT="$ROOT/results"
mkdir -p "$OUT"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/asin-coverage.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

if [ ! -x "$JAVA8_HOME/bin/java" ] || [ ! -x "$JAVA8_HOME/bin/javac" ]; then
    echo "JAVA8_HOME must name an installed JDK 8: $JAVA8_HOME" >&2
    exit 2
fi

{
    "$JAVA8_HOME/bin/java" -version 2>&1
    "$JAVA8_HOME/bin/javac" -version 2>&1
    printf 'JAVA8_HOME=%s\n' "$JAVA8_HOME"
    printf 'compile_flags=-source 8 -target 8 -encoding UTF-8\n'
} > "$OUT/jdk8-environment.txt"
grep -Eq '(java|openjdk) version "1\.8\.' "$OUT/jdk8-environment.txt" || {
    echo "JAVA8_HOME does not run Java 8" >&2
    exit 2
}

"$JAVA8_HOME/bin/javac" -source 8 -target 8 -encoding UTF-8 -d "$TMP" \
    "$ROOT/src/AsinCoverageJava8Oracle.java" \
    "$ROOT/src/Q120AsinCoverageProbe.java"
"$JAVA8_HOME/bin/java" -cp "$TMP" AsinCoverageJava8Oracle "$OUT/samples.tsv"
"$JAVA8_HOME/bin/java" -cp "$TMP" Q120AsinCoverageProbe \
    "$OUT/samples.tsv" "$OUT/mismatches.tsv" "$OUT/q120-summary.json" "$OUT/run-summary.txt" \
    | tee "$OUT/run-console.txt"

(
    cd "$ROOT"
    sha256sum README.md run-java8.sh src/AsinCoverageJava8Oracle.java \
        src/Q120AsinCoverageProbe.java results/jdk8-environment.txt \
        results/samples.tsv results/oracle-summary.txt results/mismatches.tsv \
        results/q120-summary.json results/run-summary.txt results/run-console.txt \
        > results/SHA256SUMS
)
printf 'evidence=%s\n' "$OUT"
cat "$OUT/oracle-summary.txt"
cat "$OUT/run-summary.txt"
