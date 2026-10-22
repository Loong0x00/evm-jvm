#!/usr/bin/env python3
"""Small q1/q7/q4096 execution schedule-equivalence smoke on generated eager arrays."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
build,fixtures,out=map(lambda x:Path(x).resolve(),sys.argv[1:4]); assert build.parent==fixtures.parent==out.parent==ROOT/'build'
assert build.name.startswith('java-diff-mc-max-arrays-8192-build-') and fixtures.name.startswith('java-diff-mc-max-arrays-8192-fixtures-') and out.name.startswith('java-diff-mc-max-arrays-8192-schedule-') and not out.exists()
out.mkdir();(out/'logs').mkdir();(out/'tmp').mkdir();spec=importlib.util.spec_from_file_location('p41smalldiag',HERE/'checkpoint_diagnostic.py');diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
env={**os.environ,'TMPDIR':str(out/'tmp'),'GOPROXY':'off','GOSUMDB':'off','GOTOOLCHAIN':'local','MC_ENTRY_BINDINGS':'generated/ArrayCount8.class'}
driver=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json';fixture=json.loads((fixtures/'array-count-8.json').read_text());zipfile=fixtures/'array-count-8.zip'
def run(label,args):
 t=time.monotonic();log=out/'logs'/(label+'.log')
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 (out/'logs'/(label+'.json')).write_text(json.dumps({'phase':label,'exit':r.returncode,'seconds':round(time.monotonic()-t,3),'command':list(map(str,args))},indent=2)+'\n');assert r.returncode==0,(label,log)
rows=[]
for q in (1,7,4096):
 world=out/f'world-q{q}';args=[world,coord,engine,zipfile,str(q)];env['MC_ENTRY_BINDINGS']=fixture['entry']
 for phase in ('setup-chain','finish','verify'):run(f'q{q}-{phase}',[driver,phase,*args])
 h=json.loads((world/'durable-head.json').read_text());blob=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();d=diag.inspect(blob)
 assert h['lifecycle']==h['outcome']==2 and h['javaKind']==0 and d['heapCounts']['ordinaryArrays']==8 and d['heapCounts']['arrayElements']==6
 arrays=[x for x in d['heap'] if int(x['metadata'],16)>>255==0];assert len(arrays)==8 and all(not x['sparse'] and not x['packedFloat'] for x in arrays)
 rows.append({'quantum':q,'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'vfsRoot':h['vfsRoot'],'heapCounts':d['heapCounts'],'arrays':[{'rank':x['rank'],'count':x['count'],'cells':x['cells']} for x in arrays],'checkpointSHA256':h['checkpointSHA256'],'checkpointBytes':len(blob),'distinctProcessVerify':True})
assert all((r['machineRoot'],r['vfsRoot'],r['heapCounts'],r['arrays'])==(rows[0]['machineRoot'],rows[0]['vfsRoot'],rows[0]['heapCounts'],rows[0]['arrays']) for r in rows)
summary={'schema':1,'generatedOnly':True,'profile':'P41-ARRAY-8192','targetOrdinaryArrays':8,'schedules':rows,'machineVFSAndEagerHeapEquivalentAcrossSchedules':True,'checkpointBytesMayDifferBySchedule':True,'noOriginalInputs':True}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
