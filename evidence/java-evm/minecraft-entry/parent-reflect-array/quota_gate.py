#!/usr/bin/env python3
"""Generated reflection max-length/elements quota and retained EnumSet controls."""
from pathlib import Path
import json,hashlib,os,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-reflect-array-build-parent-p53-v2';O=ROOT/'build/java-diff-mc-reflect-array-quota-parent-p53';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();D=O/'driver-src';shutil.copytree(ROOT/'build/java-diff-mc-reflect-array-generated-parent-p53/driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);return r
body={
 'ParentReflectMax':'Object[] a=(Object[])java.lang.reflect.Array.newInstance(Object.class,65536); if(a.length!=65536||a[0]!=null||a[65535]!=null)throw new ArithmeticException();',
 'ParentReflectOver':'try{java.lang.reflect.Array.newInstance(Object.class,65537);throw new ArithmeticException();}catch(OutOfMemoryError expected){}',
 'ParentReflectElements':'Object[] a=(Object[])java.lang.reflect.Array.newInstance(Object.class,65536); Object[] b=(Object[])java.lang.reflect.Array.newInstance(Object.class,65536); Object[] c=(Object[])java.lang.reflect.Array.newInstance(Object.class,65536); if(a==b||b==c||c[65535]!=null)throw new ArithmeticException();try{java.lang.reflect.Array.newInstance(Object.class,65536);throw new ArithmeticException();}catch(OutOfMemoryError expected){}',
 'ParentReflectEnum':'E value=E.A; java.util.EnumSet set=java.util.EnumSet.allOf(E.class); if(set.size()!=2)throw new ArithmeticException(); E[] a=(E[])java.lang.reflect.Array.newInstance(E.class,2); a[0]=value; if(a[1]!=null||a[0]!=value)throw new ArithmeticException();'}
sources=[]
for name,code in body.items():
 p=O/(name+'.java');extra='enum E{A,B}'if name=='ParentReflectEnum'else'';p.write_text('public class '+name+'{'+extra+' public static void main(String[] args){'+code+'}}\n');sources.append(p)
assert run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources])['exit']==0
for name in('ParentReflectMax','ParentReflectEnum'):assert run('stock-'+name,['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',C,name])['exit']==0
cases={}
for name in body:
 files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,p in enumerate(files):
  data=p.read_bytes();fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':p.stem,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':name,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'quotaErrorsAreProfileNotStockJavaHeapLimits':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if len(entries) != 1 && len(entries) != 2 && len(entries) != 3 {','if len(entries) != 8 {').replace('expected one clone or up to three retained/P38 reopen requests','expected exactly eight parent reflection quota reopen requests');a='if mode == "parent-small" || mode == "parent-matrix" {';assert a in s;p.write_text(s.replace(a,'if mode == "parent-quota" {if err=r.parentQuota();err!=nil{os.Exit(writeFailure(r,err))};return}\n '+a,1));(D/'parent_quota.go').write_text('''package main
import("fmt";"path/filepath";"reflect")
func(r *runner)parentQuota()error{var rows []scheduleReport
for _,fixture:=range []string{"ParentReflectMax","ParentReflectOver","ParentReflectElements","ParentReflectEnum"}{var pair []scheduleReport
for _,q:=range []uint64{4096,65536}{row,w,err:=r.runSchedule(fmt.Sprintf("parent-%s-q%d",fixture,q),q,fixture,true,true);if w!=nil{w.close()};if err!=nil{return err};pair=append(pair,row);rows=append(rows,row)}
if pair[0].Final.MachineStateRoot!=pair[1].Final.MachineStateRoot||pair[0].Final.VfsStateRoot!=pair[1].Final.VfsStateRoot||pair[0].Final.TotalJvmSteps!=pair[1].Final.TotalJvmSteps||!reflect.DeepEqual(pair[0].HeapAudit,pair[1].HeapAudit){return fmt.Errorf("quota schedules diverged")}}
r.report.Schedules=rows;r.report.Status="fresh reflection quotas and retained EnumSet passed";return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)}
''');assert run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600)['exit']==0
for attempt in range(1,7):
 gas=1000000000*2**(attempt-1);report=O/f'parent-quota-attempt-{attempt}';args=[O/'driver','parent-quota',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,report,str(gas)];r=run(f'attempt-{attempt}',args);r['gasBudget']=gas
 if r['exit']==0:
  assert run('reopen',[args[0],'reopen',*args[2:]])['exit']==0;break
 assert json.load(open(report/'gate-failure.json'))['failure']['classification']=='test-only-gas-budget'
else:raise AssertionError('finite quota budget retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','successfulBudget':gas,'successfulAttempt':attempt,'noResourceCapChanges':True,'runs':rows},indent=2)+'\n');print((O/'summary.json').read_text())
