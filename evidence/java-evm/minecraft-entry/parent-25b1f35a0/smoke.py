#!/usr/bin/env python3
"""Parent EVM map smoke: ordinary budgets, no rescue, real Java8 test oracle."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),MC_ENTRY_BINDINGS='MapMain.class,MapMain$Key.class')
def call(label,args):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'command':list(map(str,args))})+'\n');assert code==0,(label,code)
call('fixtures',[sys.executable,root/'evidence/java-evm/minecraft-entry/marker-map-preflight/fixtures/generate-platform-map.py',out/'fixtures'])
call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',out/'fixtures/classes','MapMain'])
summary={};reference=None
for q in (1,7,4096):
 w=out/('q'+str(q));args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',out/'fixtures/platform-map.zip',q]
 call('q%d-start'%q,[build/'driver','setup-chain']+args)
 rep=out/'reports'/w.name
 if q==4096:
  f=json.loads((rep/'start-refusal.json').read_text());assert f['selector']=='0xf15d7343' and f['uint256Words']==['7'] and f['rootBefore']==f['rootAfter'] and f['checkpointBytes']==0 and f['gas']<=100000000
  summary[str(q)]={'scope':'ordinary reserve refusal, not OOG or rescued success','receipt':f};continue
 call('q%d-finish'%q,[build/'driver','finish']+args);call('q%d-verify'%q,[build/'driver','verify']+args)
 m=json.loads((w/'durable-head.json').read_text());assert m['lifecycle']==m['outcome']==2 and m['jvmSteps']==1397 and m['internalSteps']==9 and m['epoch']==(1397 if q==1 else 200)
 cp=(w/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==m['checkpointSHA256'];body=cp[280:]
 if reference is None:reference=body
 else:assert reference==body
 j=i=0
 for n,p in enumerate(sorted(rep.glob('slice-*.json')),1):
  r=json.loads(p.read_text());s=r['slice'];assert r['epoch']==s['epoch']==n and 0<r['gasUsed']<=100000000 and r['elapsedMS']<=30000 and s['executedJvmSteps']<=q and s['totalJvmSteps']==j+s['executedJvmSteps'] and s['totalInternalSteps']==i+s['executedInternalSteps'] and len(r['nestedLogs'])==1
  j,i=s['totalJvmSteps'],s['totalInternalSteps']
 assert n==m['epoch'];summary[str(q)]={'epoch':m['epoch'],'java':j,'internal':i,'machineRoot':m['machineRoot'],'payloadSHA256':hashlib.sha256(body).hexdigest()}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
