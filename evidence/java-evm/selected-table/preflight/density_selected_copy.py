#!/usr/bin/env python3
"""Opaque selected-table density gate; uses generated Java8 fixtures only."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[4];proto=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
src=out/'src';src.mkdir();classes=out/'classes';classes.mkdir()
big=(root/'evidence/java-evm/capacity-baseline/preflight/fixtures/BigEntry.java').read_text();(src/'BigEntry.java').write_text(big);(src/'BigTwin.java').write_text(big.replace('BigEntry','BigTwin'))
(src/'BigPair.java').write_text('public class BigPair { public static int run(int x) { return BigEntry.use(x) + BigTwin.use(x) + 7; } }\n')
jdk='/usr/lib/jvm/java-8-openjdk/bin/'
subprocess.run([jdk+'javac','-source','8','-target','8','-g:none','-d',str(classes)]+list(map(str,src.glob('*.java'))),env=env,check=True)
(out/'Oracle.java').write_text('public class Oracle { public static void main(String[] a) { System.out.println(BigPair.run(7)); } }\n')
subprocess.run([jdk+'javac','-source','8','-target','8','-g:none','-cp',str(classes),'-d',str(out),str(out/'Oracle.java')],env=env,check=True)
oracle=subprocess.check_output([jdk+'java','-cp',str(classes)+':'+str(out),'Oracle'],env=env,text=True);assert oracle=='23\n';(out/'oracle.log').write_text(oracle)
names=['BigPair','BigEntry','BigTwin'];zp=out/'density.zip'
with zipfile.ZipFile(zp,'w') as z:
 for n in names:
  i=zipfile.ZipInfo(n+'.class',(1980,1,1,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,(classes/(n+'.class')).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
files={n:{'bytes':(classes/(n+'.class')).stat().st_size,'sha256':hashlib.sha256((classes/(n+'.class')).read_bytes()).hexdigest()} for n in names};total=sum(v['bytes'] for v in files.values());assert 131072<total<=262144
exe=proto/'optimized/driver';world=out/'world'
def call(name,args,timeout):
 with (out/(name+'.json')).open('w') as f,(out/(name+'.stderr')).open('w') as err:subprocess.run([str(exe)]+list(map(str,args)),stdout=f,stderr=err,env=env,check=True,timeout=timeout)
 return json.loads((out/(name+'.json')).read_text())
setup=call('setup',['-command','setup','-dir',world,'-zip',zp,'-names',','.join(names)],120)
ordinary=call('ordinary',['-command','slice','-dir',world,'-length',zp.stat().st_size,'-mode',7,'-gas',100000000],32)
report={'classes':files,'aggregate':total,'oracle':23,'ordinary':ordinary,'boundary':None}
if 'error' in ordinary:
 assert ordinary['beforeRoot']==ordinary['afterRoot']==setup['head']['StateRoot'] and ordinary['slice']['Schema']==0 and ordinary['checkpointBytes']==0
 # Explicitly authorized BOUNDARY observation AFTER retaining the failed ordinary
 # receipt; never ordinary rescue/acceptance. Same unchanged binding/old root.
 boundary=call('boundary-1B',['-command','slice','-dir',world,'-length',zp.stat().st_size,'-mode',7,'-gas',1000000000],122);report['boundary']=boundary
 last=boundary
else:last=ordinary
if 'error' not in last:
 assert last['slice']['Lifecycle']==2 and last['slice']['Result']==23
 report['terminal']=call('terminal',['-command','terminal','-dir',world,'-length',zp.stat().st_size],32)
report['ordinarySliced']={}
for q in (7,1):
 w=out/('world-q'+str(q));setupq=call('q%d-setup'%q,['-command','setup','-dir',w,'-zip',zp,'-names',','.join(names)],120)
 assert setupq['head']['StateRoot']==setup['head']['StateRoot']
 rows=[]
 for n in range(1,65):
  r=call('q%d-%d'%(q,n),['-command','slice','-dir',w,'-length',zp.stat().st_size,'-mode',7,'-quantum',q,'-gas',100000000],32);rows.append(r)
  if 'error' in r or r['slice']['Lifecycle']!=1:break
 else:raise AssertionError('density sliced bound')
 report['ordinarySliced'][str(q)]=rows
 if 'error' in rows[-1] and rows[-1]['head']['Java']['Epoch']>0:
  prior=call('q%d-pending-after-refusal'%q,['-command','terminal','-dir',w,'-length',zp.stat().st_size],32)
  retry=call('q%d-ordinary-retry'%q,['-command','slice','-dir',w,'-length',zp.stat().st_size,'-mode',7,'-quantum',q,'-gas',100000000],32)
  assert retry.get('error')==rows[-1].get('error') and retry['gas']==rows[-1]['gas'] and retry['head']==rows[-1]['head']
  assert prior['head']['Java']['CheckpointRoot']==rows[-2]['slice']['CheckpointRoot']
  resumed=call('q%d-boundary-resume-1B'%q,['-command','slice','-dir',w,'-length',zp.stat().st_size,'-mode',7,'-quantum',4096,'-gas',1000000000],122)
  assert 'error' not in resumed and resumed['slice']['Result']==23 and resumed['slice']['Lifecycle']==2
  for k in ('MachineStateRoot','VFSStateRoot','Result','TotalJvmSteps','TotalInternalSteps'):assert resumed['slice'][k]==last['slice'][k]
  report['ordinarySliced'][str(q)+'pending']=prior;report['ordinarySliced'][str(q)+'retry']=retry;report['ordinarySliced'][str(q)+'boundaryResume']=resumed
  report['ordinarySliced'][str(q)+'boundaryTerminal']=call('q%d-boundary-terminal'%q,['-command','terminal','-dir',w,'-length',zp.stat().st_size],32)
 if 'error' not in rows[-1]:
  assert rows[-1]['slice']['Result']==23 and rows[-1]['slice']['Lifecycle']==2
  if 'error' not in last:
   for k in ('MachineStateRoot','VFSStateRoot','Result','TotalJvmSteps','TotalInternalSteps'):assert rows[-1]['slice'][k]==last['slice'][k],k
  report['ordinarySliced'][str(q)+'terminal']=call('q%d-terminal'%q,['-command','terminal','-dir',w,'-length',zp.stat().st_size],32)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'aggregate':total,'ordinaryGas':ordinary['gas'],'ordinaryError':ordinary.get('error'),'boundaryGas':report['boundary']['gas'] if report['boundary'] else None,'successfulLastResult':last['slice']['Result'] if 'error' not in last else None,'ordinarySliced':{str(q):{'calls':len(report['ordinarySliced'][str(q)]),'lastError':report['ordinarySliced'][str(q)][-1].get('error'),'lastEpoch':report['ordinarySliced'][str(q)][-1]['head']['Java']['Epoch']} for q in (7,1)}},indent=2))
