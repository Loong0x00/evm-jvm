#!/bin/sh
set -eu

runtime_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Callers choose a disposable workspace and archive stdout/report under the
# repository's evidence/java-evm/ tree. Never put the sole evidence in /tmp.
work=${1:?usage: replay.sh EXPLICIT_WORKSPACE (archive results under evidence/java-evm/)}
mkdir -p "$work"
cp "$runtime_dir/ZI0ZipIndex.sol" "$work/ZI0Persistent.sol"
cp "$runtime_dir/testdata/final_replay.go.txt" "$work/main.go"
python3 - "$runtime_dir/combinedartifacts/ZI0ZipIndex.json" "$work/prototype.json" <<'PY'
import json
import sys
source, target = sys.argv[1:]
artifact = json.load(open(source, encoding="utf-8"))
with open(target, "w", encoding="utf-8") as output:
    json.dump({
        "abi": artifact["abi"],
        "bytecode": "0x" + artifact["bytecode"],
        "runtime": "0x" + artifact["deployedBytecode"],
    }, output)
PY
ZI0_REPLAY_WORK="$work" go run "$work/main.go"
printf 'ZI0 final replay retained at %s\n' "$work" >&2
