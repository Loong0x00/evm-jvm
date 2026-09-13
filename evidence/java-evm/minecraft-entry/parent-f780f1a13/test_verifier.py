#!/usr/bin/env python3
"""Negative TEST copies of generated public receipts, never execution inputs."""
from pathlib import Path
import copy,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();source=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
m=json.loads((source/'q4096/durable-head.json').read_text());name='slice-00000000000000000001.json';receipt=json.loads((source/'reports/q4096'/name).read_text());raw=(source/'q4096/checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes()
results=[]
for case in ('control','outer-ABI','event-data','checkpoint','counter','engine-pin','head-lifecycle'):
 b=out/case;d=b/'q4096';r=b/'reports/q4096';(d/'checkpoints').mkdir(parents=True);r.mkdir(parents=True)
 head=copy.deepcopy(m);v=copy.deepcopy(receipt);cp=raw
 if case=='outer-ABI':v['outerABI']=v['outerABI'][:-2]+'01'
 elif case=='event-data':v['nestedLogs'][0]['data']='0x00'+v['nestedLogs'][0]['data'][4:]
 elif case=='checkpoint':cp=bytes([raw[0]^1])+raw[1:]
 elif case=='counter':v['slice']['executedJvmSteps']-=1
 elif case=='engine-pin':head['engineCodeHash']='0x'+'00'*32
 elif case=='head-lifecycle':head['lifecycle']=1
 (d/'durable-head.json').write_text(json.dumps(head));(r/name).write_text(json.dumps(v));(d/'checkpoints'/(m['checkpointSHA256']+'.bin')).write_bytes(cp)
 with (out/(case+'.log')).open('w') as f:p=subprocess.run(['node',str(here/'verify_receipts.js'),str(build),str(b),'q4096'],env=env,stdout=f,stderr=subprocess.STDOUT)
 assert (p.returncode==0)==(case=='control'),case;results.append({'case':case,'exit':p.returncode})
(out/'summary.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
