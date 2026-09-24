#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVA8_HOME=${JAVA8_HOME:-/usr/lib/jvm/java-8-openjdk}
JAVA="$JAVA8_HOME/bin/java"
JAVAC="$JAVA8_HOME/bin/javac"
OUT="$ROOT/results"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/math-cos-independent.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

if [ ! -x "$JAVA" ] || [ ! -x "$JAVAC" ] || [ ! -f "$JAVA8_HOME/release" ]; then
    echo "Set JAVA8_HOME to an installed JDK 8" >&2
    exit 2
fi
"$JAVA" -version > "$TMP/java-version.txt" 2>&1
"$JAVAC" -version > "$TMP/javac-version.txt" 2>&1
if ! grep -q 'version "1\.8\.' "$TMP/java-version.txt" \
        || ! grep -q '^javac 1\.8\.' "$TMP/javac-version.txt" \
        || ! grep -q '^JAVA_VERSION="1\.8\.' "$JAVA8_HOME/release"; then
    echo "JAVA8_HOME must name an actual JDK 8 installation" >&2
    exit 2
fi
mkdir -p "$OUT" "$TMP/classes"
{
    printf 'java_executable=%s\n' "$JAVA"
    printf 'javac_executable=%s\n' "$JAVAC"
    printf '\n[java -version]\n'
    cat "$TMP/java-version.txt"
    printf '\n[javac -version]\n'
    cat "$TMP/javac-version.txt"
    printf '\n[JDK release]\n'
    cat "$JAVA8_HOME/release"
    printf '\n[compile flags]\nsource=1.8 target=1.8 encoding=US-ASCII\n'
} > "$OUT/jdk8-environment.txt"

"$JAVAC" -encoding US-ASCII -source 1.8 -target 1.8 \
    -d "$TMP/classes" "$ROOT/src/MathCosJava8Oracle.java"
"$JAVA" -Dfile.encoding=US-ASCII -cp "$TMP/classes" MathCosJava8Oracle \
    "$OUT/java8-oracle.tsv" > "$OUT/generator-summary.txt"
python3 "$ROOT/tools/q120_cos.py" \
    "$OUT/java8-oracle.tsv" "$OUT/q120-results.tsv" \
    "$OUT/mismatches.tsv" "$OUT/q120-summary.json" \
    > "$OUT/q120-run-summary.txt"

(
    cd "$ROOT"
    sha256sum README.md run-java8.sh src/MathCosJava8Oracle.java \
        tools/q120_cos.py results/generator-summary.txt \
        results/jdk8-environment.txt results/java8-oracle.tsv \
        results/q120-results.tsv results/mismatches.tsv \
        results/q120-summary.json results/q120-run-summary.txt > SHA256SUMS
)
printf 'evidence=%s\n' "$OUT"
cat "$OUT/q120-run-summary.txt"
