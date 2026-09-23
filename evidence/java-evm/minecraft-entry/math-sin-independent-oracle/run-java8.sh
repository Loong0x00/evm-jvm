#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVA8_HOME=${JAVA8_HOME:-/usr/lib/jvm/java-8-openjdk}
JAVA="$JAVA8_HOME/bin/java"
JAVAC="$JAVA8_HOME/bin/javac"
OUT="$ROOT/results"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/math-sin-oracle.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

if [ ! -x "$JAVA" ] || [ ! -x "$JAVAC" ]; then
    echo "Set JAVA8_HOME to an installed JDK 8" >&2
    exit 2
fi
mkdir -p "$OUT" "$TMP/classes"
"$JAVA" -version > "$TMP/java-version.txt" 2>&1
"$JAVAC" -version > "$TMP/javac-version.txt" 2>&1
if ! grep -q 'version "1\.8\.' "$TMP/java-version.txt" \
        || ! grep -q '^javac 1\.8\.' "$TMP/javac-version.txt" \
        || ! grep -q '^JAVA_VERSION="1\.8\.' "$JAVA8_HOME/release"; then
    echo "JAVA8_HOME must name an actual JDK 8 installation" >&2
    exit 2
fi
{
    printf 'java_executable=%s\n' "$JAVA"
    printf 'javac_executable=%s\n' "$JAVAC"
    printf '\n[java -version]\n'
    cat "$TMP/java-version.txt"
    printf '\n[javac -version]\n'
    cat "$TMP/javac-version.txt"
    printf '\n[JDK release]\n'
    cat "$JAVA8_HOME/release"
} > "$OUT/jdk8-environment.txt"

"$JAVAC" -encoding US-ASCII -source 1.8 -target 1.8 \
    -d "$TMP/classes" "$ROOT/src/MathSinOracle.java" 2> "$TMP/javac-stderr.txt"
"$JAVA" -Dfile.encoding=US-ASCII -cp "$TMP/classes" MathSinOracle \
    "$OUT/samples.tsv" > "$OUT/generator-summary.txt"
python3 "$ROOT/tools/explore_q120.py" "$OUT/samples.tsv" > "$OUT/q120-summary.json"

cd "$ROOT"
sha256sum \
    README.md run-java8.sh src/MathSinOracle.java tools/explore_q120.py \
    results/generator-summary.txt results/jdk8-environment.txt \
    results/q120-summary.json results/samples.tsv > SHA256SUMS
printf 'wrote %s\n' "$OUT/samples.tsv"
