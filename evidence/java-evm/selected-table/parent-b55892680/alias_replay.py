#!/usr/bin/env python3
"""Dedicated loaded/unloaded method and handler isolation, using public EVM transport."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;proto=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'));src=out/'src';src.mkdir();classes=out/'classes';classes.mkdir()
for p in (here/'alias').glob('*.java'):
 if p.name=='Oracle.java':continue
 text=p.read_text()
 if p.name=='AliasChild.java':text=text.rstrip()[:-1]+''.join('\n public static int unused%d(int x){return x+%d;}'%(i,i) for i in range(32))+'\n}\n'
 (src/p.name).write_text(text)
jdk='/usr/lib/jvm/java-8-openjdk/bin/'
subprocess.run([jdk+'javac','-source','8','-target','8','-g:none','-d',str(classes)]+list(map(str,src.glob('*.java'))),env=env,check=True)
subprocess.run([jdk+'javac','-source','8','-target','8','-g:none','-cp',str(classes),'-d',str(out),str(here/'alias/Oracle.java')],env=env,check=True)
answers={str(m):subprocess.check_output([jdk+'java','-cp',str(classes)+':'+str(out),'Oracle',str(m)],env=env,text=True).strip() for m in (7,19,99)}
assert answers=={'7':'R:525','19':'R:561','99':'X:java.lang.RuntimeException'},answers
(out/'oracle.json').write_text(json.dumps(answers,indent=2)+'\n');names=['AliasRoot','AliasBase','AliasChild','AliasFace'];zp=out/'alias.zip'
with zipfile.ZipFile(zp,'w') as z:
 for n in names:
  i=zipfile.ZipInfo(n+'.class',(1980,1,1,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,(classes/(n+'.class')).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
reports={};pids=set();calls=0
def call(profile,label,args):
 path=out/(label+'.json')
 with path.open('w') as f,path.with_suffix('.stderr').open('w') as err:subprocess.run([str(proto/profile/'driver')]+list(map(str,args)),env=env,stdout=f,stderr=err,check=True,timeout=32)
 r=json.loads(path.read_text());assert r['pid'] not in pids;pids.add(r['pid']);return r
for profile in ('baseline','optimized'):
 for mode,q in [(7,4096),(7,7),(7,1),(19,4096),(99,7)]:
  label='%s-%d-q%d'%(profile,mode,q);w=out/label
  setup=call(profile,label+'-setup',['-command','setup','-dir',w,'-zip',zp,'-names',','.join(names)]);before=setup['head']['StateRoot'];rows=[];bodies=[]
  for n in range(1,1025):
   r=call(profile,label+'-%d'%n,['-command','slice','-dir',w,'-length',zp.stat().st_size,'-mode',mode,'-quantum',q]);calls+=1
   assert 'error' not in r,(label,n,r.get('error'),r.get('rawRevert'))
   sl=r['slice'];assert r['beforeRoot']==before and r['receiptRoot']==r['afterRoot']!=before;before=r['afterRoot']
   assert sl['Epoch']==n and sl['Schema']==1 and r['logs']==1 and 0<r['gas']<=100000000 and r['wallSeconds']<=30
   init=r['initialization'];assert not init['EngineInstalled'] and not init['AS0Creation']['Performed'] and init['AS0Creation']['GasUsed']==0
   cp=(w/'checkpoints'/(sl['CheckpointRoot'][2:]+'.checkpoint')).read_bytes();assert hashlib.sha256(cp).hexdigest()==r['checkpointSHA256'] and len(cp)<=1048576
   bodies.append(cp[280:]) # Exact opaque same-schema payload comparison, not Java interpretation.
   if profile=='optimized':
    tr=r['trace'];assert tr['enabled'] and len(tr['reads'])==4 and all(t['requested']==t['returned'] and t['success'] and 0<t['returned']<=4096 for t in tr['reads'])
   rows.append(r)
   if sl['Lifecycle']!=1:break
  else:raise AssertionError('alias finite progress')
  last=rows[-1];sl=last['slice']
  if mode==99:assert sl['Lifecycle']==3 and sl['JavaKind']==0 and sl['JavaRef']>0 and base64.b64decode(sl['JavaClass'])==b'java/lang/RuntimeException'
  else:assert sl['Lifecycle']==2 and sl['JavaKind']==0 and sl['Result']==(525 if mode==7 else 561)
  terminal=call(profile,label+'-terminal',['-command','terminal','-dir',w,'-length',zp.stat().st_size]);assert terminal['head']==last['head'] and terminal['checkpointSHA256']==last['checkpointSHA256']
  reports[(profile,mode,q)]={'rows':rows,'bodies':bodies}
for mode,q in [(7,4096),(7,7),(7,1),(19,4096),(99,7)]:
 a=reports[('baseline',mode,q)];b=reports[('optimized',mode,q)];assert a['bodies']==b['bodies'],(mode,q,'opaque payload mismatch')
 for x,y in zip(a['rows'],b['rows']):
  for k in ('Result','JavaKind','JavaRef','JavaClass','TotalJvmSteps','TotalInternalSteps','ExecutedJvmSteps','ExecutedInternalSteps','Lifecycle','VFSStateRoot'):assert x['slice'][k]==y['slice'][k],(mode,q,k)
for profile in ('baseline','optimized'):
 ref=reports[(profile,7,4096)]['rows'][-1]
 for q in (1,7):
  last=reports[(profile,7,q)]['rows'][-1]
  for k in ('MachineStateRoot','VFSStateRoot','Result','TotalJvmSteps','TotalInternalSteps'):assert last['slice'][k]==ref['slice'][k]
summary={'distinctProcesses':len(pids),'javaCalls':calls,'classBytes':sum(p.stat().st_size for p in classes.glob('*.class')),'oracle':answers,'cases':{str(k):{'slices':len(v['rows']),'maxGas':max(r['gas'] for r in v['rows']),'jvm':v['rows'][-1]['slice']['TotalJvmSteps'],'internal':v['rows'][-1]['slice']['TotalInternalSteps'],'opaquePayloadSHA256':hashlib.sha256(v['bodies'][-1]).hexdigest()} for k,v in reports.items()},'aliasCoverage':['32 unselected methods','distinct selected signatures/long args and result','clinit','constructors/super/private special','virtual/interface/default','separate repeated Arithmetic/NPE/Runtime handler caches','caught athrow','uncaught RuntimeException','String.equals native','fresh process restore']}
(out/'report.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
