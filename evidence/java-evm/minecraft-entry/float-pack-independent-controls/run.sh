#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/float-pack-controls.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

mkdir -p "$TMP/classes"
javac --release 8 -Xlint:-options -encoding UTF-8 -d "$TMP/classes" "$ROOT/FloatFixtureGenerator.java"
java -cp "$TMP/classes" FloatFixtureGenerator "$TMP/generated-oracle"
python3 "$ROOT/verify.py" \
  --fixtures "$TMP/generated-oracle" \
  --class-file "$TMP/classes/FloatFixtureGenerator.class" \
  --report "$TMP/generated-report.json"

diff -ru "$ROOT/oracle" "$TMP/generated-oracle"
cmp "$ROOT/reference-report.json" "$TMP/generated-report.json"
(
  cd "$ROOT"
  sha256sum -c SHA256SUMS
)
