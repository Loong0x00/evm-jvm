#!/usr/bin/env python3
"""Actual OS checkpoint-write failure through the worker's public CLI; no private access."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys
root=Path(__file__).resolve().parents[4];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
w=out/'world';exe=build/'mr0-session';common=[str(w),str(build/'artifacts/coordinator/MR0MainCoordinator.json'),str(build/'artifacts/engine/MR0MainInterpreter.json'),str(build/'fixtures/positive.zip'),'1']
def call(label,mode):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen([str(exe),mode]+common,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'command':[str(exe),mode]+common})+'\n');return code
assert call('setup','setup-chain')==0
head=w/'durable-head.json';before=head.read_bytes();old=json.loads(before);(out/'before-head.json').write_bytes(before)
cpdir=w/'checkpoints';mode=stat.S_IMODE(cpdir.stat().st_mode);cp=cpdir/(old['checkpointSHA256']+'.bin');oldcp=cp.read_bytes();assert os.geteuid()!=0
os.chmod(cpdir,0o500)
try:code=call('failed-resume','resume-one')
finally:os.chmod(cpdir,mode)
after=head.read_bytes();new=json.loads(after);(out/'after-head.json').write_bytes(after)
ref=json.loads((out/'reports/world/resume-refusal.json').read_text())
assert code==0 and 'permission denied' in ref['error'] and ref['revertHex']=='0x'
assert cp.read_bytes()==oldcp and old['trieRoot']==new['trieRoot']
# This is the bug, not an expected successful publication: old EVM root with
# fabricated child Head whose checkpoint was never written; retry then cannot run.
assert new['epoch']==old['epoch']+1 and new['checkpointRoot']!=old['checkpointRoot']
assert not (cpdir/(new['checkpointSHA256']+'.bin')).exists()
retry=call('retry','resume-one');assert retry!=0
report={'oldEpoch':old['epoch'],'newEpoch':new['epoch'],'oldRootRetained':old['trieRoot']==new['trieRoot'],'publishedHeadChanged':before!=after,'childCheckpointAbsent':True,'oldCheckpointSHA256':hashlib.sha256(oldcp).hexdigest(),'refusal':ref,'retryExit':retry,'scope':'actual OS failure in new owned world; no engine/code/page/manifest injection'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
