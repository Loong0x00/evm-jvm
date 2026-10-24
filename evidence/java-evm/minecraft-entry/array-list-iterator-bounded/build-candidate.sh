#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$ROOT/../../../.." && pwd)
"$ROOT/build-bootstrap.sh"
NODE_PATH=/home/user/evm-jvm/array-list-iterator/jvmevm/runtime/node_modules node "$ROOT/engine/build.js"
python3 - "$ROOT" <<'PY'
import json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]);e=json.loads((r/'engine/MCEntryInterpreter.json').read_text());p=r/'coordinator/MCEntryCoordinator.sol';s=p.read_text();s,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]+";',f'bytes32 private constant ENGINE_CODEHASH = hex"{e["codeHashes"]["runtimeKeccak256"]}";',s,count=1);assert n==1;p.write_text(s)
PY
NODE_PATH=/home/user/evm-jvm/array-list-iterator/jvmevm/runtime/node_modules node "$ROOT/coordinator/build.js"
"$ROOT/build-fixtures.sh"
(cd "$REPO" && GOPROXY=off GOSUMDB=off go build -o "$ROOT/build/array-list-iterator-driver" "$ROOT/canonical-driver.go")
SH
chmod +x evidence/java-evm/minecraft-entry/array-list-iterator-bounded/build-candidate.sh
