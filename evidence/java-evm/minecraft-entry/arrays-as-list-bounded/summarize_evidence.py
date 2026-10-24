#!/usr/bin/env python3
"""Validate and summarize preserved local EVM attempts without rewriting receipts."""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parent
BUILD=ROOT/'build'
REPORTS=BUILD/'reports'
def final(world):
    p=BUILD/world/'durable-head.json'; m=json.loads(p.read_text())
    assert m['lifecycle']==2 and m['outcome']==2 and m['javaRef']==0 and m['javaKind']==0, (world,m['lifecycle'],m['outcome'])
    slices=[]
    for f in sorted((REPORTS/world).glob('slice-*.json')):
        x=json.loads(f.read_text());s=x['slice']
        slices.append({'epoch':s['epoch'],'lifecycle':s['lifecycle'],'jvmTotal':s['totalJvmSteps'],
                       'internalTotal':s['totalInternalSteps'],'gas':x['gasUsed'],'elapsedMS':x['elapsedMS']})
    assert slices and slices[-1]['lifecycle']==2 and slices[-1]['jvmTotal']==m['jvmSteps']
    processes=[]
    for f in sorted((REPORTS/world).glob('process-*.json')):
        x=json.loads(f.read_text());processes.append({'pid':x['pid'],'initialRoot':x['initialRoot'],'finalRoot':x['finalRoot']})
    assert len(set(x['pid'] for x in processes))>=2, 'fresh OS process reopen not demonstrated'
    checkpoint=(BUILD/world/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest()==m['checkpointSHA256']
    return {'world':world,'quantum':m['quantum'],'rawBindingCount':len(m['rawNames']),
            'rawNamesSHA256':hashlib.sha256(json.dumps(m['rawNames'],separators=(',',':')).encode()).hexdigest(),
            'epoch':m['epoch'],'lifecycle':m['lifecycle'],'jvmSteps':m['jvmSteps'],
            'internalSteps':m['internalSteps'],'checkpointBytes':len(checkpoint),
            'checkpointRoot':m['checkpointRoot'],'machineRoot':m['machineRoot'],'vfsRoot':m['vfsRoot'],
            'processes':processes,'sliceCount':len(slices),'lastSlice':slices[-1],
            'resourceReadCount':m['counters']['readFragmentCount'],'evmCalls':m['counters']['evmCalls'],
            'checkpointPublishes':m['counters']['checkpointFileSyncs']}

# Successful execution is the unchanged guest classfile's positive assertion suite.
worlds=[final('world-q1-raw150-controls-v5'),final('world-q7-controls-v5'),final('world-q65536-controls-v5')]
assert [x['quantum'] for x in worlds]==[1,7,65536]
assert worlds[0]['rawBindingCount']==150 and worlds[1]['rawBindingCount']==1 and worlds[2]['rawBindingCount']==1
zip_path=BUILD/'arrays-as-list-fixture-v3.zip'
with zipfile.ZipFile(zip_path) as z: assert len(z.namelist())==150
refusals=[]
for name in ('ArraysAsListGetRefusal','ArraysAsListSetRefusal','ArraysAsListAddRefusal',
             'ArraysAsListToArrayRefusal','ArraysAsListIteratorRemoveRefusal','ArraysCopyOfRefusal','ArraysSortRefusal'):
    x=json.loads((REPORTS/('world-refusal-'+name+'-v5')/'resume-refusal.json').read_text())
    assert x['selector']=='0xd631c3a4' and x['rootUnchanged'] is True, name
    refusals.append({'fixture':name,'error':'CallError','code':x['uint256Words'][0],
                     'pc':x['uint256Words'][1],'gas':x['gas'],'rootUnchanged':x['rootUnchanged']})
# Preserve the two real preparation failures and one exploratory API-scope refusal.
attempts=[]
for label,path in (
 ('initial resource names omitted required .class suffix','logs/q1-raw150-setup.log'),
 ('coordinator still pinned P55 engine codehash before isolated coordinator rebuild','logs/q1-raw150-setup-v2.log'),
 ('driver initially carried the previous candidate coordinator codehash','logs/q1-raw150-controls-v4-setup.log'),
 ('driver then carried the wrong engine keccak while updating coordinator pin','logs/q1-raw150-controls-v4b-setup.log'),
 ('earlier probe attempted ArrayList.add outside this bounded API surface','reports/world-q1-raw150-controls-v2/resume-refusal.json')):
    p=BUILD/path
    attempts.append({'label':label,'path':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report={
 'profile':'MC-ARRAYS-AS-LIST-BOUNDED-1','status':'worker candidate; parent independent review/build/gates pending',
 'sourceBaseVerification':'build/pins/source-base-verification.json',
 'bootstrapRoot':'build/pins/bootstrap-root.json','pins':'pins.json',
 'executionInput':'generated Java 8 test classfiles only; no original Minecraft archive/classes/resources/worlds',
 'assertionCoverage':['empty and nonempty Object[]','String[] and Serializable[]','null elements and singleton null varargs',
  'factory returns a new list each time while sharing the supplied array','independent cursors','live caller writes after factory and iterator creation',
  'identity-preserving ordered next','hasNext and genuine NoSuchElementException on empty/nonempty exhaustion',
  'null array use raises genuine NullPointerException','RandomAccess and Serializable markers','fixed-size mutation/get/set/toArray/iterator-remove refusal',
  'unsupported Arrays.copyOf and Arrays.sort refusal',
  'retained ArrayList(int)/typed toArray/iterator, Function, NavigableSet type-link, HashMap.entrySet, and singletonList controls'],
 'classBoundary':{'rawClasses':150,'bootstrapImages':123,'assembledProgramClasses':273,
                  'lastRawIndex':149,'ArraysArrayIteratorBootstrapIndex':122,
                  'lastActualArraysArrayIteratorProgramIndex':272,
                  'executionEvidence':'q1 raw150 fixture successfully called asList, constructed/consumed actual iterator, and completed all assertions'},
 'successfulEVMWorlds':worlds,'unsupportedSurfaceRefusals':refusals,
 'preservedFailedAttempts':attempts,
 'limitsUnchanged':{'rawClasses':150,'rawBytes':1063930,'arrays':8192,'arrayElements':262144,
 'arrayLength':65536,'objects':4096,'handles':12545,'runtimeBytes':1048576,'frames':128,
 'quantum':65536,'internalPerSlice':4096,'reserveGas':25000000},
 'localCallBudgets':{'ordinaryGas':1000000000,'perCallWatchdogSeconds':30,'outerWatchdogSeconds':1200},
 'nonGoals':['no get/set/mutation/toArray or other Arrays APIs implemented','no Minecraft original execution','no profile acceptance or production merge claim']}
(BUILD/'results').mkdir(exist_ok=True)
(BUILD/'results/arrays-as-list-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'worlds':[{k:x[k] for k in ('world','quantum','rawBindingCount','epoch','lifecycle','jvmSteps','internalSteps','sliceCount')} for x in worlds],
                  'refusals':refusals,'summary':'build/results/arrays-as-list-summary.json'},indent=2))
