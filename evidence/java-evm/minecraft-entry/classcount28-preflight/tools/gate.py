#!/usr/bin/env python3
"""Generated-only class-count28 EVM gate; no original JAR/class/world input."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
here=Path(__file__).resolve().parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and out.name.startswith('java-diff-mc-classcount28-') and not out.exists()
out.mkdir(); logs=out/'logs';logs.mkdir();start=time.monotonic();commands=[]
def names(label):return ','.join(json.loads((fixtures/(label+'.json')).read_text())['entries'])
def run(label,args,bindings=None,expect=0):
 env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1');out.joinpath('tmp').mkdir(exist_ok=True)
 if bindings:env['MC_ENTRY_BINDINGS']=names(bindings)
 log=logs/(label+'.log'); t=time.monotonic()
 with log.open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'label':label,'command':list(map(str,args)),'exit':p.returncode,'elapsedSeconds':time.monotonic()-t};commands.append(row);(logs/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==expect,(label,p.returncode,log)
def report(w):return w.parent/'reports'/w.name
def inspect(world,n,q):
 h=json.loads((world/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['result']==0 and len(h['decoders'])==n and h['totalClassBytes']<=262144
 cp=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256']
 d.inspect(cp); active={x['classIndex'] for x in d.inspect(cp)['initialization'] if x['state']==2};assert set(range(n)).issubset(active),(n,q,active)
 return {'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'totalClassBytes':h['totalClassBytes'],'counters':h['counters']}
spec=importlib.util.spec_from_file_location('checkpoint_diagnostic',here/'checkpoint_diagnostic.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
driver=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json';rows={}
for n in (27,28):
 baseline=None
 for q in (1,7,4096):
  w=out/('world-%d-q%d'%(n,q));a=[driver,'setup-chain',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)]
  run('%d-q%d-start'%(n,q),a,str(n));run('%d-q%d-finish'%(n,q),[driver,'finish',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)],str(n));run('%d-q%d-reopen'%(n,q),[driver,'verify',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)],str(n))
  x=inspect(w,n,q);rows['%d/q%d'%(n,q)]=x
  if baseline is None:baseline=x
  else:
   for k in ('machineRoot','opaquePayloadSHA256'):assert x[k]==baseline[k],(n,q,k)
w=out/'world-28-reordered';run('28-reordered-start',[driver,'setup-chain',w,coord,engine,fixtures/'28.zip','4096'],'28-reordered');run('28-reordered-finish',[driver,'finish',w,coord,engine,fixtures/'28.zip','4096'],'28-reordered');run('28-reordered-reopen',[driver,'verify',w,coord,engine,fixtures/'28.zip','4096'],'28-reordered');x=inspect(w,28,4096);h=json.loads((w/'durable-head.json').read_text());base=json.loads((out/'world-28-q4096/durable-head.json').read_text());assert h['packageRoot']!=base['packageRoot'];x['packageRoot']=h['packageRoot'];rows['28/reordered']=x
# The local driver guard sees28 before any state installation, so no world exists.
w=out/'world-29';run('29-pre-mutation-refusal',[driver,'setup-chain',w,coord,engine,fixtures/'29.zip','4096'],'29',expect=2);assert not w.exists()
# Exact aggregate boundary is Java-8-valid but this fixed profile's raw parser refuses it without mutating a head. +1 reaches the independent constructor aggregate guard before engine execution.
w=out/'world-28-262144';run('262144-start',[driver,'setup-chain',w,coord,engine,fixtures/'28-262144.zip','4096'],'28-262144');b=json.loads((report(w)/'start-refusal.json').read_text());assert b['selector']=='0x71540d20' and b['uint256Words']==['1','0'] and b['rootUnchanged'];rows['28/262144-infeasible']=b
w=out/'world-28-262145';run('262145-constructor-refusal',[driver,'boundary-create',w,coord,engine,fixtures/'28-262145.zip','4096'],'28-262145');b=json.loads((report(w)/'boundary-refusal.json').read_text());assert b['selector']=='0xab23ed08' and b['uint256Words']==['12'] and b['rootUnchanged'];rows['28/262145']=b
summary={'profile':'MC-CLASSCOUNT28-PREFLIGHT1','generatedOnly':True,'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
