#!/usr/bin/env python3
"""Check actual outcomes, not the host driver's misleading final-reopened label."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();mode=sys.argv[3]
assert mode in ('candidate','repaired','edges') and not out.exists();out.mkdir();(out/'tmp').mkdir()
names='EdgeMain.class,EdgeMain$Marker.class,EdgeMain$A.class,EdgeMain$B.class' if mode=='edges' else 'ArraycopyMain.class,ArraycopyMain$A.class,ArraycopyMain$B.class'
env=dict(os.environ,TMPDIR=str(out/'tmp'),MC_ENTRY_BINDINGS=names,PYTHONDONTWRITEBYTECODE='1')
def call(label,args):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'command':list(map(str,args))})+'\n');assert code==0,(label,code)
call('fixtures',[sys.executable,here/'generate-edges.py' if mode=='edges' else here.parent/'arraycopy-preflight/fixtures/generate-arraycopy.py',out/'fixtures'])
call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',out/'fixtures/classes','EdgeMain' if mode=='edges' else 'ArraycopyMain'])
spec=importlib.util.spec_from_file_location('diag',here/'checkpoint_frames.py');diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
summary={};reference=None
for q in (1,7,4096):
 w=out/('q'+str(q));args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',out/'fixtures/arraycopy.zip',q];rep=out/'reports'/w.name
 call('q%d-start'%q,[build/'driver','setup-chain']+args)
 if not (rep/'start-refusal.json').exists():
  call('q%d-finish'%q,[build/'driver','finish']+args)
  call('q%d-verify'%q,[build/'driver','verify']+args)
 m=json.loads((w/'durable-head.json').read_text());refusals=[json.loads(p.read_text()) for p in rep.glob('*refusal.json')]
 r={'epoch':m['epoch'],'java':m['jvmSteps'],'internal':m['internalSteps'],'lifecycle':m['lifecycle'],'outcome':m['outcome'],'machineRoot':m['machineRoot'],'refusals':refusals}
 if m['epoch']:
  cp=(w/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==m['checkpointSHA256'];r['diagnostic']=diag.inspect(cp);r['payloadSHA256']=hashlib.sha256(cp[280:]).hexdigest()
 if mode=='candidate':
  assert len(refusals)==1 and refusals[0]['selector']=='0x4e487b71' and refusals[0]['uint256Words']==['50']
  assert refusals[0]['rootBefore']==refusals[0]['rootAfter'] and m['lifecycle']==(0 if q==4096 else 1)
  assert m['jvmSteps']=={1:176,7:175,4096:0}[q]
 elif mode=='repaired' and q==4096 and refusals:
  assert len(refusals)==1 and refusals[0]['selector']=='0xf15d7343' and refusals[0]['uint256Words']==['7'] and m['epoch']==0
  r['scope']='ordinary reserve refusal, no rescue'
 else:
  assert not refusals and m['lifecycle']==m['outcome']==2,r
  values=next(x['staticValues'] for x in r['diagnostic']['initialization'] if x['classIndex']==0)
  assert len(values)==1 and (int(values[0]['packedValue'],16)&((1<<64)-1))==(0x1234 if mode=='edges' else 4107)
  if reference is None:reference=cp[280:]
  else:assert reference==cp[280:],'terminal opaque payload mismatch'
 j=i=0
 for n,p in enumerate(sorted(rep.glob('slice-*.json')),1):
  v=json.loads(p.read_text());s=v['slice'];assert v['epoch']==s['epoch']==n and 0<v['gasUsed']<=100000000 and v['elapsedMS']<=30000 and s['executedJvmSteps']<=q and s['totalJvmSteps']==j+s['executedJvmSteps'] and s['totalInternalSteps']==i+s['executedInternalSteps'] and len(v['nestedLogs'])==1
  j,i=s['totalJvmSteps'],s['totalInternalSteps']
 assert j==m['jvmSteps'] and i==m['internalSteps']
 summary[str(q)]=r;(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
