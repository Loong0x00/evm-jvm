#!/usr/bin/env python3
"""Cold-array regression (including accepted-P59 counterexample) and real growth-OOM ordering."""
from pathlib import Path
import json,hashlib,os,subprocess,shutil,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-array-list-add-build-parent-p60-002';OLD=ROOT/'build/java-diff-mc-linked-map-put-build-parent-p59-002';G=ROOT/'build/java-diff-mc-array-list-add-generated-parent-p60-003';O=ROOT/'build/java-diff-mc-array-list-add-focused-parent-p60';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);return r
r=run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,H/'ParentColdArrayArguments.java',H/'ParentArrayListGrowOOM.java']);assert r['exit']==0;r=run('stock-cold',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',C,'ParentColdArrayArguments']);assert r['exit']==0;cases={}
for name in('ParentColdArrayArguments','ParentArrayListGrowOOM'):
 q=O/'bundles'/name;q.mkdir(parents=True);files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];rs=[]
 for i,p in enumerate(files):
  b=p.read_bytes();fn=f'{i:03d}.class';(q/fn).write_bytes(b);rs.append({'index':i,'binaryName':p.stem,'file':fn,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 cases[name]={'entryClass':name,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'quotaCaseNotStockHeapOracle':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text();needle='if mode == "parent-small" || mode == "parent-matrix" {';assert s.count(needle)==1;s=s.replace(needle,'if mode=="parent-cold"||mode=="parent-oom"||mode=="parent-baseline-cold"{if err=r.parentFocused(mode);err!=nil{os.Exit(writeFailure(r,err))};return}\n'+needle,1);p.write_text(s)
(D/'parent_focused.go').write_text('''package main
import("fmt";"path/filepath")
func(r *runner)parentFocused(mode string)error{
 if mode=="parent-baseline-cold"{row,w,err:=r.runSchedule("parent-baseline-cold-direct",65536,"ParentColdArrayArguments",true,true);if w!=nil{w.close()};if err!=nil{return err};r.report.Schedules=append(r.report.Schedules,row);bad,e:=r.runResumedRefusal("parent-baseline-cold-q1","ParentColdArrayArguments","ReferenceError","2",1,maxInternal);if e!=nil{return e};r.report.Controls=append(r.report.Controls,bad);r.report.Status="accepted P59 direct passes but cold covariant array argument after resume raw-refuses";return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)}
 fixture:="ParentColdArrayArguments";qs:=[]uint64{1,7,65536};if mode=="parent-oom"{fixture="ParentArrayListGrowOOM";qs=[]uint64{4096,65536}}
 var rows []scheduleReport
 for _,q:=range qs{row,w,err:=r.runSchedule(fmt.Sprintf("parent-%s-q%d",fixture,q),q,fixture,true,true);if w!=nil{w.close()};if err!=nil{return err};if err=r.parentFlatConfig(row,fixture);err!=nil{return err};rows=append(rows,row)}
 for i:=1;i<len(rows);i++{if rows[i].Final.MachineStateRoot!=rows[0].Final.MachineStateRoot||rows[i].Final.VfsStateRoot!=rows[0].Final.VfsStateRoot||rows[i].Final.TotalJvmSteps!=rows[0].Final.TotalJvmSteps||rows[i].Final.TotalInternalSteps!=rows[0].Final.TotalInternalSteps{return fmt.Errorf("focused roots/counters differ")}}
 r.report.Status="cold reference-array hierarchy and growth-OOM ordering genuine gates passed";r.report.Schedules=rows;return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)
}
''');r=run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);assert r['exit']==0
BD=O/'baseline-src';shutil.copytree(D,BD)
for p in BD.glob('*.go'):p.write_text(p.read_text().replace('MC-ARRAY-LIST-ADD-BOUNDED-1','MC-LINKED-HASH-MAP-PUT-P59-1'))
r=run('baseline-build',['go','build','-trimpath','-o',O/'baseline-driver','./'+str(BD.relative_to(ROOT))],600);assert r['exit']==0
args=[O/'baseline-driver','parent-baseline-cold',OLD/'engine/MCEntryInterpreter.json',OLD/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'parent-baseline-cold','1000000000'];r=run('baseline-cold',args);assert r['exit']==0
for mode in('parent-cold','parent-oom'):
 gas=1000000000
 for attempt in range(1,8):
  label=mode+f'-attempt-{attempt}';report=O/label;args=[O/'driver',mode,B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,report,str(gas)];r=run(label,args);r['gasBudget']=gas
  if r['exit']==0:
   rr=run(label+'-reopen',[args[0],'reopen',*args[2:]]);assert rr['exit']==0;break
  p=report/'gate-failure.json';assert p.exists()and json.load(open(p))['failure']['classification']=='test-only-gas-budget',r;gas*=2
 else:raise AssertionError('finite retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','initialGas':1000000000,'runs':rows,'actualGlobalArrayElementsQuotaNotChanged':262144,'baselineColdFailureReproducedBeforeAnyOriginalRun':True},indent=2)+'\n');print(json.dumps(rows,indent=2))
