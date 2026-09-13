#!/usr/bin/env python3
"""User-authorized LOCAL1B CALL budget; same pinned EVM code and genuine checkpoint.
No change to interpreter/core/consensus/gas schedule, reserve, time or memory caps.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];basis=here.parent/'parent-c24d374bc'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-local1b-') and not out.exists();out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
s=(basis/'executed_smaller_driver.go.txt').read_text();a='const ordinaryGas = uint64(100_000_000)';assert s.count(a)==1;s=s.replace(a,'// Explicit user-authorized LOCAL-only external call ceiling; EVM gas accounting unchanged.\nconst ordinaryGas = uint64(1_000_000_000)')
a='"method": method, "epoch": d.Slice.Epoch,';assert s.count(a)==1;s=s.replace(a,'"executionBudget":"LOCAL1B-USER-AUTHORIZED", "suppliedGas":ordinaryGas, '+a)
a='"diagnostic": missingDiagnostic(r.Out),';assert s.count(a)==1;s=s.replace(a,'"executionBudget":"LOCAL1B-USER-AUTHORIZED", "suppliedGas":ordinaryGas, '+a)
p=out/'main.go';p.write_text(s)
for args in (['gofmt','-w',str(p)],['go','build','-trimpath','-o',str(out/'driver'),str(p)],['go','vet',str(p)]):subprocess.run(args,cwd=root,env=env,check=True)
worlds=root/'build/java-diff-mc-properties-parent-official20-c24d374bc';w=worlds/'official';rep=worlds/'reports/official'
h=json.loads((w/'durable-head.json').read_text());assert h['epoch']==249 and h['jvmSteps']==1683 and h['checkpointSHA256']=='affcf10ae1a90714a60255dc1b13475e62026d412dd38b1993e802b36528d2fe'
(out/'initial-head.json').write_bytes((w/'durable-head.json').read_bytes());cp=w/'checkpoints'/(h['checkpointSHA256']+'.bin');(out/'initial.checkpoint').write_bytes(cp.read_bytes())
f=rep/'resume-refusal.json';assert f.is_file();shutil.copy2(f,out/'prior100M-refusal.json');archive=rep/'prior100M-final-q1-refusal.json';assert not archive.exists();f.rename(archive)
spec=importlib.util.spec_from_file_location('diag',here/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
args=[w,basis/'coordinator/MCEntryCoordinator.json',basis/'engine/MCEntryInterpreter.json','unused',1];rows=[]
for n in range(1,257):
 before=(w/'durable-head.json').read_bytes();old=json.loads(before)
 with (out/('call-%d.log'%n)).open('w') as log:
  proc=subprocess.Popen(list(map(str,[out/'driver','resume-one-q1',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT);rc=proc.wait()
 (out/('call-%d-process.json'%n)).write_text(json.dumps({'pid':proc.pid,'exit':rc,'suppliedGas':1000000000,'requestedJvmSteps':1})+'\n');assert rc==0
 if f.exists():
  r=json.loads(f.read_text());assert r['rootBefore']==r['rootAfter']==old['trieRoot'];assert (w/'durable-head.json').read_bytes()==before;shutil.copy2(f,out/'refusal.json');print(json.dumps(r,indent=2));break
 h=json.loads((w/'durable-head.json').read_text());r=json.loads((rep/('slice-%020d.json'%h['epoch'])).read_text());assert h['epoch']==old['epoch']+1 and h['jvmSteps']<=old['jvmSteps']+1 and r['suppliedGas']==1000000000 and r['gasUsed']<=1000000000 and r['elapsedMS']<=30000
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();v={'head':h,'gasUsed':r['gasUsed'],'diagnostic':d.inspect(cp)};rows.append(v);(out/('epoch-%d.json'%h['epoch'])).write_text(json.dumps(v,indent=2)+'\n')
 if h['lifecycle']!=1:break
else:raise AssertionError('256 one-step observation guard reached; inspect before extending')
with (out/'reopen.log').open('w') as log:subprocess.run(list(map(str,[out/'driver','verify',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'successfulNewSlices':len(rows),'lastHead':h,'lastNewGas':rows[-1]['gasUsed'] if rows else None},indent=2))
