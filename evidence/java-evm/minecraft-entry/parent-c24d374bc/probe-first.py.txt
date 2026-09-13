#!/usr/bin/env python3
"""Generated TEST-only public EVM controls. Ordinary gas; no failed-state recovery."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'properties-preflight';build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();mode=sys.argv[3]
assert mode in ('candidate','repaired') and not out.exists();out.mkdir();(out/'tmp').mkdir();(out/'classes').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
call('java8-compile',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-d',out/'classes',here/'OverrideProbe.java',src/'fixtures/PropertiesProbe.java',src/'fixtures/PropertiesConstructionProbe.java'])
for name in ('OverrideProbe','PropertiesProbe','PropertiesConstructionProbe'):call(name+'-java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',out/'classes',name])
spec=importlib.util.spec_from_file_location('diag',here/'checkpoint_frames.py');diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
summary={};labels=[]
probes=[('OverrideProbe',('OverrideProbe.class','OverrideProbe$VirtualDefaults.class'),(7,))] if mode=='candidate' else [('OverrideProbe',('OverrideProbe.class','OverrideProbe$VirtualDefaults.class'),(1,7,4096)),('PropertiesConstructionProbe',('PropertiesConstructionProbe.class',),(1,7,4096)),('PropertiesProbe',('PropertiesProbe.class',),(1,7,4096))]
for name,entries,quanta in probes:
 jar=out/(name+'.zip')
 with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
  for n in entries:
   i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(out/'classes'/n).read_bytes())
 env['MC_ENTRY_BINDINGS']=','.join(entries);reference=None
 for q in quanta:
  label=name+'-q'+str(q);w=out/label;rep=out/'reports'/label;args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',jar,q]
  call(label+'-start',[build/'driver','setup-chain',*args])
  if not (rep/'start-refusal.json').exists():
   call(label+'-finish',[build/'driver','finish',*args]);call(label+'-reopen',[build/'driver','verify',*args])
  h=json.loads((w/'durable-head.json').read_text());failures=[json.loads(p.read_text()) for p in rep.glob('*refusal.json')]
  row={'epoch':h['epoch'],'java':h['jvmSteps'],'internal':h['internalSteps'],'lifecycle':h['lifecycle'],'machineRoot':h['machineRoot'],'failures':failures}
  if failures:
   assert mode=='repaired' and name=='PropertiesProbe' and q==4096 and len(failures)==1
   f=failures[0];assert f['selector']=='0xf15d7343' and f['uint256Words']==['7'] and f['rootBefore']==f['rootAfter'] and h['epoch']==0
  else:
   cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256'];d=diag.inspect(cp);row['diagnostic']=d;row['opaqueSHA256']=hashlib.sha256(cp[280:]).hexdigest()
   if mode=='candidate':assert h['lifecycle']==h['outcome']==3 and h['javaKind']==3 # genuine guest ArithmeticException from failed counter assertion
   else:
    assert h['lifecycle']==h['outcome']==2
    if name=='OverrideProbe':
     v=next(x['staticValues'] for x in d['initialization'] if x['classIndex']==0);assert (int(v[-1]['packedValue'],16)&((1<<64)-1))==412
    if reference is None:reference=cp[280:]
    else:assert reference==cp[280:],'opaque terminal mismatch'
  summary[label]=row;labels.append(label);(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
call('verify-canonical',['node',here.parent/'parent-f780f1a13/verify_receipts.js',build,out,*labels])
print(json.dumps(summary,indent=2))
