#!/usr/bin/env python3
"""Parent whole-group replay: no detached per-command process groups or pipe deadlock."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;worker=root/'evidence/java-evm/main-root/atomicity-preflight';out=Path(sys.argv[1]).resolve();fixed='--fixed' in sys.argv;sys.argv=sys.argv[:2];assert not out.exists();sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('candidate',worker/'run_atomicity.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def run(out,label,argv,env=None,cwd=None):
 e=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1');e.update(env or {})
 argv=list(map(str,argv))
 if label=='go-build' and fixed:
  subprocess.run([sys.executable,str(here/'repair_copy.py'),str(out/'main.go')],env=e,check=True)
  p=out/'main.go';s=p.read_text()
  a='failed, _ := coordinatorCall(e, ca, engineABI, "resumeMain", args...)';assert s.count(a)==1;s=s.replace(a,'failed, failedDecoded := coordinatorCall(e, ca, engineABI, "resumeMain", args...)')
  a='"sameSession": true, "failedOutputEmpty":';assert s.count(a)==1
  s=s.replace(a,'"priorHeadBytes":beforeBytes, "afterFaultHeadBytes":afterBytes, "failedOutputHex":"0x"+hex.EncodeToString(failed.Out), "failedCheckpointBytes":len(failedDecoded.Checkpoint), "failedSliceSchema":failedDecoded.Slice.Schema, "beforeRoot":beforeRoot, "retryRoot":e.root, "sameSession": true, "failedOutputEmpty":')
  p.write_text(s);subprocess.run(['gofmt','-w',str(p)],check=True)
 if fixed and len(argv)>1 and argv[1] in ('atomicity-retry','atomicity-resume'):
  w=Path(argv[2]);(out/(label+'-before-head.json')).write_bytes((w/'durable-head.json').read_bytes())
  argv=['strace','-f','-yy','-e','trace=fsync,fdatasync,rename,renameat,renameat2','-o',str(out/(label+'-syscalls.log'))]+argv
 start=time.monotonic()
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,argv)),cwd=cwd or root,env=e,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'processGroup':os.getpgrp(),'command':list(map(str,argv)),'exit':code,'seconds':time.monotonic()-start})+'\n')
 assert code==0,(label,code)
m.run=run;m.main()
# Positive cases use the freshly built same executable; no fresh Solidity claim.
positive=out/'positive';positive.mkdir();(positive/'tmp').mkdir();shutil.copytree(out/'artifacts',positive/'artifacts')
for kind,name in [('engine','MR0MainInterpreter'),('coordinator','MR0MainCoordinator')]:shutil.copy2(root/'evidence/java-evm/main-root/session-preflight/artifacts'/kind/(name+'.sol'),positive/'artifacts'/kind/(name+'.sol'))
exe=out/'mr0-atomicity'
for kind in ('positive','rebind','rebind-new','exception'):
 for q in (1,7,4096):
  w=positive/(kind+'-q'+str(q));args=[w,positive/'artifacts/coordinator/MR0MainCoordinator.json',positive/'artifacts/engine/MR0MainInterpreter.json',out/'fixtures'/(kind+'.zip'),q]
  for mode in ('setup-chain','finish','verify'):run(positive,w.name+'-'+mode,[exe,mode]+args)
# Independently build the parent's strict ABI/event/checkpoint verifier.
v=out/'verify.go';shutil.copy2(root/'evidence/java-evm/main-root/session-parent-2cf366518/verify_receipts.go.txt',v)
run(out,'verifier-build',['go','build','-trimpath','-o',out/'verify',v]);run(out,'strict-positive',[out/'verify',positive,root/'evidence/java-evm/main-root/session-preflight'])
run(out,'go-vet',['go','vet',out/'main.go'])
print('PASS: independent Go build, candidate fault matrix, 12 worlds, parent427-ABI/event/CP receipt verifier; broader acceptance remains separate')
