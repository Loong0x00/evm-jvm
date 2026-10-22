#!/usr/bin/env python3
"""P41 public-driver boundary gate; q4096 only for large checkpoint chains."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
build,fixtures,out=map(lambda x:Path(x).resolve(),sys.argv[1:4])
assert build.parent==fixtures.parent==out.parent==ROOT/'build'
assert build.name.startswith('java-diff-mc-max-arrays-8192-build-') and fixtures.name.startswith('java-diff-mc-max-arrays-8192-fixtures-') and out.name.startswith('java-diff-mc-max-arrays-8192-gate-') and not out.exists()
out.mkdir(); (out/'logs').mkdir(); (out/'tmp').mkdir()
pins=json.loads((build/'pins.json').read_text()); assert pins['maxArrays']==8192 and pins['maxObjects']==4096 and pins['maxHandles']==12545
spec=importlib.util.spec_from_file_location('p41_cpdiag',HERE/'checkpoint_diagnostic.py');diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
env={**os.environ,'TMPDIR':str(out/'tmp'),'GOPROXY':'off','GOSUMDB':'off','GOTOOLCHAIN':'local','MC_ENTRY_BINDINGS':'generated/ArrayCount4096.class'}
driver=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json'
results=[]
def run(label,args):
 t=time.monotonic();log=out/'logs'/(label+'.log')
 with log.open('w') as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'phase':label,'exit':p.returncode,'seconds':round(time.monotonic()-t,3),'command':list(map(str,args))};(out/'logs'/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==0,(label,log);return row
for target in (4096,4097,8192,8193):
 fixture=json.loads((fixtures/f'array-count-{target}.json').read_text()); assert fixture['requestedOrdinaryArrays']==target
 archive=fixtures/f'array-count-{target}.zip'; assert hashlib.sha256(archive.read_bytes()).hexdigest()==fixture['zipSHA256']
 env['MC_ENTRY_BINDINGS']=fixture['entry'];world=out/f'world-{target}-q4096';args=[world,coord,engine,archive,'4096']
 for phase in ('setup-chain','finish','verify'):
  run(f'array-{target}-{phase}',[driver,phase,*args])
 head=json.loads((world/'durable-head.json').read_text()); cp=world/'checkpoints'/(head['checkpointSHA256']+'.bin'); blob=cp.read_bytes(); assert hashlib.sha256(blob).hexdigest()==head['checkpointSHA256']
 decoded=diag.inspect(blob); oom=target==8193; expected=min(target,8192)
 assert head['quantum']==4096 and head['epoch']>0 and head['lifecycle']==head['outcome']==(3 if oom else 2)
 assert head['javaKind']==(7 if oom else 0) and decoded['javaKind']==head['javaKind']
 counts=decoded['heapCounts']; assert counts['ordinaryArrays']==expected,(target,counts)
 assert counts['ordinaryObjects']==(0 if not oom else 0) and counts['arrayElements']==fixture['ordinaryArrayElements']
 arrays=[r for r in decoded['heap'] if int(r['metadata'],16)>>255==0]
 assert len(arrays)==expected and all(r['count']>=0 for r in arrays)
 # All eager records remain explicit and dense; no sparse/lazy checkpoint record accepted.
 assert all(not r['sparse'] and not r['packedFloat'] for r in arrays)
 handles={r['handle'] for r in arrays}
 outer=next(r for r in arrays if r['count']==fixture['innerArrays'])
 aliases=[int(v,16) for v in outer['cells']]
 assert all(v==0 or v in handles for v in aliases)
 assert len([v for v in aliases if v])==fixture['innerArrays'] if not oom else len([v for v in aliases if v])==fixture['innerArrays']-1
 assert len(set(v for v in aliases if v))==len([v for v in aliases if v])
 if oom:
  assert decoded['javaRef']!=0 and counts['exceptionObjects']==1
  exc=next(r for r in decoded['heap'] if r['handle']==decoded['javaRef']); assert int(exc['metadata'],16)>>255==1 and exc['classIndex']==fixture.get('bindingCount',1)+pins['canonicalOOMBootstrapLeafIndex']
 else: assert decoded['javaRef']==0
 results.append({'targetArrays':target,'ordinaryArrays':counts['ordinaryArrays'],'ordinaryObjects':counts['ordinaryObjects'],'arrayElements':counts['arrayElements'],'arrayRecords':len(arrays),'outerArrayReferences':len(aliases),'nonNullArrayAliases':len([v for v in aliases if v]),'exceptionObjects':counts['exceptionObjects'],'lifecycle':head['lifecycle'],'javaKind':head['javaKind'],'quantum':4096,'epochs':head['epoch'],'jvmSteps':head['jvmSteps'],'internalSteps':head['internalSteps'],'machineRoot':head['machineRoot'],'checkpointSHA256':head['checkpointSHA256'],'checkpointBytes':len(blob),'opaquePayloadSHA256':hashlib.sha256(blob[280:]).hexdigest(),'distinctProcessVerify':True,'allArraysDense':True,'fixtureClassSHA256':fixture['classSHA256'],'fixtureZipSHA256':fixture['zipSHA256']})
summary={'schema':1,'profile':'MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192','generatedOnly':True,'ordinaryGasBudget':32000000000,'budgetLabel':'LOCAL32B after preserved measured 1B, 2B, 4B, 8B and 16B failures; generated-test allowance, not EVM rule','watchdogSecondsPerCall':1200,'largeBoundaryQuantum':4096,'maxArrays':8192,'unchangedCaps':{'objects':4096,'arrayElements':262144,'constantPool':4096,'runtimeBytes':1048576,'checkpointBytes':2097152},'results':results,'noOriginalInputs':True}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
