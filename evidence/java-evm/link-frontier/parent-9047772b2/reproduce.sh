#!/bin/sh
# Fresh-output-only replay. Execution consumes only opaque ZIP bytes via public CB0 APIs.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
OUT=${1:?usage: reproduce.sh NEW-ignored-build/java-diff-mc-link-frontier-*}
case "$OUT" in "$ROOT"/build/java-diff-mc-link-frontier-*) ;; *) echo 'OUT must be fresh ignored build/java-diff-mc-link-frontier-*' >&2; exit 2;; esac
[ ! -e "$OUT" ] || { echo "refusing existing output: $OUT" >&2; exit 2; }
mkdir -p "$OUT/tmp" "$OUT/results"; export TMPDIR="$OUT/tmp"
python3 "$ROOT/evidence/java-evm/link-frontier/parent-9047772b2/generate_fixture.py" "$OUT/fixture" >"$OUT/generate.log" 2>&1
python3 "$ROOT/evidence/java-evm/link-frontier/parent-9047772b2/repair_driver.py" "$OUT/main.go"
gofmt -w "$OUT/main.go"
(cd "$ROOT" && go build -o "$OUT/driver" "$OUT/main.go")
ZIP="$OUT/fixture/link-frontier-generated.zip"; LENGTH=$(wc -c <"$ZIP"|tr -d ' ')
setup() { "$OUT/driver" -dir "$OUT/world-$1" -zip "$ZIP" -names "$2" -command setup >"$OUT/results/$1-setup.json"; }
slice() { "$OUT/driver" -dir "$OUT/world-$1" -length "$LENGTH" -command slice -mode "$2" -quantum "$3" ${4:-} >"$OUT/results/$5"; }
# Closed four-image public-main chain; direct and q1 differ only grouping.
setup closed-direct0 LinkLauncher,LinkMain,LinkBase,LinkMarker
slice closed-direct0 0 4096 '' closed-direct0.json
setup closed-direct7 LinkLauncher,LinkMain,LinkBase,LinkMarker
slice closed-direct7 7 4096 '' closed-direct7.json
setup closed-q1 LinkLauncher,LinkMain,LinkBase,LinkMarker
n=0; while :; do n=$((n+1)); [ "$n" -le 256 ] || exit 1; slice closed-q1 7 1 '' closed-q1-$n.json; life=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lifecycle"])' "$OUT/results/closed-q1-$n.json"); [ "$life" = 1 ] || break; done
# One supplied DemandEntry succeeds without resolving the CP MissingTarget; paths bind on use.
setup demand-0 DemandEntry; slice demand-0 0 4096 '' demand-0.json
for m in 1 2 3; do setup demand-$m DemandEntry; slice demand-$m $m 4096 -allow-failure demand-$m-refusal.json; done
# Prior EVM-issued q1 checkpoints survive the later resume refusal exactly.
setup demand-q1 DemandEntry
n=0; while :; do n=$((n+1)); [ "$n" -le 256 ] || exit 1; slice demand-q1 1 1 -allow-failure demand-q1-$n.json; cmd=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["command"])' "$OUT/results/demand-q1-$n.json"); [ "$cmd" = refusal ] && break; done
"$OUT/driver" -dir "$OUT/world-demand-q1" -length "$LENGTH" -command terminal >"$OUT/results/demand-q1-after.json"
for k in super interface; do if [ "$k" = super ]; then names=SuperEntry; else names=InterfaceEntry; fi; setup "$k" "$names"; slice "$k" 9 4096 -allow-failure "$k-refusal.json"; done
# The fifth generated image is attempted, but public CB0 rejects its decoder before EVM call.
"$OUT/driver" -dir "$OUT/world-fifth" -zip "$ZIP" -names LinkLauncher,LinkMain,LinkBase,LinkMarker,DemandEntry -command setup >"$OUT/results/fifth-capacity.json"
# Actual preloading controls: the SAME original demand modes, with dependencies selected.
for m in 1 2 3;do setup eager-$m DemandEntry,MissingTarget;slice eager-$m $m 4096 '' eager-$m.json;done
setup eager-super SuperEntry,MissingSuper;slice eager-super 9 4096 '' eager-super.json
setup eager-interface InterfaceEntry,MissingInterface;slice eager-interface 9 4096 '' eager-interface.json
# Cast itself, without a trailing invokevirtual; null versus non-null, target missing/present.
setup cast-null CastEntry;slice cast-null 0 4096 '' cast-null.json
setup cast-missing CastEntry;slice cast-missing 1 4096 -allow-failure cast-missing.json
setup cast-present CastEntry,MissingTarget;slice cast-present 1 4096 '' cast-present.json
# Independent terminal reopens, not merely in-process reads.
for w in closed-direct0 closed-direct7 closed-q1 demand-0 eager-1 eager-2 eager-3 eager-super eager-interface cast-null cast-present;do
 "$OUT/driver" -dir "$OUT/world-$w" -length "$LENGTH" -command terminal >"$OUT/results/$w-terminal.json"
done
python3 "$ROOT/evidence/java-evm/link-frontier/preflight/verify.py" "$OUT" >"$OUT/report.json"
python3 "$ROOT/evidence/java-evm/link-frontier/parent-9047772b2/verify_parent.py" "$OUT" > "$OUT/parent-report.json"
(cd "$ROOT" && go vet "$OUT/main.go")
cat "$OUT/parent-report.json"
