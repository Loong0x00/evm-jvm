#!/usr/bin/env bash
set -euo pipefail

C=$(cd -- "$(dirname -- "$0")" && pwd -P)
ROOT=$(git -C "$C" rev-parse --show-toplevel)
BASE="$ROOT/evidence/java-evm/minecraft-entry/array-list-add-source-base-p59"
JAVAC=/usr/lib/jvm/java-8-openjdk/bin/javac
JAVAP=/usr/lib/jvm/java-8-openjdk/bin/javap
NODE_PATH="$ROOT/jvmevm/runtime/node_modules"
RUN_ID=${1:-"$(date -u +%Y%m%dT%H%M%SZ)-$$"}
[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]
OUT="$C/build/reproduce-$RUN_ID"
RESOLVED=$(realpath -m "$OUT")
[[ "$RESOLVED" == "$C"/* ]]
[[ ! -e "$RESOLVED" ]] || { echo "refusing to overwrite $RESOLVED" >&2; exit 2; }
[[ -x "$JAVAC" && -x "$JAVAP" ]]
mkdir -p "$RESOLVED/old" "$RESOLVED/current" "$RESOLVED/solidity/engine" "$RESOLVED/solidity/coordinator"

context=(
  "$BASE/bootstrap/java/util/ArrayList.java"
  "$BASE/bootstrap/java/util/Iterator.java"
  "$BASE/bootstrap/java/util/AbstractCollection.java"
  "$BASE/bootstrap/java/util/AbstractList.java"
  "$BASE/compiler-support/java/util/Collection.java"
  "$BASE/compiler-support/java/util/List.java"
  "$BASE/compiler-support/java/util/RandomAccess.java"
)
"$JAVAC" -g:none -source 8 -target 8 -d "$RESOLVED/old" "${context[@]}"
oldal="$RESOLVED/old/java/util/ArrayList.class"
olditr="$RESOLVED/old/java/util/ArrayList\$Itr.class"
[[ $(stat -c %s "$oldal") == 1178 ]]
[[ $(sha256sum "$oldal" | cut -d' ' -f1) == 566127a7444cdcc05de5ce43724e412c80108c775f1950b9a559a620e08f9fd2 ]]
[[ $(stat -c %s "$olditr") == 713 ]]
[[ $(sha256sum "$olditr" | cut -d' ' -f1) == 340358b70e03af53ac4f696d19362c8c6615f24cbf6099357864eb983a02c029 ]]

current=(
  "$C/bootstrap/java/util/ArrayList.java"
  "$C/bootstrap/java/util/Iterator.java"
  "$C/bootstrap/java/util/AbstractCollection.java"
  "$C/bootstrap/java/util/AbstractList.java"
  "$C/compiler-support/java/util/Collection.java"
  "$C/compiler-support/java/util/List.java"
  "$C/compiler-support/java/util/RandomAccess.java"
)
"$JAVAC" -g:none -source 8 -target 8 -d "$RESOLVED/current" "${current[@]}"
for name in ArrayList 'ArrayList$Itr'; do
  "$JAVAP" -p -c -classpath "$RESOLVED/current" "java.util.$name" > "$RESOLVED/$name.javap.txt"
done

# Build artifact copies from immutable candidate sources; never overwrite the pinned files.
for component in engine coordinator; do
  mkdir -p "$RESOLVED/solidity/$component"
  cp "$C/$component/"*.sol "$C/$component/build.js" "$RESOLVED/solidity/$component/"
  (cd "$ROOT" && NODE_PATH="$NODE_PATH" node "$RESOLVED/solidity/$component/build.js" > "$RESOLVED/$component-build.json")
done

NODE_PATH="$NODE_PATH" python3 - "$C" "$BASE" "$RESOLVED" <<'PY'
import importlib.util,json,pathlib,sys,os,hashlib
c,base,out=map(pathlib.Path,sys.argv[1:4])
spec=importlib.util.spec_from_file_location('root_helper',c/'root_helper.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
s=(c/'engine/MCEntryInterpreter.sol').read_text()
r=h.root_record(s,'JVMEVM:MC-ARRAY-LIST-ADD-BOUNDED-1:BOOTSTRAP:1',str(c.resolve()),os.environ.copy())
old=json.loads((base/'engine/MCEntryInterpreter.json').read_text())
new=json.loads((out/'solidity/engine/MCEntryInterpreter.json').read_text())
oldc=json.loads((base/'coordinator/MCEntryCoordinator.json').read_text())
newc=json.loads((out/'solidity/coordinator/MCEntryCoordinator.json').read_text())
assert old['abi']==new['abi'] and old['storageLayout']==new['storageLayout']
assert oldc['abi']==newc['abi'] and oldc['storageLayout']==newc['storageLayout']
pins=json.loads((c/'pins.json').read_text())
assert r['root']==pins['bootstrapRoot']
for rel,name in [('java/util/ArrayList.class','ArrayList'),('java/util/ArrayList$Itr.class','ArrayList$Itr')]:
    raw=(out/'current'/rel).read_bytes()
    row=next(x for x in pins['changedImages'] if x['name']==('java/util/ArrayList' if name=='ArrayList' else 'java/util/ArrayList$Itr'))
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
assert new['codeHashes']['runtimeSHA256']==pins['engine']['runtimeSHA256']
assert newc['codeHashes']['runtimeSHA256']==pins['coordinator']['runtimeSHA256']
print(json.dumps({'engineRuntimeBytes':len(bytes.fromhex(new['deployedBytecode'])),'engineRuntimeSHA256':new['codeHashes']['runtimeSHA256'],'coordinatorRuntimeBytes':len(bytes.fromhex(newc['deployedBytecode'])),'coordinatorRuntimeSHA256':newc['codeHashes']['runtimeSHA256'],'bootstrapRoot':r['root']},indent=2))
PY
printf 'reproduction outputs: %s\n' "$RESOLVED"
