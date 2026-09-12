#!/usr/bin/env python3
"""Parent independent build/basic kernel replay, NOT full MR0 transport acceptance."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];w=root/'evidence/java-evm/main-root/repair-preflight';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-main-root-repair-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,cwd=root):
 args=list(map(str,args))
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'command':args,'exit':code})+'\n')
 assert code==0,(label,code)
 return p.pid
# Copy SOURCE ONLY so the fresh compiler cannot silently reuse archived artifacts.
for kind,name in [('engine','MR0MainInterpreter'),('coordinator','MR0MainCoordinator')]:
 d=out/'artifacts'/kind;d.mkdir(parents=True)
 for n in (name+'.sol','build.js'):shutil.copy2(w/kind/n,d/n)
 run(kind+'-build',['node',d/'build.js'])
e=json.loads((out/'artifacts/engine/MR0MainInterpreter.json').read_text());c=json.loads((out/'artifacts/coordinator/MR0MainCoordinator.json').read_text());assert hashlib.sha256(bytes.fromhex(e['deployedBytecode'])).hexdigest()=='5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875'
assert c['codeHashes']['runtimeKeccak256']=='06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c'
shutil.copy2(w/'transport/driver.go.txt',out/'main.go');run('driver-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']);run('driver-vet',['go','vet',out/'main.go'])
run('fixtures',[sys.executable,w/'transport/fixtures/generate-positive-exception.py',out/'fixtures'])
summary={}
for kind in ('positive','rebind','rebind-new','exception'):
 pairs=[]
 for q in (1,7,4096):
  d=out/(kind+'-q'+str(q));args=[d,out/'artifacts/coordinator/MR0MainCoordinator.json',out/'artifacts/engine/MR0MainInterpreter.json',out/'fixtures'/(kind+'.zip'),q]
  pids=[run(d.name+'-'+mode,[out/'driver',mode]+args) for mode in ('setup-chain','finish','verify')]
  assert len(set(pids))==3
  m=json.loads((d/'durable-head.json').read_text());assert m['stage']=='final-reopened' and m['quantum']==q and m['result']==0
  assert m['engineCodeHash']=='0x'+e['codeHashes']['runtimeKeccak256'] and m['coordinatorCodeHash']=='0x'+c['codeHashes']['runtimeKeccak256']
  assert m['counters']['maxGas']<=100000000 and m['counters']['maxCallMs']<=30000
  # A terminal-exception no-op finish opens but does not publish a manifest;
  # don't fabricate persisted PID evidence for it. External process receipts
  # still establish that all three real processes were launched successfully.
  expected=[pids[0],pids[2]] if kind=='exception' and q==4096 else pids
  assert m['processPids']==expected,(kind,q,m['processPids'],expected)
  cp=(d/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==m['checkpointSHA256'] and len(cp)<=1048576
  if kind=='exception':assert m['lifecycle']==m['outcome']==3
  else:assert m['lifecycle']==m['outcome']==2
  pairs.append((m,cp[280:]))
 for m,cp in pairs[1:]:
  for k in ('machineRoot','vfsRoot','lifecycle','outcome','jvmSteps','internalSteps','javaKind','javaClass'):assert m[k]==pairs[0][0][k],(kind,k)
  assert cp==pairs[0][1],(kind,'opaque terminal payload')
 summary[kind]={'epochs':[m['epoch'] for m,cp in pairs],'jvmSteps':pairs[0][0]['jvmSteps'],'internalSteps':pairs[0][0]['internalSteps'],'maxGas':max(m['counters']['maxGas'] for m,cp in pairs),'maxCallMs':max(m['counters']['maxCallMs'] for m,cp in pairs),'payloadSHA256':hashlib.sha256(pairs[0][1]).hexdigest()}
run('worker-verifier',[sys.executable,w/'strict_verify.py',out])
(out/'parent-summary.json').write_text(json.dumps({'worlds':12,'scope':'independent kernel/basic transport replay only; full Session/persistence/refusal/event/read-return gates remain','cases':summary},indent=2)+'\n');print(json.dumps(summary,indent=2))
