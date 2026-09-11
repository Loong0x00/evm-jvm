#!/usr/bin/env bash
# Rebuild final runtime drivers in a new ignored workspace and replay generated fixtures.
# No official server artifact is read, inflated, uploaded, or executed.
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "usage: $0 NEW_BUILD_DIRECTORY" >&2; exit 2; fi
repo=$(git rev-parse --show-toplevel)
out=$1
if [[ $out != /* ]]; then out="$repo/$out"; fi
if [[ -e $out ]]; then echo "refusing existing output: $out" >&2; exit 2; fi
mkdir -p "$out"
cp "$repo/jvmevm/artifactstore/di0/runtime/DI0Resource.sol" "$out/DI0Inflate.sol"
cp "$repo/evidence/java-evm/di0/parent-e738ad221/yield/replay.go.txt" "$out/replay.go"
cp "$repo/evidence/java-evm/di0/budget-preflight/persistence.go.txt" "$out/persistence.go"
cp "$repo/evidence/java-evm/di0/budget-preflight/trees.go.txt" "$out/trees.go"
cp "$repo/evidence/java-evm/di0/parent-e738ad221/headers64/source.go.txt" "$out/headers64.go"
cp "$repo/evidence/java-evm/di0/parent-e738ad221/yield/long-trees.go.txt" "$out/long-trees.go"
cp "$repo/evidence/java-evm/di0/parent-e738ad221/yield/long-performance.go.txt" "$out/long-performance.go"
python3 - "$repo" "$out" <<'PY'
import json,sys
from pathlib import Path
repo,out=map(Path,sys.argv[1:])
x=json.loads((repo/'jvmevm/artifactstore/di0/runtime/combinedartifacts/DI0Resource.json').read_text())
(out/'DI0Resource.driver.json').write_text(json.dumps({'abi':x['abi'],'bytecode':x['bytecode'],'runtime':x['deployedBytecode']},separators=(',',':')))
replacements={
'MC-DI0/binding/preflight/v1':'MC-DI0/binding/v1',
'MC-DI0/output/preflight/v1':'MC-DI0/output/v1',
'MC-DI0/byte/preflight/v1':'MC-DI0/byte/v1',
'MC-DI0/publication/preflight/v2':'MC-DI0/publication/v1',
'MC-DI0/page/preflight/v2':'MC-DI0/page/v1',
'MC-DI0/published/preflight/v2':'MC-DI0/published/v1',
'MC-DI0/final/preflight/v2':'MC-DI0/final/v1',
}
for name in ('replay.go','persistence.go','trees.go','headers64.go','long-trees.go','long-performance.go'):
 p=out/name;s=p.read_text()
 for old,new in replacements.items():s=s.replace(old,new)
 p.write_text(s)
# Production dependency checks move the changed-SSTORE proof later than the archived
# 70k preflight point. The first final-artifact trial is retained; 90k proves a changed
# write before real OOG and rollback, then retries normally. Add final-only constructor
# length/precedence probes without changing any positive fixture expectation.
p=out/'replay.go';s=p.read_text().replace('70_000','90_000').replace('70000','90000')
needle='''\tcontrols := map[string]interface{}{}\n\tother := common.HexToAddress("0xd100000000000000000000000000000000000099")'''
insert='''\tcontrols := map[string]interface{}{}\n\tnameOut, _, _, nameErr := cenv.create(append(init, pack(ca, "", ci, croot, []byte{})...))\n\trefuse("constructorEmptyName", nameOut, nameErr, 4, controls)\n\tnameOut, _, _, nameErr = cenv.create(append(init, pack(ca, "", ci, croot, bytes.Repeat([]byte{'n'}, 257))...))\n\trefuse("constructorLongName", nameOut, nameErr, 4, controls)\n\tnameOut, _, _, nameErr = cenv.create(append(init, pack(ca, "", ci, common.Hash{}, []byte{})...))\n\trefuse("constructorRootBeforeName", nameOut, nameErr, 3, controls)\n\tother := common.HexToAddress("0xd100000000000000000000000000000000000099")'''
if needle not in s:raise SystemExit('constructor probe insertion point not found')
s=s.replace(needle,insert)
p.write_text(s)
(out/'tree-base.go').write_text(s.replace('func main() {','func originalMain() {',1))
PY
(
 cd "$out"
 go build -trimpath -o replay replay.go persistence.go
 go build -trimpath -o trees tree-base.go persistence.go trees.go
 go build -trimpath -o headers64 tree-base.go persistence.go headers64.go
 go build -trimpath -o long-performance tree-base.go persistence.go long-trees.go long-performance.go
 mkdir java8
 /usr/lib/jvm/java-8-openjdk/bin/javac -d java8 "$repo/evidence/java-evm/di0/budget-preflight/InflateOracle.java"
 sha256sum DI0Resource.driver.json replay trees headers64 long-performance > binaries.sha256
 timeout 1200 ./replay DI0Resource.driver.json > execution-report.json 2> replay.stderr
 mkdir trees-out headers64-out
 timeout 1200 env DI0_ARTIFACT="$out/DI0Resource.driver.json" DI0_TREE_OUT="$out/trees-out" ./trees > trees-evm.json
 /usr/lib/jvm/java-8-openjdk/bin/java -Xms16m -Xmx256m -XX:MaxMetaspaceSize=128m -Xss1m -cp java8 InflateOracle "$out/trees-out/generated" > trees-java8.json
 timeout 1200 env DI0_ARTIFACT="$out/DI0Resource.driver.json" DI0_TREE_OUT="$out/headers64-out" ./headers64 > headers64-evm.json
 /usr/lib/jvm/java-8-openjdk/bin/java -Xms16m -Xmx256m -XX:MaxMetaspaceSize=128m -Xss1m -cp java8 InflateOracle "$out/headers64-out/generated" > headers64-java8.json
 timeout 1200 ./long-performance DI0Resource.driver.json > long-performance-report.json
 python3 - <<'PY'
import json
ok={'verified-EVM-output','expected-EVM-rejection','expected-constructor-rejection'}
r=json.load(open('execution-report.json'))
assert len(r['Results'])==37 and all(x['Outcome'] in ok for x in r['Results'])
assert r['Controls']['allExactSelectors'] and r['QEquality']['equal']
assert r['OOG']['postWriteProof'] and r['OOG']['publishRolledBack'] and r['OOG']['publishRetrySameChild']
p=r['Persistence'];assert p['successfulDurablePublications']==60 and p['distinctChildPIDs']
d=p['dynamicCacheFreshProcesses'];assert d['distinctChildPIDs'] and all(x['verified'] for x in d['freshProcessStages'])
for name,n in [('trees',29),('headers64',4)]:
 rows=json.load(open(name+'-evm.json'));j=json.load(open(name+'-java8.json'));js={x['name']:x for x in j['fixtures']}
 assert len(rows)==n and len(js)==n and j['javaVersion']=='1.8.0_504'
 for row in rows:
  e=row['EVM'];a=js[row['Name']];assert e['Outcome'] in ok and e['Gas']['StepMax']<100_000_000
  if e['Outcome']=='verified-EVM-output':
   assert not a['inflaterError'] and a['finished'] and a['remaining']==0
   assert not a['zipFileError'] and not a['zipInputStreamError']
   assert a['plainBytes']==e['Plain']==a['zipFileBytes']==a['zipInputStreamBytes']
  else:assert e['Error'] and a['inflaterError'] and a['zipFileError'] and a['zipInputStreamError']
  if name=='headers64':assert e['Outcome']=='verified-EVM-output' and e['Work']==128
r=json.load(open('long-performance-report.json'))
assert r['allEqual'] and r['allCallsBelow100M'] and len(r['pairs'])==6 and len(r['sweeps'])==5
assert all(x['equal'] for x in r['pairs'])
assert all(x['allEqual'] and x['quantums']==128 and x['maxStepGas']<100_000_000 for x in r['sweeps'])
print('FRESH FINAL-ARTIFACT PASS: 37/29/4 cases, Java8 generated oracle, 6 pairs, 5 q1..128 sweeps, 60-publication/process persistence, changed-write and CREATE rollback')
PY
 sha256sum execution-report.json trees-evm.json trees-java8.json headers64-evm.json headers64-java8.json long-performance-report.json > reports.sha256
)
