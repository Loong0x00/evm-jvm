#!/usr/bin/env python3
"""Fresh full parent narrow-atomicity gate, under canonical whole-group watchdog."""
from pathlib import Path
import base64,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
b=out.with_name(out.name+'-matrix');run('matrix',[sys.executable,here/'replay.py',b,'--fixed'])
# Independently compare captured pre-failure bytes and every retry/newly-published
# EVM root/CP against a normal two-slice control using the same opaque fixture.
exe=b/'mr0-atomicity';control=out/'control';args=[control,b/'artifacts/coordinator/MR0MainCoordinator.json',b/'artifacts/engine/MR0MainInterpreter.json',b/'fixtures/positive.zip',1]
for mode in ('setup-chain','resume-one','verify'):run('control-'+mode,[exe,mode]+args)
c=json.loads((control/'durable-head.json').read_text());points=json.loads((b/'atomicity-summary.json').read_text())['points'];checked=0
for point in points:
 name=point['point'];name={'actual-os-checkpoint-EACCES':'os-eacces','actual-os-manifest-dir-EACCES':'os-manifest'}.get(name,name)
 w=b/('world-'+name);h=json.loads((w/'durable-head.json').read_text())
 for k in ('trieRoot','epoch','checkpointRoot','machineRoot','vfsRoot','jvmSteps','internalSteps','lifecycle','outcome','javaKind','javaRef','javaClass'):assert h[k]==c[k],(name,k)
 assert (w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes()==(control/'checkpoints'/(c['checkpointSHA256']+'.bin')).read_bytes()
 if name not in ('manifest-after-rename','manifest-after-dirsync','os-eacces','os-manifest'):
  r=json.loads((b/'reports'/w.name/'atomicity-retry.json').read_text());before=(b/(name+'-same-session-before-head.json')).read_bytes()
  assert base64.b64decode(r['priorHeadBytes'])==base64.b64decode(r['afterFaultHeadBytes'])==before
  assert r['failedOutputHex']=='0x' and r['failedCheckpointBytes']==r['failedSliceSchema']==0 and r['beforeRoot']==json.loads(before)['trieRoot'] and r['retryRoot']==c['trieRoot']
 checked+=1
# strace proves no guessed directory fsync after rename; persisted snapshots do
# NOT include an operation that can only happen after their serialization.
syscallChecks={}
for point,want in [('manifest-after-rename',0),('manifest-after-dirsync',1)]:
 label=point+'-public';w=b/('world-'+point);lines=(b/(label+'-syscalls.log')).read_text().splitlines()
 ren=[i for i,l in enumerate(lines) if 'rename' in l and '/durable-head.json' in l and l.endswith('= 0')];assert len(ren)==1
 actual=sum('fsync(' in l and ('<'+str(w)+'>) = 0') in l for l in lines[ren[0]+1:]);assert actual==want
 syscallChecks[point]={'actualDirectorySyncsAfterRename':actual}
p=out.with_name(out.name+'-probes');run('race-probes',[sys.executable,here/'probe.py',b,p,'--fixed'])
create=json.loads((p/'create-report.json').read_text());assert create['retryRoot']==c['trieRoot'] and create['outputBytes']==create['createdCodeBytes']==0
run('accepted-cb0',['go','test','-count=1','./jvmevm/localcontinuation/cb0'])
protected=subprocess.check_output(['git','diff','26e528965','--','jvmevm','core','params','consensus','eth','Makefile'],cwd=root);assert not protected;(out/'protected.diff').write_bytes(protected)
(out/'summary.json').write_text(json.dumps({'faultWorldsComparedToControl':checked,'strictReceiptResult':json.loads((b/'strict-positive.log').read_text()),'syscallChecks':syscallChecks,'lateCreateCancellation':create,'scope':'narrow COPY atomicity only; no full Session/promotion/original Java'},indent=2)+'\n')
print('PASS: fixed COPY,13 fault/retry worlds vscontrol,12positive worlds427strictreceipts,realOSfailures,postpoisonops,Go-race lateCALL/CREATEcancel+prior-read probes,strace IO,acceptedCB0regression')
