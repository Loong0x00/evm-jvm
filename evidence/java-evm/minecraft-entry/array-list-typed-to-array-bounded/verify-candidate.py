#!/usr/bin/env python3
"""Strict source, DBOOT, artifact, and owned fresh-EVM receipt checks."""
import hashlib, importlib.util, json, pathlib, re, subprocess, os
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/'source-base-p53'
P=json.loads((ROOT/'pins.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text())
# Verify the source-only provenance before verifying candidate artifacts.
manifest=load(BASE/'source-manifest.json')
assert manifest['acceptedGuestCodeCommit']==P['baseGuestCodeCommit'] and len(manifest['files'])==16
assert sha((BASE/'source-manifest.json').read_bytes())==P['sourceBaseManifestSHA256']
for rel,pin in manifest['files'].items():
 raw=(BASE/rel).read_bytes(); assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],rel
# The exact normalized source delta is one ArrayList class image + profile domains.
old_profile='MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1'; profile=P['profile']
base_engine=(BASE/'engine/MCEntryInterpreter.sol').read_text()
engine=(ROOT/'engine/MCEntryInterpreter.sol').read_text()
normalized=engine.replace(profile,old_profile)
def function_text(src,name):
 start=src.index('    function '+name+'('); end=src.find('\n    function ',start+1)
 return src[start:] if end<0 else src[start:end]
old_arraylist=function_text(base_engine,'_bootstrapArrayList')
new_arraylist=function_text(normalized,'_bootstrapArrayList')
normalized=normalized.replace(new_arraylist,old_arraylist)
assert normalized==base_engine, 'engine changed beyond DBOOT domains and ArrayList leaf 98'
base_co=(BASE/'coordinator/MCEntryCoordinator.sol').read_text()
co=(ROOT/'coordinator/MCEntryCoordinator.sol').read_text()
old_engine_hash=re.search(r'ENGINE_CODEHASH = hex"([0-9a-f]+)"',base_co).group(1)
new_engine_hash=re.search(r'ENGINE_CODEHASH = hex"([0-9a-f]+)"',co).group(1)
co_normalized=co.replace(profile,old_profile).replace(new_engine_hash,old_engine_hash)
assert co_normalized==base_co, 'coordinator changed beyond profile domains and engine codehash pin'
# Bootstrap image leaves and authentic root.
spec=importlib.util.spec_from_file_location('array_list_to_array_root_helper',ROOT/'root_helper.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
domain=P['bootstrapDomain']
root=helper.root_record(engine,domain,str(ROOT),{**os.environ,'NODE_PATH':str(ROOT.parents[3]/'jvmevm/runtime/node_modules')})
base_domain=re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\);',base_engine).group(1)
base_root=helper.root_record(base_engine,base_domain,str(ROOT),{**os.environ,'NODE_PATH':str(ROOT.parents[3]/'jvmevm/runtime/node_modules')})
assert root['root']==P['bootstrapRoot'] and root['leaves']==P['orderedBootstrapLeaves']
assert [i for i,(a,b) in enumerate(zip(base_root['leaves'],root['leaves'])) if a!=b]==[98]
assert len(root['leaves'])==P['bootstrapCount']==117
assert re.search(r'new bytes32\[\]\(117\)',engine)
# Java source/image and exact JVM method descriptor.
old_java=(BASE/'bootstrap/java/util/ArrayList.java').read_text()
java=(ROOT/'bootstrap/java/util/ArrayList.java').read_text()
block='''    /** Bounded ordinary typed-target copy; list growth/mutation remains unbound. */
    public Object[] toArray(Object[] target) {
        int count = size;
        int capacity = target.length;
        if (capacity < count) rejectShortTarget();
        for (int i = 0; i < count; i++) target[i] = elementData[i];
        if (capacity > count) target[count] = null;
        return target;
    }

    // Deliberately unbound: an undersized target is outside this measured profile.
    private native void rejectShortTarget();

'''
assert java.count(block)==1 and java.replace(block,'')==old_java
compiled=(ROOT/'build/repro-classes/java/util/ArrayList.class').read_bytes()
assert compiled[:8]==bytes.fromhex('cafebabe00000034')
assert sha(compiled)==P['arrayListImage']['sha256'] and len(compiled)==P['arrayListImage']['bytes']
assert (ROOT/'ArrayList.class.hex').read_text().strip()==compiled.hex()
javap=(ROOT/'build/ArrayList.javap.txt').read_text()
assert re.search(r'public java\.lang\.Object\[\] toArray\(java\.lang\.Object\[\]\);\s+descriptor: \(\[Ljava/lang/Object;\)\[Ljava/lang/Object;\s+Code:',javap)
assert 'private native void rejectShortTarget();' in javap
assert 'getfield      #2                  // Field size:I' in javap
assert 'getfield      #1                  // Field elementData:[Ljava/lang/Object;' in javap
assert 'aastore' in javap and 'arraylength' in javap and 'areturn' in javap
assert re.search(r'public java\.util\.Iterator iterator\(\);',javap)
# Generated test input and pinned engine/coordinator artifacts.
e=load(ROOT/'engine/MCEntryInterpreter.json'); c=load(ROOT/'coordinator/MCEntryCoordinator.json')
assert len(bytes.fromhex(e['deployedBytecode']))==P['engine']['bytes']
assert e['codeHashes']['runtimeSHA256']==P['engine']['runtimeSHA256']
assert e['codeHashes']['runtimeKeccak256']==P['engine']['runtimeKeccak256']
assert e['sourceHashes']['MCEntryInterpreter.sol']==P['engine']['sourceSHA256']
assert len(bytes.fromhex(c['deployedBytecode']))==P['coordinator']['bytes']
assert c['codeHashes']['runtimeSHA256']==P['coordinator']['runtimeSHA256']
assert c['codeHashes']['runtimeKeccak256']==P['coordinator']['runtimeKeccak256']
assert re.search(r'ENGINE_CODEHASH = hex"'+P['engine']['runtimeKeccak256']+r'"',co)
assert P['globalNativeBindings']==22 and P['stringLocalBinding']==12
assert P['rawClassCountLimit']==150 and P['rawByteLimit']==1063930 and P['limitsUnchanged']
# Fresh generated guest lifecycle execution: q1/q7/q128 plus actual reopen process.
runs=ROOT/'runs'; names={'1':'typed-to-array-final-q1','7':'typed-to-array-final-q7-002','128':'typed-to-array-final-q128'}
results={}
for q,name in names.items():
 run=runs/name; head=load(run/'session/durable-head.json'); world=load(run/'reports/session/world-report.json')
 assert head['stage']=='final-reopened' and head['lifecycle']==2 and head['outcome']==2
 assert head['result']==0 and head['javaKind']==0 and head['jvmSteps']>0
 assert world['manifest']['stage']=='final-reopened'
 assert head['quantum']==int(q)
 results[q]={k:head[k] for k in ('epoch','jvmSteps','internalSteps','machineRoot','vfsRoot','checkpointRoot','lifecycle','outcome','result','javaKind')}
 results[q]['counters']=head['counters']
 assert load(run/'reports/session/start.json')['zipSHA256']==sha((ROOT/'test-fixtures/generated/typed-to-array-positive.zip').read_bytes())
assert len({v['machineRoot'] for v in results.values()})==1
assert len({v['vfsRoot'] for v in results.values()})==1
assert len({v['checkpointRoot'] for v in results.values()})==3
# Inherited refusal controls are real EVM resume failures with exact atomicity.
refusals={}
for op in ('noarg','add','get','equals','hash','clone'):
 p=runs/f'refusal-{op}-q1-001/reports/session/resume-refusal.json'
 if op=='clone': p=runs/'refusal-clone-q1-002/reports/session/resume-refusal.json'
 x=load(p);assert x['selector']=='0xd631c3a4' and x['rootUnchanged'] and x['durableHeadUnchanged'],op
 refusals[op]={'selector':x['selector'],'words':x['uint256Words'],'rootUnchanged':x['rootUnchanged'],'durableHeadUnchanged':x['durableHeadUnchanged']}
raw=load(runs/'raw-arraylist-replacement-q1-001/reports/session/start-refusal.json')
assert raw['selector']=='0x6a23ad80' and raw['rootUnchanged'] and raw['durableHeadUnchanged']
report={
 'status':'source/build and historical worker-owned EVM receipts verified; parent acceptance is separate',
 'baseSourceFilesVerified':16,'baseCommit':P['baseGuestCodeCommit'],'oldBootstrapImageCount':117,'changedLeafIndexes':[98],
 'bootstrapRoot':P['bootstrapRoot'],'arrayListImage':P['arrayListImage'],'engine':P['engine'],'coordinator':P['coordinator'],
 'q1q7q128':results,'generatedFixtureSHA256':sha((ROOT/'test-fixtures/generated/typed-to-array-positive.zip').read_bytes()),
 'refusalControls':refusals,'rawArrayListReplacement':{'selector':raw['selector'],'words':raw['uint256Words'],'rootUnchanged':True,'headUnchanged':True},
 'globalNativeBindings':22,'rawClassesInPositiveRun':2,'limitsUnchanged':True,
 'tested':{'sameTargetIdentity':True,'objectIterableMapEntryStringArrays':True,'oversizedFirstNullAndTailPreservation':True,'nullTargetGuestNPE':True,'nullReceiverGuestNPE':True,'privateSizeAgainstMisleadingOverride':True,'iteratorExhaustionAndNSEE':True,'reflectArrayNewInstance':True,'inheritedRawRefusals':True,'bootstrapRawReplacementRefused':True},
 'notTested':{'nonemptyElementCopy':True,'undersizedTargetGuard':True,'HashMapEntrySetFunctionOldTailControlsRerun':True,'rawClass150Frontier':True,'ArrayNewInstanceComponentNoInitializationAndClassNativeControls':True,'heapObjectCountTelemetryNotExposedByThisHead':True},
 'originalMinecraftInputsInspected':False,'MinecraftExecutionClaim':False,'parentReviewPerformed':False
}
(ROOT/'runs/candidate-verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'root':report['bootstrapRoot'],'engineRuntimeBytes':P['engine']['bytes'],'qSteps':{q:v['jvmSteps'] for q,v in results.items()},'refusals':list(refusals)},indent=2))
