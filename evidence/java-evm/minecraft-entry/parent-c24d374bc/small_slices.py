#!/usr/bin/env python3
"""Lower only the existing public ResumeMain instruction budget; same engine/CP.
The saved default quantum, gas/reserve, interpreter and authoritative CP are not
rewritten. Failed q7 receipt is preserved before attempting fresh q1 calls.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();worlds=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
s=(build/'main.go').read_text();a='func doResume(dir, artPath string, one bool) {';assert s.count(a)==1;s=s.replace(a,'''func doResume(dir, artPath string, one bool) { doResumeBudget(dir,artPath,one,0) }
func doResumeBudget(dir, artPath string, one bool, smaller uint64) {''')
a='''cp := readCheckpoint(e)
		args := []interface{}{[32]byte(e.m.PackageRoot), e.m.Epoch, [32]byte(e.m.CheckpointRoot), cp, e.m.Quantum, uint32(4096)}''';assert s.count(a)==1;s=s.replace(a,'''cp := readCheckpoint(e)
        budget := e.m.Quantum
        if smaller != 0 { if smaller > budget { panic("not a smaller slice") }; budget=smaller }
		args := []interface{}{[32]byte(e.m.PackageRoot), e.m.Epoch, [32]byte(e.m.CheckpointRoot), cp, budget, uint32(4096)}''')
a='case "resume-one", "atomicity-resume":';assert s.count(a)==1;s=s.replace(a,'''case "resume-one-q1":
        doResumeBudget(os.Args[2],os.Args[3],true,1)
    '''+a)
p=out/'main.go';p.write_text(s)
for args in (['gofmt','-w',str(p)],['go','build','-trimpath','-o',str(out/'driver'),str(p)],['go','vet',str(p)]):subprocess.run(args,cwd=root,env=env,check=True)
w=worlds/'official';rep=worlds/'reports/official';f=rep/'resume-refusal.json';assert f.is_file();r=json.loads(f.read_text());assert r['selector']=='0xf15d7343' and r['uint256Words']==['7']
shutil.copy2(f,out/'prior-q7-refusal.json');saved=rep/'prior-q7-refusal.json';assert not saved.exists();f.rename(saved)
shutil.copy2(w/'durable-head.json',out/'prior-head.json')
spec=importlib.util.spec_from_file_location('diag',here/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json','unused',1];rows=[]
for n in range(1,65):
 before=(w/'durable-head.json').read_bytes();old=json.loads(before)
 with (out/('resume-%d.log'%n)).open('w') as log:
  p=subprocess.Popen(list(map(str,[out/'driver','resume-one-q1',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT);rc=p.wait()
 (out/('resume-%d-process.json'%n)).write_text(json.dumps({'pid':p.pid,'exit':rc,'requestedJvmSteps':1})+'\n');assert rc==0
 if f.exists():
  r=json.loads(f.read_text());assert r['rootBefore']==r['rootAfter']==old['trieRoot'];assert (w/'durable-head.json').read_bytes()==before
  shutil.copy2(f,out/'q1-refusal.json');print(json.dumps({k:r.get(k) for k in ('error','selector','uint256Words','diagnostic','gas')},indent=2));break
 h=json.loads((w/'durable-head.json').read_text());assert h['quantum']==old['quantum'] and h['epoch']==old['epoch']+1 and 0<=h['jvmSteps']-old['jvmSteps']<=1
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();diag=d.inspect(cp);rows.append({'head':h,'diagnostic':diag});(out/('epoch-%d.json'%h['epoch'])).write_text(json.dumps(rows[-1],indent=2)+'\n')
 if h['lifecycle']!=1:break
else:raise AssertionError('64 one-step observation bound reached; inspect')
with (out/'fresh-reopen.log').open('w') as log:subprocess.run(list(map(str,[out/'driver','verify',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
with (out/'verified-receipts.json').open('w') as log:subprocess.run(['node',str(here.parent/'parent-f780f1a13/verify_receipts.js'),str(build),str(worlds),'official'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Same-code successful q1 continuations:',len(rows))
