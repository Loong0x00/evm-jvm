#!/usr/bin/env python3
"""Generated-only Enum82 q1/q7/direct/reopen, type and active-init gate."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
here=Path(__file__).resolve().parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and out.name.startswith('java-diff-mc-enum-bootstrap-') and not out.exists()
out.mkdir(); (out/'logs').mkdir(); (out/'tmp').mkdir(); start=time.monotonic(); commands=[]; rows={}
spec=importlib.util.spec_from_file_location('enum_checkpoint_diagnostic',here/'checkpoint_diagnostic.py'); diagnostic=importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver=build/'driver'; coord=build/'coordinator/MCEntryCoordinator.json'; engine=build/'engine/MCEntryInterpreter.json'
def names(label): return ','.join(json.loads((fixtures/(label+'.json')).read_text())['entries'])
def report(w): return w.parent/'reports'/w.name
def run(label,args,binding,expect=0):
 env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',MC_ENTRY_BINDINGS=names(binding)); log=out/'logs'/(label+'.log'); then=time.monotonic()
 with log.open('w') as f: p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'label':label,'command':list(map(str,args)),'exit':p.returncode,'seconds':time.monotonic()-then}; commands.append(row); (out/'logs'/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n'); assert p.returncode==expect,(label,p.returncode,log)
def terminal(w):
 h=json.loads((w/'durable-head.json').read_text()); assert h['lifecycle']==h['outcome']==2 and h['result']==0 and h['javaKind']==0 and len(h['decoders'])==2 and h['totalClassBytes']<=262144
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256']; d=diagnostic.inspect(cp)
 # Raw classes come first, then all 82 append-only bootstraps. Enum is tail index 83.
 active={x['classIndex'] for x in d['initialization'] if x['state']==2}; assert {0,1,83}.issubset(active),(active,d['initialization'])
 return {'machineRoot':h['machineRoot'],'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'checkpointSHA256':h['checkpointSHA256'],'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'classCount':d['classCount'],'activeInitialization':sorted(active)}
baseline=None
for tag,q in (('q1',1),('q7',7),('direct',4096)):
 w=out/('enum-'+tag); run('enum-'+tag+'-start',[driver,'setup-chain',w,coord,engine,fixtures/'enum-bootstrap.zip',str(q)],'enum-bootstrap'); run('enum-'+tag+'-finish',[driver,'finish',w,coord,engine,fixtures/'enum-bootstrap.zip',str(q)],'enum-bootstrap'); run('enum-'+tag+'-reopen',[driver,'verify',w,coord,engine,fixtures/'enum-bootstrap.zip',str(q)],'enum-bootstrap')
 x=terminal(w); rows['enum/'+tag]=x
 if baseline is None: baseline=x
 else:
  for key in ('machineRoot','opaquePayloadSHA256'): assert x[key]==baseline[key],(tag,key,x,baseline)
# Raw Enum is profile-owned and must fail atomically at raw binding index 1.
w=out/'raw-enum'; run('raw-enum-refusal',[driver,'setup-chain',w,coord,engine,fixtures/'raw-enum-replacement.zip','4096'],'raw-enum-replacement')
r=json.loads((report(w)/'start-refusal.json').read_text()); assert r['selector']=='0x6a23ad80' and list(map(str,r['uint256Words']))==['1','1'] and r['rootUnchanged']; rows['raw/enum-replacement']=r
node_env=dict(os.environ,NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
subprocess.run(['node',here/'verify_receipts.js',build,out,'1','enum-q1','enum-q7','enum-direct'],cwd=root,env=node_env,check=True)
summary={'profile':'MC-ENUM-BOOTSTRAP-PREFLIGHT1','generatedOnly':True,'hostOracle':json.loads((fixtures/'summary.json').read_text())['enum-bootstrap'],'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start,'scope':'Java8 enum constructor fields/name/ordinal/direct toString, Comparable bridge/cast/null guest exceptions, Serializable assignability, active superclass initialization, reserved raw replacement, and canonical q1/q7/direct/reopen only.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
