#!/usr/bin/env python3
"""Owned COPY test observer hooks for late cancellation and prior-Head read errors."""
from pathlib import Path
import base64,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;base=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
s=(root/'evidence/java-evm/main-root/atomicity-preflight/transport/atomicity_session.go.txt').read_text()
if '--fixed' in sys.argv:
 script=here/'repair_copy.py';p=out/'source.go.txt';p.write_text(s);subprocess.run([sys.executable,str(script),str(p)],check=True);s=p.read_text()
a='out, left, err := v.Call(c.Origin, to, data, c.GasLimit, uint256.MustFromBig(c.Value))';assert s.count(a)==1;s=s.replace(a,a+'\nif os.Getenv("MR0_PARENT_PAUSE_AFTER_CALL")=="1" {time.Sleep(callTimeout()+20*time.Millisecond)}')
a='out, addr, left, err := v.Create(c.Origin, code, c.GasLimit, uint256.MustFromBig(c.Value))';assert s.count(a)==1;s=s.replace(a,a+'\nif os.Getenv("MR0_PARENT_PAUSE_AFTER_CREATE")=="1" {time.Sleep(callTimeout()+20*time.Millisecond)}')
a='previous, previousErr := readManifest(e.dir)';assert s.count(a)==1;s=s.replace(a,'if os.Getenv("MR0_PARENT_UNREADABLE_PRIOR")=="1" {must(os.Chmod(filepath.Join(e.dir,"durable-head.json"),0000))}\n'+a)
a='switch os.Args[1] {';assert s.count(a)==1;s=s.replace(a,a+'\ncase "parent-late-cancel", "parent-prior-read", "parent-poison":\nparentProbe(os.Args[2],os.Args[3],os.Args[1])')
s=s.replace('case "setup-chain":','case "parent-late-create":parentCreateProbe(os.Args[2],os.Args[3])\ncase "setup-chain":',1)
s+='\n'+(here/'probe_driver.go.txt').read_text();p=out/'main.go';p.write_text(s);subprocess.run(['gofmt','-w',str(p)],check=True);exe=out/'probe';subprocess.run(['go','build','-race','-trimpath','-o',str(exe),str(p)],cwd=root,env=env,check=True)
summary={}
for case in ('parent-late-cancel','parent-prior-read','parent-poison'):
 w=out/case;args=[str(w),str(base/'artifacts/coordinator/MR0MainCoordinator.json'),str(base/'artifacts/engine/MR0MainInterpreter.json'),str(base/'fixtures/positive.zip'),'1']
 for mode in ('setup-chain',case):
  cmd=[str(exe),mode]+args
  if mode=='parent-poison':cmd=['strace','-f','-yy','-e','trace=fsync,fdatasync,rename,renameat,renameat2','-o',str(out/'poison-syscalls.log')]+cmd
  with (out/(case+'-'+mode+'.log')).open('w') as f:subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
 r=json.loads((out/'reports'/case/'parent-probe.json').read_text());summary[case]=r
 if case=='parent-late-cancel':
  assert r['error']!='<nil>' and r['oldRoot']==r['afterRoot'] and r['priorHeadBytes']==r['afterHeadBytes']
  assert (r['failedOutputHex']=='0x')==('--fixed' in sys.argv)
  assert r['retryError']=='<nil>'
 elif case=='parent-prior-read':
  assert 'permission denied' in r['error'] and r['oldRoot']==r['afterRoot'] and r['priorHeadBytes']==r['afterHeadBytes']
  assert r['poisoned']==('--fixed' in sys.argv) and r['retryError']!='<nil>'
 else:
  assert r['poisoned'] and r['retryGas']==r['poisonCreateGas']==0 and r['retryError']!='<nil>' and r['poisonCreateError']!='<nil>' and r['poisonPublishError']!='<nil>' and r['postProbeHeadUnchanged']
 # A separate process reopens the actual published authority, not any failed trace.
 with (out/(case+'-reopen.log')).open('w') as f:subprocess.run([str(exe),'verify']+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
r=summary['parent-poison'];before=json.loads(base64.b64decode(r['priorHeadBytes']));after=json.loads(base64.b64decode(r['afterHeadBytes']))
lines=(out/'poison-syscalls.log').read_text().splitlines();renames=[i for i,l in enumerate(lines) if 'rename' in l and '/durable-head.json' in l and l.endswith('= 0')];assert len(renames)==1
world=out/'parent-poison';syncs=[l for l in lines[renames[0]+1:] if 'fsync(' in l and ('<'+str(world)+'>) = 0') in l];assert len(syncs)==0
claimed=after['counters']['directorySyncs']-before['counters']['directorySyncs'];assert claimed==(0 if '--fixed' in sys.argv else 1)
r['syscallConfirmedDirectorySyncsAfterHeadRename']=len(syncs);r['publishedDirectorySyncCounterDelta']=claimed
world=out/'parent-late-create';args=[str(world),str(base/'artifacts/coordinator/MR0MainCoordinator.json'),str(base/'artifacts/engine/MR0MainInterpreter.json'),str(base/'fixtures/positive.zip'),'1']
for mode in ('setup-chain','parent-late-create','verify'):
 with (out/('create-'+mode+'.log')).open('w') as f:subprocess.run([str(exe),mode]+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
r=json.loads((out/'reports/parent-late-create/parent-create-probe.json').read_text());assert r['error']!='<nil>' and r['oldRoot']==r['afterRoot'] and r['headBytesEqual'] and r['retryError']=='<nil>'
assert (r['address']=='0x'+'00'*20 and r['createdCodeBytes']==r['outputBytes']==0)==('--fixed' in sys.argv)
(out/'create-report.json').write_text(json.dumps(r,indent=2)+'\n')
(out/'report.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:{f:r[f] for f in ('error','gas','poisoned','retryError','retryGas')}|{'failedOutputBytes':(len(r['failedOutputHex'])-2)//2} for k,r in summary.items()},indent=2))
