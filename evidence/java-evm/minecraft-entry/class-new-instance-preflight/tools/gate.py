#!/usr/bin/env python3
"""Generated-only q1/q7/direct/reopen preflight for bounded Class.newInstance."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
here=Path(__file__).resolve().parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and not out.exists()
out.mkdir(); logs=out/'logs'; logs.mkdir(); start=time.monotonic(); rows={}; commands=[]
spec=importlib.util.spec_from_file_location('diagnostic',here/'checkpoint_diagnostic.py'); d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
def names(case): return ','.join(json.loads((fixtures/'summary.json').read_text())[case]['entries'])
def run(label,args,case):
 env=dict(os.environ,MC_ENTRY_BINDINGS=names(case),TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1'); (out/'tmp').mkdir(exist_ok=True)
 log=logs/(label+'.log'); t=time.monotonic()
 with log.open('w') as f: p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'label':label,'command':list(map(str,args)),'exit':p.returncode,'seconds':time.monotonic()-t}; commands.append(row); assert p.returncode==0,row
def final(world, expectedClasses):
 h=json.loads((world/'durable-head.json').read_text()); assert h['lifecycle']==h['outcome']==2 and h['result']==0
 cp=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); x=d.inspect(cp); assert x['classCount']>=expectedClasses and x['javaKind']==0
 return {'machineRoot':h['machineRoot'],'checkpointSHA256':hashlib.sha256(cp).hexdigest(),'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'initialization':x['initialization']}
driver=build/'driver'; coord=build/'coordinator/MCEntryCoordinator.json'; engine=build/'engine/MCEntryInterpreter.json'
# success verifies target <clinit>, constructor field accesses, exactly-once init and two distinct construction results in genuine Java Code.
for case,expect in (('success',2),('null',1)):
 baseline=None
 for q in (1,7,4096):
  w=out/(case+'-q'+str(q)); z=fixtures/(case+'.zip')
  run(case+'-q'+str(q)+'-start',[driver,'setup-chain',w,coord,engine,z,str(q)],case)
  run(case+'-q'+str(q)+'-finish',[driver,'finish',w,coord,engine,z,str(q)],case)
  run(case+'-q'+str(q)+'-reopen',[driver,'verify',w,coord,engine,z,str(q)],case)
  got=final(w,expect); rows[case+'/q'+str(q)]=got
  if baseline is None: baseline=got
  else:
   for k in ('machineRoot','opaquePayloadSHA256'): assert got[k]==baseline[k],(case,q,k)
# Profile refusals are start-call reverts before a checkpoint/head mutation. They are deliberately not Java checked exceptions.
for case in ('bootstrap-refusal','abstract-refusal','constructor-refusal'):
 w=out/case; z=fixtures/(case+'.zip'); run(case+'-start',[driver,'setup-chain',w,coord,engine,z,'4096'],case)
 r=json.loads((out/'reports'/w.name/'start-refusal.json').read_text()); assert r['rootUnchanged'] and r['error']=='execution reverted' and len(r['uint256Words'])==2
 rows[case]=r
summary={'profile':'MC-CLASS-NEW-INSTANCE-PREFLIGHT1','generatedOnly':True,'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
