#!/bin/bash
# Fresh generated-input replay. No official JAR/classes or production edits.
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
p="$repo/evidence/java-evm/class-bridge/parent-e3f45ec22"
s="$repo/evidence/java-evm/class-bridge/preflight"
[[ $# == 1 ]] || { echo 'usage: reproduce.sh NEW_BUILD_DIR' >&2; exit 2; }
w=$1
[[ $w == /* ]] || w="$repo/$w"
[[ ! -e $w ]] || { echo 'refusing existing workspace' >&2; exit 2; }
bash "$s/run.sh" "$w" > "$w-baseline.log"
python3 "$p/padded_fixtures.py" "$w/classes" "$w/padded"
for n in 4096 4097 8193 65536 65537; do
 /usr/lib/jvm/java-8-openjdk/bin/java -cp "$w/padded/$n:$w/classes" Oracle BridgeAlpha 7
done > "$w/padded-java8.log"
CLASS_BRIDGE_NODE_MODULES="$w/npm/node_modules" node "$p/compile.js" "$w/PagedBridge.json" > "$w/paged-compile.json"
cp "$p/traced-base.go.txt" "$w/traced-base.go"
cp "$p/traced-sizes.go.txt" "$w/traced-sizes.go"
go build -trimpath -o "$w/sizes" "$w/traced-base.go" "$w/traced-sizes.go"
set +e
"$w/sizes" "$w/padded" "$w/ClassBridge.json" > "$w/original-size-failure.json"
rc=$?
set -e
[[ $rc == 1 ]] || { echo 'original valid-size failure not reproduced' >&2; exit 1; }
"$w/sizes" "$w/padded" "$w/PagedBridge.json" > "$w/paged-sizes.json"
go run "$s/replay.go" "$w" "$w/PagedBridge.json" "$w/paged-original.json"
python3 "$s/verify_report.py" "$w/paged-original.json"
python3 - "$w" <<'PY'
from pathlib import Path
import sys,json,hashlib
w=Path(sys.argv[1]);rows=json.loads((w/'paged-sizes.json').read_text())
assert [x['Size'] for x in rows]==[4096,4097,8193,65536,65537]
for x in rows[:-1]:
 assert x['Result']==76 and x['JVM']==181 and not x['Error']
 assert sum(x['ReadSizes'])==x['Size'] and max(x['ReadSizes'])<=4096
assert rows[-2]['Slices']==26 and rows[-1]['Error'].startswith('BridgeError(8)')
assert (w/'padded-java8.log').read_text().splitlines()==['BridgeAlpha(7)=76']*5
print('STRICT PASS: fresh baseline; original valid4097+ size failure; paged boundaries and 64KiB q7 equality; original positives/refusals retained')
print('paged artifact SHA256',hashlib.sha256((w/'PagedBridge.json').read_bytes()).hexdigest())
PY
