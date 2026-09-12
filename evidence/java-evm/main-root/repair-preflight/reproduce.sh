#!/bin/sh
# Fresh COPY-only MR0 repair reproducer. It refuses any existing caller output.
set -eu
out=${1:?usage: reproduce.sh build/java-diff-mc-main-root-repair-NAME}
case "$out" in build/java-diff-mc-main-root-repair-*) ;; *) echo 'refuse non-MR0 ignored build path' >&2; exit 2;; esac
if [ -e "$out" ]; then echo "refuse existing output: $out" >&2; exit 2; fi
mkdir -p "$out/artifacts" "$out/tmp"
export TMPDIR="$out/tmp"
# The pinned solc dependency must be made explicit by the caller/environment.
: "${NODE_PATH:?set NODE_PATH to a node_modules tree containing solc 0.8.30 and js-sha3}"
start=$(date +%s); deadline=$((start + 1200))
run() { remain=$((deadline - $(date +%s))); [ "$remain" -gt 0 ] || { echo '20-minute watchdog expired' >&2; exit 124; }; timeout "$remain" "$@"; }
cp -a evidence/java-evm/main-root/repair-preflight/engine "$out/artifacts/engine"
cp -a evidence/java-evm/main-root/repair-preflight/coordinator "$out/artifacts/coordinator"
( cd "$out/artifacts/engine" && run node build.js > ../engine-build.json )
( cd "$out/artifacts/coordinator" && run node build.js > ../coordinator-build.json )
cp evidence/java-evm/main-root/repair-preflight/transport/driver.go.txt "$out/main.go"
( cd "$out" && run go build -o mr0-repair . )
run python3 evidence/java-evm/main-root/repair-preflight/transport/fixtures/generate-positive-exception.py "$out/fixtures" > "$out/fixture-build.json"
coord="$out/artifacts/coordinator/MR0MainCoordinator.json"
engine="$out/artifacts/engine/MR0MainInterpreter.json"
for kind in positive rebind rebind-new exception; do
  for q in 1 7; do
    d="$out/$kind-q$q"
    run "$out/mr0-repair" setup-chain "$d" "$coord" "$engine" "$out/fixtures/$kind.zip" "$q"
    run "$out/mr0-repair" finish "$d" "$coord" "$engine" "$out/fixtures/$kind.zip" "$q"
    run "$out/mr0-repair" verify "$d" "$coord" "$engine" "$out/fixtures/$kind.zip" "$q"
  done
done
run python3 evidence/java-evm/main-root/repair-preflight/strict_verify.py "$out" | tee "$out/strict-verify.json"
printf '{"watchdogSeconds":%s,"declaredMaxBytes":4294967296,"status":"completed"}\n' "$(( $(date +%s) - start ))" > "$out/watchdog.json"
