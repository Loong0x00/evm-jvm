#!/usr/bin/env python3
"""Public Resume CAS and opaque-checkpoint tamper refusals followed by exact retry."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];proto=Path(sys.argv[1]).resolve();fixtures=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
s=(proto/'optimized/main.go').read_text();s=s.replace('func main() {','var negativeTest string\nfunc main() {\nflag.StringVar(&negativeTest,"negative","","test-only public Resume tamper")',1)
a='r, e = s.Resume(h.Coordinator.PackageRoot, h.Java.Epoch, h.Java.CheckpointRoot, cp, q, 4096, gas)'
b='''ep,rr:=h.Java.Epoch,h.Java.CheckpointRoot
 switch negativeTest {case "epoch":ep--;case "root":rr[0]^=1;case "checkpoint":cp[len(cp)-1]^=1;case "package":h.Coordinator.PackageRoot[0]^=1;case "":default:panic("unknown negative")}
 r,e=s.Resume(h.Coordinator.PackageRoot,ep,rr,cp,q,4096,gas)'''
assert s.count(a)==1;s=s.replace(a,b);p=out/'main.go';p.write_text(s);exe=out/'driver';subprocess.run(['gofmt','-w',str(p)],check=True);subprocess.run(['go','build','-trimpath','-o',str(exe),str(p)],cwd=root,env=env,check=True)
zp=fixtures/'zips/big-method-rich.zip';w=out/'world'
def call(label,args):
 with (out/(label+'.json')).open('w') as f,(out/(label+'.stderr')).open('w') as err:subprocess.run([str(exe),'-dir',str(w)]+list(map(str,args)),env=env,stdout=f,stderr=err,check=True,timeout=120 if label=='setup' else 32)
 return json.loads((out/(label+'.json')).read_text())
call('setup',['-command','setup','-zip',zp,'-names','BigCaller,BigEntry']);first=call('first',['-command','slice','-length',zp.stat().st_size,'-quantum',1]);assert 'error' not in first and first['slice']['Lifecycle']==1
cp=(w/'checkpoints'/(first['slice']['CheckpointRoot'][2:]+'.checkpoint'));before=cp.read_bytes();report={}
for kind in ('epoch','root','checkpoint','package'):
 r=call(kind,['-command','slice','-length',zp.stat().st_size,'-quantum',7,'-negative',kind])
 assert 'error' in r and r['slice']['Schema']==0 and r['head']==first['head'] and r['beforeRoot']==r['afterRoot']==first['afterRoot']
 assert r['logs']==0 and r['checkpointBytes']==0 and r['rawRevert']!='0x' and 0<r['gas']<=100000000
 assert cp.read_bytes()==before
 report[kind]={'gas':r['gas'],'revert':r['rawRevert'],'error':r['error']}
for n in range(1,9):
 r=call('retry'+str(n),['-command','slice','-length',zp.stat().st_size,'-quantum',7]);assert 'error' not in r
 if r['slice']['Lifecycle']!=1:break
assert r['slice']['Lifecycle']==2 and r['slice']['Result']==15 and r['slice']['TotalJvmSteps']==11
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
