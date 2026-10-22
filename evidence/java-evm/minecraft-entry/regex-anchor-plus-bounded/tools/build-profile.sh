#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)
D="$ROOT/evidence/java-evm/minecraft-entry/regex-anchor-plus-bounded"
BASE="$ROOT/evidence/java-evm/minecraft-entry/regex-anchor-plus-source-base-p41"
JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-8-openjdk}
export NODE_PATH="$ROOT/jvmevm/runtime/node_modules"
export GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local
# Never overwrite historical compiled classes, artifacts, reports, or worlds.
# Each invocation leaves a fresh, uniquely named reproducible build directory.
WORK=$(mktemp -d "${TMPDIR:-/tmp}/regex-anchor-plus-build.XXXXXX")
mkdir -p "$WORK/profile" "$WORK/compiled"
P="$WORK/profile"
for path in bootstrap engine coordinator tools reference; do mkdir -p "$P/$path"; done
cp -R "$D/bootstrap/java" "$P/bootstrap/"
cp -R "$D/engine/." "$P/engine/"
cp -R "$D/coordinator/." "$P/coordinator/"
cp -R "$D/tools/." "$P/tools/"
cp -R "$D/reference/." "$P/reference/"
cp "$D/pins.json" "$P/pins.json"
"$JAVA_HOME/bin/javac" -source 8 -target 8 -g:none -d "$WORK/compiled" \
  "$D/bootstrap/java/util/regex/Pattern.java" \
  "$D/bootstrap/java/util/regex/Matcher.java" \
  "$D/bootstrap/java/util/regex/PatternSyntaxException.java" \
  "$D/bootstrap/java/lang/String.java"
python3 "$P/tools/materialize.py" --class-dir "$WORK/compiled" --engine "$P/engine/MCEntryInterpreter.sol" --base "$BASE/engine/MCEntryInterpreter.sol" --repo-root "$ROOT"
node "$P/engine/build.js"
node "$P/coordinator/build.js"
python3 "$P/tools/pin-artifacts.py" --profile "$P" --repo-root "$ROOT"
python3 "$P/tools/verify-fresh-build.py" --profile "$P" --repo-root "$ROOT"
printf 'FRESH_BUILD_DIR=%s\n' "$WORK"
