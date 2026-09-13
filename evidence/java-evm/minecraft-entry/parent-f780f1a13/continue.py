#!/usr/bin/env python3
"""Continue ONLY actual successful EVM checkpoints; stop at next measured refusal."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
import importlib.util
spec=importlib.util.spec_from_file_location('checkpoint_diagnostic',Path(__file__).resolve().parents[4]/'evidence/java-evm/minecraft-entry/parent-f780f1a13/checkpoint_frames.py');diagmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagmodule);inspect=diagmodule.inspect
root=Path(__file__).resolve().parents[4];build=Path(sys.argv[1]).resolve();label=sys.argv[2];out=Path(sys.argv[3]).resolve();jar=Path(sys.argv[4]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'));w=build/label;rep=build/'reports'/label;execution=Path(sys.argv[5]).resolve() if len(sys.argv)>5 else build
args=[str(w),str(execution/'coordinator/MCEntryCoordinator.json'),str(execution/'engine/MCEntryInterpreter.json'),str(jar),'1'];rows=[]
def observe():
 m=json.loads((w/'durable-head.json').read_text());cp=(w/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();diag=inspect(cp);assert diag['checkpointSHA256']==m['checkpointSHA256'] and diag['javaSteps']==m['jvmSteps']
 (out/('epoch-%d.json'%m['epoch'])).write_text(json.dumps({'head':m,'diagnostic':diag},indent=2)+'\n');(out/('epoch-%d.checkpoint'%m['epoch'])).write_bytes(cp);rows.append({'epoch':m['epoch'],'jvm':m['jvmSteps'],'diagnostic':diag});return m
old=observe()
for n in range(1,513):
 with (out/('resume-%d.log'%n)).open('w') as f:
  p=subprocess.Popen([str(execution/'driver'),'resume-one']+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/('resume-%d-process.json'%n)).write_text(json.dumps({'pid':p.pid,'exit':code})+'\n');assert code==0
 failure=rep/'resume-refusal.json'
 if failure.exists():
  r=json.loads(failure.read_text());assert r['rootBefore']==r['rootAfter']==old['trieRoot'];assert (w/'checkpoints'/(old['checkpointSHA256']+'.bin')).is_file();shutil.copy2(failure,out/'refusal.json');print(json.dumps({k:r.get(k) for k in ('error','diagnostic','selector','uint256Words','gas')},indent=2));break
 old=observe()
 if old['lifecycle']!=1:break
else:raise AssertionError('bounded frontier observation reached512 successful slices; inspect before extending')
# Validate successful current EVM head/checkpoint in an additional fresh process.
with (out/'reopen.log').open('w') as f:subprocess.run([str(execution/'driver'),'verify']+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
(out/'summary.json').write_text(json.dumps({'successfulStates':rows,'lastPublishedEpoch':old['epoch'],'lastPublishedJavaSteps':old['jvmSteps']},indent=2)+'\n');print('last successful Java steps',old['jvmSteps'])
