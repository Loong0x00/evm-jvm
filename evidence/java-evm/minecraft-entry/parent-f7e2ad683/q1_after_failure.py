#!/usr/bin/env python3
"""After preserving q7 refusal, lower public instruction budget to1 on same-code CP."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();worlds=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
w=worlds/'official';rep=worlds/'reports/official';f=rep/'resume-refusal.json';assert f.is_file();before=json.loads((w/'durable-head.json').read_text());shutil.copy2(f,out/'initial-q7-refusal.json');f.rename(rep/'initial-q7-refusal.json')
spec=importlib.util.spec_from_file_location('d',here/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json','unused',1];rows=[]
for n in range(1,257):
 old=json.loads((w/'durable-head.json').read_text());oldbytes=(w/'durable-head.json').read_bytes()
 with (out/('q1-%d.log'%n)).open('w') as log:
  p=subprocess.Popen(list(map(str,[build/'driver','resume-one-q1',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT);rc=p.wait()
 (out/('q1-%d-process.json'%n)).write_text(json.dumps({'pid':p.pid,'exit':rc,'requestedJvmSteps':1,'suppliedGas':1000000000})+'\n');assert rc==0
 if f.exists():
  r=json.loads(f.read_text());assert r['rootBefore']==r['rootAfter']==old['trieRoot'] and (w/'durable-head.json').read_bytes()==oldbytes;shutil.copy2(f,out/'q1-refusal.json');print(json.dumps({k:r.get(k) for k in ('error','diagnostic','selector','uint256Words','gas')},indent=2));break
 h=json.loads((w/'durable-head.json').read_text());r=json.loads((rep/('slice-%020d.json'%h['epoch'])).read_text());assert h['quantum']==7 and h['epoch']==old['epoch']+1 and h['jvmSteps']-old['jvmSteps']<=1 and r['slice']['executedJvmSteps']<=1 and r['executionBudget']=='LOCAL1B-USER-AUTHORIZED' and r['suppliedGas']==1000000000
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();v={'head':h,'gas':r['gasUsed'],'diagnostic':d.inspect(cp)};rows.append(v);(out/('epoch-%d.json'%h['epoch'])).write_text(json.dumps(v,indent=2)+'\n')
 if h['lifecycle']!=1:break
else:print('256 successful q1 observations reached; still running')
with (out/'reopen.log').open('w') as log:subprocess.run(list(map(str,[build/'driver','verify',*args])),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'summary.json').write_text(json.dumps({'initialHead':before,'successfulQ1':rows,'lastHead':json.loads((w/'durable-head.json').read_text())},indent=2)+'\n');print('successful q1',len(rows),'last Java',json.loads((w/'durable-head.json').read_text())['jvmSteps'])
