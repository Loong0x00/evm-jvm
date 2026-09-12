#!/usr/bin/env python3
"""Negative TEST copies only; mutated receipts are NEVER passed to Java/EVM."""
from pathlib import Path
import json,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];base=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();v=root/'evidence/java-evm/main-root/session-preflight/strict_verify.py';report={}
for label in ('exception-zero-ref','zero-package','false-event','wrong-coordinator-code'):
 d=out/('java-diff-mc-main-root-session-verifier-'+label);d.mkdir()
 for kind in ('engine','coordinator'):
  src=base/'artifacts'/kind;dest=d/'artifacts'/kind;dest.mkdir(parents=True)
  for p in src.iterdir():
   if p.suffix in ('.json','.sol'):shutil.copy2(p,dest/p.name)
 for src in base.glob('*-q*'):
  if not src.is_dir():continue
  dst=d/src.name;dst.mkdir();shutil.copy2(src/'STORE-FORMAT',dst/'STORE-FORMAT');shutil.copy2(src/'durable-head.json',dst/'durable-head.json')
  m=json.loads((src/'durable-head.json').read_text());(dst/'checkpoints').mkdir();cp=m['checkpointSHA256']+'.bin';shutil.copy2(src/'checkpoints'/cp,dst/'checkpoints'/cp)
 shutil.copytree(base/'reports',d/'reports')
 if label=='exception-zero-ref':
  for q in (1,7,4096):
   p=d/('exception-q'+str(q))/'durable-head.json';j=json.loads(p.read_text());j.update(javaRef=0,javaClass='');p.write_text(json.dumps(j))
 elif label=='zero-package':
  p=d/'positive-q1/durable-head.json';j=json.loads(p.read_text());j.update(packageRoot='0x'+'00'*32,instanceId='0x'+'00'*32);p.write_text(json.dumps(j))
 elif label=='false-event':
  p=sorted((d/'reports/positive-q1').glob('slice-*.json'))[0];j=json.loads(p.read_text());j['nestedLogs'][0]['address']='0x'+'00'*20;p.write_text(json.dumps(j))
 else:
  p=d/'artifacts/coordinator/MR0MainCoordinator.json';j=json.loads(p.read_text());r=j['deployedBytecode'];j['deployedBytecode']=('ff' if r[:2]!='ff' else 'fe')+r[2:];p.write_text(json.dumps(j))
 with (out/(label+'.log')).open('w') as f:r=subprocess.run([sys.executable,str(v),str(d)],stdout=f,stderr=subprocess.STDOUT)
 report[label]={'exit':r.returncode,'incorrectlyAccepted':r.returncode==0}
 assert r.returncode==0,(label,'original verifier no longer exposes recorded weakness')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
