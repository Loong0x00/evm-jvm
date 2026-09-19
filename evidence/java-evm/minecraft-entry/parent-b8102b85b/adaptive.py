#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,time,shutil
root=Path(__file__).resolve().parents[2]
a=Path(__file__).resolve().parent
world=(root/'build/java-diff-mc-thread-local-set-parent-official37a-b8102b85b/official').resolve()
b=(root/'build/java-diff-mc-thread-local-set-parent-build1-b8102b85b').resolve()
driver=a/'driver'; reports=world.parent/'reports'/world.name; refusal=reports/'resume-refusal.json'; out=a/'adaptive-results';out.mkdir(exist_ok=True)
q=4096; rows=[]
for n in range(1,100):
    before=json.loads((world/'durable-head.json').read_text()); before_bytes=(world/'durable-head.json').read_bytes()
    if refusal.exists(): refusal.unlink()
    t=time.monotonic()
    p=subprocess.run([driver,'resume-one-qn',world,b/'coordinator/MCEntryCoordinator.json',b/'engine/MCEntryInterpreter.json','unused',str(q)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    wall=time.monotonic()-t
    assert p.returncode==0,(p.returncode,p.stdout[-1000:])
    after=json.loads((world/'durable-head.json').read_text())
    if refusal.exists():
        r=json.loads(refusal.read_text());assert before_bytes==(world/'durable-head.json').read_bytes();assert r['rootBefore']==r['rootAfter'] and r['rootUnchanged'];shutil.copy2(refusal,out/f'{n:03d}-q{q}-refusal.json');rows.append({'n':n,'q':q,'ok':False,'wall':wall,'java':before['jvmSteps'],'gas':r['gas'],'selector':r['selector'],'diagnostic':r.get('diagnostic')});print(rows[-1],flush=True)
        if q==1:break
        q=max(1,q//2);continue
    assert after['epoch']==before['epoch']+1 and 0<after['jvmSteps']-before['jvmSteps']<=q
    receipt=json.load(open(reports/f"slice-{after['epoch']:020d}.json"));assert receipt['executionBudget']=='LOCAL4P2B-USER-AUTHORIZED' and receipt['suppliedGas']==4200000000 and receipt['elapsedMS']<=30000
    rows.append({'n':n,'q':q,'ok':True,'wall':wall,'epoch':after['epoch'],'java':after['jvmSteps'],'delta':after['jvmSteps']-before['jvmSteps'],'internal':after['internalSteps'],'gas':receipt['gasUsed'],'elapsedMS':receipt['elapsedMS'],'checkpointBytes':receipt['checkpointBytes']});print(rows[-1],flush=True)
    if after['lifecycle']!=1:break
else:raise SystemExit('adaptive bound exhausted')
(out/'summary.json').write_text(json.dumps({'rows':rows,'lastHead':json.loads((world/'durable-head.json').read_text())},indent=2)+'\n')
