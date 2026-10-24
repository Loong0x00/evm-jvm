#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=/home/user/evm-jvm/array-list-to-array
PROFILE=MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1
"$ROOT/build-bootstrap.sh"
python3 - "$ROOT" "$PROFILE" <<'PY'
from pathlib import Path
import re,sys
r=Path(sys.argv[1]); profile=sys.argv[2]
engine=r/'engine/MCEntryInterpreter.sol'; s=engine.read_text()
raw=(r/'ArrayList.class.hex').read_text().strip()
s,n=re.subn(r'    function _bootstrapArrayList\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}', '    function _bootstrapArrayList() private pure returns (bytes memory) { return hex"'+raw+'"; }', s, count=1)
assert n==1
s=s.replace('MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1',profile)
engine.write_text(s)
co=r/'coordinator/MCEntryCoordinator.sol'; c=co.read_text().replace('MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1',profile); co.write_text(c)
PY
NODE_PATH="$REPO/jvmevm/runtime/node_modules" node "$ROOT/engine/build.js"
python3 - "$ROOT" <<'PY'
import json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]);e=json.loads((r/'engine/MCEntryInterpreter.json').read_text());p=r/'coordinator/MCEntryCoordinator.sol';s=p.read_text();s,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]+";',f'bytes32 private constant ENGINE_CODEHASH = hex"{e["codeHashes"]["runtimeKeccak256"]}";',s,count=1);assert n==1;p.write_text(s)
PY
NODE_PATH="$REPO/jvmevm/runtime/node_modules" node "$ROOT/coordinator/build.js"
"$ROOT/build-fixtures.sh"
sed 's/MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1/MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1/g' "$ROOT/canonical-driver.go.txt" > "$ROOT/canonical-driver.go"
python3 - "$ROOT" <<'PY'
import json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]); e=json.loads((r/'engine/MCEntryInterpreter.json').read_text()); c=json.loads((r/'coordinator/MCEntryCoordinator.json').read_text()); p=r/'canonical-driver.go'; s=p.read_text()
s,n=re.subn(r'const immutableEngineSHA256 = "[0-9a-f]+"',f'const immutableEngineSHA256 = "{e["codeHashes"]["runtimeSHA256"]}"',s,count=1); assert n==1
s,n=re.subn(r'const immutableEngineKeccak = "0x[0-9a-f]+"',f'const immutableEngineKeccak = "0x{e["codeHashes"]["runtimeKeccak256"]}"',s,count=1); assert n==1
s,n=re.subn(r'const immutableCoordinatorKeccak = "0x[0-9a-f]+"',f'const immutableCoordinatorKeccak = "0x{c["codeHashes"]["runtimeKeccak256"]}"',s,count=1); assert n==1
s,n=re.subn(r'435002',str(len(bytes.fromhex(e['deployedBytecode']))),s); assert n==2
p.write_text(s)
PY
(cd "$REPO" && GOPROXY=off GOSUMDB=off go build -o "$ROOT/build/array-list-typed-to-array-driver" "$ROOT/canonical-driver.go")
chmod 0644 "$ROOT/canonical-driver.go"
chmod 0644 "$ROOT/canonical-driver.go"
