#!/usr/bin/env python3
"""Parent-only dependency selection from actual canonical EVM missing-class errors.
Every added same-JAR binding starts a NEW world. No Java/ZIP/class evaluation,
failed-state reuse, host catalogue, platform stubs or quota changes.
"""
from pathlib import Path
import json,os,re,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3]
out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
execution=root/'build/java-diff-mc-classcount-parent-gate-6748eb593/original-execution'
jar=Path('/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar')
old=root/'build/java-diff-mc-classcount-parent-official19-6748eb593'
names=json.loads((here/'official19-bindings.json').read_text());env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'));rows=[]
for count in range(20,25):
 f=old/'reports/official/resume-refusal.json'
 if not f.exists():break
 r=json.loads(f.read_text());d=r.get('diagnostic')
 if r.get('selector')!='0x555db429' or not d:break
 name=d['name']
 if not re.fullmatch(r'org/apache/logging/log4j/[A-Za-z0-9_$/]+',name):break
 if d['site'] not in ('4098','4103','4104','4107','4108'):break
 entry=name+'.class';assert entry not in names;names.append(entry);assert len(names)==count<=24
 nf=out/('official%d-bindings.json'%count);nf.write_text(json.dumps(names,indent=2)+'\n')
 new=root/'build'/('java-diff-mc-classcount-parent-official%d-6748eb593'%count)
 args=[sys.executable,str(here/'frontier.py'),str(execution),str(new),str(jar),str(nf),'7']
 with (out/('official%d.log'%count)).open('w') as log:
  p=subprocess.Popen(args,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT);rc=p.wait()
 (out/('official%d-process.json'%count)).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':args})+'\n')
 assert rc==0,(count,'preserve actual failure; no fallback')
 h=json.loads((new/'official/durable-head.json').read_text())
 if h['epoch']:
  with (out/('official%d-verified.json'%count)).open('w') as log:subprocess.run(['node',str(here.parent/'parent-f780f1a13/verify_receipts.js'),str(execution),str(new),'official'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 rows.append({'bindingCount':count,'addedFromEVMError':d,'world':str(new),'epoch':h['epoch'],'java':h['jvmSteps'],'lifecycle':h['lifecycle']});(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[-1]),flush=True);old=new
 if h['lifecycle']!=1:break
print('Stopped at next actual unsupported diagnostic, terminal outcome, or existing24-count bound. No Done inference.',flush=True)
