#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVA8_HOME=${JAVA8_HOME:-/usr/lib/jvm/java-8-openjdk}
JAVA="$JAVA8_HOME/bin/java"
JAVAC="$JAVA8_HOME/bin/javac"
FIXTURE="$ROOT/../math-sin-independent-oracle/results/samples.tsv"
RESULTS="$ROOT/results"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/math-sin-numerics.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

if [ ! -x "$JAVA" ] || [ ! -x "$JAVAC" ]; then
    echo "Set JAVA8_HOME to an installed JDK 8" >&2
    exit 2
fi
mkdir -p "$RESULTS" "$TMP/classes"
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
} > "$RESULTS/jdk8-environment.txt"

"$JAVAC" -encoding US-ASCII -source 1.8 -target 1.8 \
    -d "$TMP/classes" "$ROOT/src/MathSinNumericsOracle.java" \
    2> "$TMP/javac-stderr.txt"
python3 "$ROOT/tools/numerics_control.py" prepare \
    --out "$RESULTS/generated-inputs.tsv" \
    > "$RESULTS/generated-input-summary.json"
python3 "$ROOT/tools/numerics_control.py" grid \
    --fixture "$FIXTURE" --out-dir "$RESULTS/grid" > /dev/null
"$JAVA" -Dfile.encoding=US-ASCII -cp "$TMP/classes" MathSinNumericsOracle \
    "$RESULTS/generated-inputs.tsv" "$RESULTS/jdk8-oracle.tsv" \
    > "$RESULTS/jdk8-oracle-summary.txt"
python3 "$ROOT/tools/numerics_control.py" compare \
    --inputs "$RESULTS/generated-inputs.tsv" \
    --oracle "$RESULTS/jdk8-oracle.tsv" \
    --out-dir "$RESULTS/generated" > /dev/null
python3 "$ROOT/tools/numerics_control.py" overflow \
    --grid "$RESULTS/grid/grid-summary.json" \
    --samples "$RESULTS/generated/sample-summary.json" \
    --out "$RESULTS/overflow-analysis.json" > /dev/null

cd "$ROOT"
sha256sum \
    README.md run-controls.sh src/MathSinNumericsOracle.java \
    tools/numerics_control.py \
    results/generated-input-summary.json results/generated-inputs.tsv \
    results/generated/sample-comparison.tsv results/generated/sample-summary.json \
    results/grid/grid-mismatches.tsv results/grid/grid-summary.json \
    results/jdk8-environment.txt results/jdk8-oracle-summary.txt \
    results/jdk8-oracle.tsv results/overflow-analysis.json > results/SHA256SUMS
printf 'numerical controls passed; results: %s\n' "$RESULTS"
