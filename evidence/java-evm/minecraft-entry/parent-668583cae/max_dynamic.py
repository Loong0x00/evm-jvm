#!/usr/bin/env python3
"""LOCAL uint64-max gas continuation; successful checkpoints only, atomically narrow refusals."""
from pathlib import Path
import json,subprocess,sys,time,shutil
root=Path(__file__).resolve().parents[4];world=Path(sys.argv[1]).resolve();build=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();reports=world.parent/'reports'/world.name;refusal=reports/'resume-refusal.json';q=4096;rows=[];MAX=(1<<64)-1
for n in range(1,201):
 before=json.loads((world/'durable-head.json').read_text());before_bytes=(world/'durable-head.json').read_bytes()
 if refusal.exists():refusal.unlink()
 t=time.monotonic();p=subprocess.run([build/'driver','resume-one-qn',world,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json','unused',str(q)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40);wall=time.monotonic()-t;assert p.returncode==0,(p.returncode,p.stdout[-1000:]);after=json.loads((world/'durable-head.json').read_text())
 if refusal.exists():
  r=json.loads(refusal.read_text());assert before_bytes==(world/'durable-head.json').read_bytes() and r['rootBefore']==r['rootAfter'] and r['rootUnchanged'] and r['durableHeadUnchanged'];shutil.copy2(refusal,out/f'{n:03d}-q{q}-refusal.json');rows.append({'n':n,'q':q,'ok':False,'wall':wall,'java':before['jvmSteps'],'gas':r['gas'],'selector':r['selector'],'words':r['uint256Words'],'diagnostic':r.get('diagnostic')});print(rows[-1],flush=True)
  if q==1:break
  q=max(1,q//2);continue
 assert after['epoch']==before['epoch']+1 and 0<after['jvmSteps']-before['jvmSteps']<=q
 receipt=json.load(open(reports/f"slice-{after['epoch']:020d}.json"));assert receipt['executionBudget']=='LOCAL-U64MAX-USER-AUTHORIZED' and receipt['suppliedGas']==MAX and receipt['elapsedMS']<=30000
 rows.append({'n':n,'q':q,'ok':True,'wall':wall,'epoch':after['epoch'],'java':after['jvmSteps'],'delta':after['jvmSteps']-before['jvmSteps'],'internal':after['internalSteps'],'gas':receipt['gasUsed'],'elapsedMS':receipt['elapsedMS'],'checkpointBytes':receipt['checkpointBytes']});print(rows[-1],flush=True)
 if after['lifecycle']!=1:break
 if q<4096:q=min(4096,q*2)
else:print('bounded max-gas telemetry window (200 calls)')
(out/'summary.json').write_text(json.dumps({'schema':1,'suppliedGas':str(MAX),'maxQuantum':4096,'rows':rows,'lastHead':json.loads((world/'durable-head.json').read_text())},indent=2)+'\n')
