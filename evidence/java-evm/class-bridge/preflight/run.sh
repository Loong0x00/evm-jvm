#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "usage: $0 NEW_BUILD_DIR" >&2; exit 2; fi
ROOT=$(git rev-parse --show-toplevel)
SRC="$ROOT/evidence/java-evm/class-bridge/preflight"
OUT=$1
if [[ -e "$OUT" ]]; then echo "refusing existing output: $OUT" >&2; exit 2; fi
mkdir -p "$OUT/npm" "$OUT/classes" "$OUT/zips"
OUT=$(cd "$OUT" && pwd)
cp "$SRC/package.json" "$SRC/package-lock.json" "$OUT/npm/"
npm ci --prefix "$OUT/npm" --ignore-scripts --no-audit --no-fund >"$OUT/npm.log"
CLASS_BRIDGE_NODE_MODULES="$OUT/npm/node_modules" node "$SRC/compile.js" "$OUT/ClassBridge.json" >"$OUT/compile.log"
/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none -d "$OUT/classes" \
  "$SRC/BridgeAlpha.java" "$SRC/BridgeBeta.java" "$SRC/Oracle.java"
(
 cd "$OUT/classes"
 /usr/lib/jvm/java-8-openjdk/bin/java Oracle BridgeAlpha 7
 /usr/lib/jvm/java-8-openjdk/bin/java Oracle BridgeBeta 8
) >"$OUT/java8-oracle.log"
/usr/lib/jvm/java-8-openjdk/bin/javap -classpath "$OUT/classes" -c -p BridgeAlpha BridgeBeta >"$OUT/java8-bytecode.log"
grep -q 'invokestatic' "$OUT/java8-bytecode.log"
python3 "$SRC/make_fixtures.py" "$OUT/classes" "$OUT/zips"
(
 cd "$ROOT"
 go run "$SRC/replay.go" "$OUT" "$OUT/ClassBridge.json" "$OUT/report.json"
) >"$OUT/replay.log"
python3 "$SRC/verify_report.py" "$OUT/report.json" >"$OUT/verify.log"
sha256sum "$SRC"/BridgeAlpha.java "$SRC"/BridgeBeta.java "$SRC"/Oracle.java \
 "$SRC"/ClassBridge.sol "$SRC"/compile.js "$SRC"/make_fixtures.py "$SRC"/replay.go \
 "$SRC"/run.sh "$SRC"/verify_report.py "$SRC"/package.json "$SRC"/package-lock.json \
 "$OUT"/classes/*.class "$OUT"/zips/*.zip "$OUT/ClassBridge.json" "$OUT/report.json" \
 "$OUT/java8-bytecode.log" >"$OUT/SHA256SUMS"
cat "$OUT/compile.log" "$OUT/java8-oracle.log" "$OUT/replay.log" "$OUT/verify.log"
