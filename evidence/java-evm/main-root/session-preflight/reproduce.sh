#!/bin/sh
# COPY-only MR0 Session reproducer. It refuses existing output and never touches
# accepted sources or prior evidence. The oversized engine is installed only at
# the documented LOCAL initial-state address; all other controllers use CREATE.
set -eu
out=${1:?usage: reproduce.sh build/java-diff-mc-main-root-session-NAME}
case "$out" in build/java-diff-mc-main-root-session-*) ;; *) echo 'refuse non-session ignored build path' >&2; exit 2;; esac
if [ -e "$out" ]; then echo 'refuse existing output' >&2; exit 2; fi
: "${NODE_PATH:?set NODE_PATH to pinned solc 0.8.30/js-sha3 dependencies}"
out=$(cd "$(dirname "$out")" && pwd)/$(basename "$out")
mkdir -p "$out/artifacts" "$out/tmp"
export TMPDIR="$out/tmp"
start=$(date +%s); deadline=$((start + 1200))
run() { remain=$((deadline - $(date +%s))); [ "$remain" -gt 0 ] || { echo '20-minute watchdog expired' >&2; exit 124; }; timeout "$remain" "$@"; }
cp -a evidence/java-evm/main-root/session-preflight/artifacts/engine "$out/artifacts/engine"
cp -a evidence/java-evm/main-root/session-preflight/artifacts/coordinator "$out/artifacts/coordinator"
( cd "$out/artifacts/engine" && run node build.js > ../engine-build.json )
( cd "$out/artifacts/coordinator" && run node build.js > ../coordinator-build.json )
cp evidence/java-evm/main-root/session-preflight/transport/session.go.txt "$out/main.go"
( cd "$out" && run go build -o mr0-session . )
run python3 evidence/java-evm/main-root/session-preflight/fixtures/generate-positive-exception.py "$out/fixtures" > "$out/fixture-build.json"
coord="$out/artifacts/coordinator/MR0MainCoordinator.json"
engine="$out/artifacts/engine/MR0MainInterpreter.json"
for kind in positive rebind rebind-new exception; do
  for quantum in 1 7 4096; do
    world="$out/$kind-q$quantum"
    run "$out/mr0-session" setup-chain "$world" "$coord" "$engine" "$out/fixtures/$kind.zip" "$quantum"
    # A direct terminal exception may legitimately open/close without adding a
    # published manifest PID; external process receipts still record this call.
    run "$out/mr0-session" finish "$world" "$coord" "$engine" "$out/fixtures/$kind.zip" "$quantum"
    run "$out/mr0-session" verify "$world" "$coord" "$engine" "$out/fixtures/$kind.zip" "$quantum"
  done
done
run python3 evidence/java-evm/main-root/session-preflight/strict_verify.py "$out" > "$out/strict-verify.json"
cat "$out/strict-verify.json"
printf '{"status":"completed","elapsedSeconds":%s,"declaredWallSeconds":1200,"declaredPeakGroupRSSBytes":4294967296,"tmpdir":"%s"}\n' "$(( $(date +%s) - start ))" "$TMPDIR" > "$out/reproducer.json"
