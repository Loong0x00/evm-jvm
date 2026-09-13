#!/usr/bin/env python3
"""Continue the authorized LOCAL1B run after correcting read-only frame diagnostics."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];basis=here.parent/'parent-c24d374bc';execution=Path(sys.argv[1]).resolve();worlds=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
spec=importlib.util.spec_from_file_location('d',here/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
w=worlds/'official';rep=worlds/'reports/official';args=[w,basis/'coordinator/MCEntryCoordinator.json',basis/'engine/MCEntryInterpreter.json','unused',7]
f=rep/'resume-refusal.json';assert not f.exists();rows=[]
for n in range(1,513):
 before=(w/'durable-head.json').read_bytes();old=json.loads(before)
 if old['lifecycle']!=1:break
 with (out/('call-%d.log'%n)).open('w') as log:
  p=subprocess.Popen(list(map(str,[execution/'driver','resume-one',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT);rc=p.wait()
 (out/('call-%d-process.json'%n)).write_text(json.dumps({'pid':p.pid,'exit':rc,'suppliedGas':1000000000,'requestedJvmSteps':old['quantum']})+'\n');assert rc==0
 if f.exists():
  r=json.loads(f.read_text());assert r['rootBefore']==r['rootAfter']==old['trieRoot'] and (w/'durable-head.json').read_bytes()==before;shutil.copy2(f,out/'refusal.json');print(json.dumps({k:r.get(k) for k in ('error','diagnostic','selector','uint256Words','gas')},indent=2));break
 h=json.loads((w/'durable-head.json').read_text());cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();r=json.loads((rep/('slice-%020d.json'%h['epoch'])).read_text());assert r['gasUsed']<=1000000000 and r['elapsedMS']<=30000
 v={'head':h,'gasUsed':r['gasUsed'],'diagnostic':d.inspect(cp)};rows.append(v);(out/('epoch-%d.json'%h['epoch'])).write_text(json.dumps(v,indent=2)+'\n')
 if h['lifecycle']!=1:break
else:raise AssertionError('512 observation batch completed; inspect before extending')
with (out/'reopen.log').open('w') as log:subprocess.run(list(map(str,[execution/'driver','verify',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');h=json.loads((w/'durable-head.json').read_text());print(json.dumps({k:h[k] for k in ('epoch','jvmSteps','internalSteps','lifecycle','outcome','javaKind','checkpointRoot')},indent=2))
