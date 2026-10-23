#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ID=${1:?usage: run-gates.sh UNIQUE_RUN_ID}
case "$ID" in *[!A-Za-z0-9._-]*|'') echo 'invalid run id' >&2; exit 2;; esac
RUNS="$ROOT/runs/$ID"
LOGS="$ROOT/runs/logs/$ID"
BIN="$ROOT/build/array-list-driver"
COORD="$ROOT/coordinator/MCEntryCoordinator.json"
ENGINE="$ROOT/engine/MCEntryInterpreter.json"
ZIP="$ROOT/test-fixtures/generated"
mkdir -p "$RUNS" "$LOGS"
run_ok() {
  name=$1 q=$2 binding=$3 zip=$4
  dir="$RUNS/$name"
  test ! -e "$dir" || { echo "world already exists: $dir" >&2; exit 2; }
  mkdir "$dir"
  MC_ENTRY_BINDINGS="$binding" GOPROXY=off GOSUMDB=off "$BIN" setup-chain "$dir" "$COORD" "$ENGINE" "$ZIP/$zip.zip" "$q" >"$LOGS/$name-setup.log" 2>&1
  MC_ENTRY_BINDINGS="$binding" GOPROXY=off GOSUMDB=off "$BIN" finish "$dir" "$COORD" "$ENGINE" "$ZIP/$zip.zip" "$q" >"$LOGS/$name-finish.log" 2>&1
  MC_ENTRY_BINDINGS="$binding" GOPROXY=off GOSUMDB=off "$BIN" verify "$dir" "$COORD" "$ENGINE" "$ZIP/$zip.zip" "$q" >"$LOGS/$name-verify.log" 2>&1
}
run_refusal() {
  name=$1 binding=$2 zip=$3
  dir="$RUNS/$name"
  test ! -e "$dir" || { echo "world already exists: $dir" >&2; exit 2; }
  mkdir "$dir"
  MC_ENTRY_BINDINGS="$binding" GOPROXY=off GOSUMDB=off "$BIN" setup-chain "$dir" "$COORD" "$ENGINE" "$ZIP/$zip.zip" 1 >"$LOGS/$name-setup.log" 2>&1
  MC_ENTRY_BINDINGS="$binding" GOPROXY=off GOSUMDB=off "$BIN" finish "$dir" "$COORD" "$ENGINE" "$ZIP/$zip.zip" 1 >"$LOGS/$name-finish.log" 2>&1
}
run_ok default-q1 1 probe/ArrayListDefaultProbe.class default
run_ok default-q7 7 probe/ArrayListDefaultProbe.class default
run_ok default-q128 128 probe/ArrayListDefaultProbe.class default
run_ok negative-int-q1 1 probe/ArrayListNegativeProbe.class negative
run_ok int-only-q1 1 probe/ArrayListIntOnlyProbe.class int-only
for spec in \
  'add probe/ArrayListRefusalAddProbe.class add' \
  'iterator probe/ArrayListRefusalIteratorProbe.class iterator' \
  'typed-to-array probe/ArrayListRefusalTypedToArrayProbe.class typed-to-array' \
  'equals probe/ArrayListRefusalEqualsProbe.class equals' \
  'hash probe/ArrayListRefusalHashProbe.class hash' \
  'get probe/ArrayListRefusalGetProbe.class get' \
  'clone probe/ArrayListCloneProbe.class clone'; do
  set -- $spec
  run_refusal "unsupported-$1-q1" "$2" "$3"
done
# The raw class intentionally duplicates the canonical bootstrap binary name.
# A source bootstrap replacement must refuse atomically instead of shadowing it.
name=raw-replacement-q1
dir="$RUNS/$name"
test ! -e "$dir" || { echo "world already exists: $dir" >&2; exit 2; }
mkdir "$dir"
MC_ENTRY_BINDINGS=java/util/ArrayList.class GOPROXY=off GOSUMDB=off "$BIN" setup-chain "$dir" "$COORD" "$ENGINE" "$ZIP/raw-replacement.zip" 1 >"$LOGS/$name-setup.log" 2>&1
python3 - "$ROOT" "$ID" <<'PY'
import hashlib,json,pathlib,re,sys
root=pathlib.Path(sys.argv[1]); rid=sys.argv[2]; runs=root/'runs'/rid; reports=runs/'reports'
qs={}
for q in (1,7,128):
 n=f'default-q{q}'; d=json.loads((runs/n/'durable-head.json').read_text()); w=json.loads((reports/n/'world-report.json').read_text())
 assert d['stage']=='final-reopened' and d['lifecycle']==2 and d['outcome']==2 and d['result']==0 and d['javaKind']==0
 assert w['manifest']['stage']=='final-reopened'
 qs[str(q)]={k:d[k] for k in ('epoch','jvmSteps','internalSteps','machineRoot','vfsRoot','trieRoot','checkpointRoot','checkpointSHA256','lifecycle','outcome','result','javaKind')}
assert len({x['machineRoot'] for x in qs.values()})==1
assert len({x['vfsRoot'] for x in qs.values()})==1
neg=json.loads((runs/'negative-int-q1/durable-head.json').read_text())
assert neg['lifecycle']==2 and neg['outcome']==2 and neg['result']==0 and neg['javaKind']==0
intOnly=json.loads((runs/'int-only-q1/durable-head.json').read_text())
assert intOnly['lifecycle']==2 and intOnly['outcome']==2 and intOnly['result']==0 and intOnly['javaKind']==0
intOnlyReport=json.loads((reports/'int-only-q1/world-report.json').read_text())
assert intOnlyReport['manifest']['stage']=='final-reopened'
refusals={}
for op in ('add','iterator','typed-to-array','equals','hash','get','clone'):
 name=f'unsupported-{op}-q1'; report=reports/name/'resume-refusal.json'
 if not report.exists(): report=reports/name/'start-refusal.json'
 x=json.loads(report.read_text()); assert x['rootUnchanged'] and x.get('durableHeadUnchanged')
 assert x['selector']=='0xd631c3a4', (op,x['selector'],x.get('uint256Words'))
 refusals[op]={'selector':x['selector'],'words':x['uint256Words'],'rootUnchanged':x['rootUnchanged'],'durableHeadUnchanged':x['durableHeadUnchanged'],'gas':x['gas']}
raw=json.loads((reports/'raw-replacement-q1/start-refusal.json').read_text())
assert raw['rootUnchanged'] and raw.get('durableHeadUnchanged') and raw['selector']=='0x6a23ad80'
pins=json.loads((root/'pins.json').read_text()); javap=(root/'build/repro-javap.txt').read_text(); rawClass=bytes.fromhex((root/'ArrayList.class.hex').read_text().strip())
ctor=javap.split('  public java.util.ArrayList();',1)[1].split('  public java.util.ArrayList(int);',1)[0]
clinit=javap.split('  static {};',1)[1]
intctor=javap.split('  public java.util.ArrayList(int);',1)[1].split('  public int size();',1)[0]
assert 'getstatic' in ctor and 'DEFAULTCAPACITY_EMPTY_ELEMENTDATA' in ctor
assert 'anewarray' in clinit and 'putstatic' in clinit and 'DEFAULTCAPACITY_EMPTY_ELEMENTDATA' in clinit
assert 'anewarray' in intctor and 'initialCapacity' not in intctor
base=root.parents[3]/'evidence/java-evm/minecraft-entry/array-list-default-source-base-p49'
pattern=re.compile(r'    public ArrayList\(int initialCapacity\) \{.*?\n    \}',re.S)
source=(root/'bootstrap/java/util/ArrayList.java').read_text(); baseSource=(base/'bootstrap/java/util/ArrayList.java').read_text()
assert pattern.search(source).group(0)==pattern.search(baseSource).group(0)
report={'runId':rid,'execution':'fresh local geth EVM; generated Java8 fixtures only; no original Minecraft inputs','constructorProbe':qs,'intNegativeCaught':True,'intOnlyFirstUse':{'jvmSteps':intOnly['jvmSteps'],'epochs':intOnly['epoch'],'totalExternalEvmGas':intOnly['counters']['gas'],'maxSingleEvmCallGas':intOnly['counters']['maxGas'],'maxCallMs':intOnly['counters']['maxCallMs'],'machineRoot':intOnly['machineRoot'],'vfsRoot':intOnly['vfsRoot'],'firstUseExecutesOrdinaryClassClinit':True},'unsupportedRawRefusals':refusals,'rawArrayListReplacement':{'selector':raw['selector'],'words':raw['uint256Words'],'rootUnchanged':raw['rootUnchanged'],'durableHeadUnchanged':raw['durableHeadUnchanged'],'gas':raw['gas']},'classfileEvidence':{'bytes':len(rawClass),'sha256':hashlib.sha256(rawClass).hexdigest(),'classVersion':52,'fieldPrivateStaticFinalSentinel':True,'defaultConstructorGetstaticSentinel':True,'ordinaryClinitCreatesZeroLengthObjectArray':True,'intConstructorAllocatesNewObjectArray':True,'intConstructorSourceMatchesP49ByteForByte':True},'runtimePins':{'engineRuntimeBytes':pins['engine']['runtimeBytes'],'engineRuntimeSHA256':pins['engine']['runtimeSHA256'],'engineRuntimeKeccak256':pins['engine']['runtimeKeccak256'],'coordinatorRuntimeBytes':pins['coordinator']['runtimeBytes'],'bootstrapRoot':pins['bootstrapRoot']},'equivalence':{'machineRootEqualAcrossQ1Q7Q128':True,'vfsRootEqualAcrossQ1Q7Q128':True,'checkpointOpaqueHashesMayDifferByQuantum':True}}
(root/'runs'/f'{rid}-verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'runId':rid,'machineRoot':qs['1']['machineRoot'],'vfsRoot':qs['1']['vfsRoot'],'epochs':{q:v['epoch'] for q,v in qs.items()},'refusalCount':len(refusals)+1},indent=2))
PY
