#!/usr/bin/env python3
"""Run positive and adversarial receipt-only controls; mutated data is never EVM input."""
from pathlib import Path
import json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;base=Path(sys.argv[1]).resolve();exe=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
ref=root/'evidence/java-evm/main-root/session-preflight'
def run(name,path,want):
 with (out/(name+'.log')).open('w') as f:r=subprocess.run([str(exe),str(path),str(ref)],env=env,stdout=f,stderr=subprocess.STDOUT)
 assert (r.returncode==0)==want,(name,r.returncode);return {'exit':r.returncode,'expectedSuccess':want}
report={'positive':run('positive',base,True)}
subprocess.run([sys.executable,str(here/'probe_verifier.py'),str(base),str(out/'mutants')],env=env,check=True,stdout=(out/'original-verifier.log').open('w'))
for d in sorted((out/'mutants').glob('java-diff-*')):
 # The original verifier did not require pending blobs. Supply all genuine
 # pending blobs so rejection is attributable to the intended negative, not
 # an unrelated missing-file check introduced by this stronger verifier.
 for src in base.glob('*-q*/checkpoints/*.bin'):
  dst=d/src.relative_to(base)
  if dst.exists():assert dst.read_bytes()==src.read_bytes()
  else:shutil.copy2(src,dst)
 report[d.name]=run(d.name,d,False)
# Extra independent single-field receipt/CP corruptions on otherwise valid copies.
for name in ('zero-gas','wrong-epoch','wrong-schema','wrong-counter','checkpoint-byte'):
 d=out/('java-diff-mc-main-root-session-extra-'+name);d.mkdir()
 shutil.copytree(base/'artifacts',d/'artifacts');shutil.copytree(base/'reports',d/'reports')
 for src in base.glob('*-q*'):
  if not src.is_dir():continue
  dst=d/src.name;dst.mkdir();shutil.copy2(src/'durable-head.json',dst/'durable-head.json');shutil.copy2(src/'STORE-FORMAT',dst/'STORE-FORMAT');shutil.copytree(src/'checkpoints',dst/'checkpoints')
 p=sorted((d/'reports/positive-q1').glob('slice-*.json'))[0];j=json.loads(p.read_text())
 if name=='zero-gas':j['gasUsed']=0
 elif name=='wrong-epoch':j['epoch']=9876
 elif name=='wrong-schema':j['slice']['schema']=2
 elif name=='wrong-counter':j['slice']['totalJvmSteps']+=1
 else:
  cp=d/'positive-q1/checkpoints'/(j['checkpointSHA256']+'.bin');b=bytearray(cp.read_bytes());b[-1]^=1;cp.write_bytes(b)
 p.write_text(json.dumps(j));report[name]=run(name,d,False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
