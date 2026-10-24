#!/usr/bin/env python3
"""Fresh corrected-engine callback/exception/collision/order-growth gates; no original inputs."""
from pathlib import Path
import json,hashlib,os,subprocess,shutil,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-linked-map-put-build-parent-p59-002';G=ROOT/'build/java-diff-mc-linked-map-put-generated-parent-p59';O=ROOT/'build/java-diff-mc-linked-map-put-focused-parent-p59';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);return r
src=H.parent/'linked-hash-map-put-bounded/tests/src';sources=[src/'PutProbe.java',src/'CallbackExceptionProbe.java',src/'CollisionRefusalProbe.java',src/'CollisionEightProbe.java',H/'ParentCallbackSideeffects.java'];r=run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources]);assert r['exit']==0
spec={'CallbackExceptionProbe':['CallbackExceptionProbe','HashThrowKey','ExistingKey','EqualsThrowKey'],'ParentCallbackSideeffects':['ParentCallbackSideeffects',*[p.stem for p in sorted(C.glob('ParentCallbackSideeffects$*.class'))]],'PutProbe':['PutProbe','ProbeKey'],'CollisionEightProbe':['CollisionEightProbe','CollisionKey']};cases={}
for name,classes in spec.items():
 r=run('stock-'+name,['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',C,name]);assert r['exit']==0
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,binary in enumerate(classes):
  b=(C/(binary+'.class')).read_bytes();fn=f'{i:03d}.class';(q/fn).write_bytes(b);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 cases[name]={'entryClass':name,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text();needle='if mode == "parent-small" || mode == "parent-matrix" {';assert s.count(needle)==1;s=s.replace(needle,'if strings.HasPrefix(mode,"parent-case-"){if err=r.parentSuite(strings.TrimPrefix(mode,"parent-case-"));err!=nil{os.Exit(writeFailure(r,err))};return}\n'+needle,1);p.write_text(s)
(D/'parent_suite.go').write_text('''package main
import("fmt";"path/filepath";"reflect")
func(r *runner)parentSuite(fixture string)error{
 qs:=[]uint64{1,7};if fixture=="PutProbe"||fixture=="CollisionEightProbe"{qs=[]uint64{4096,65536}}
 var rows []scheduleReport
 for _,q:=range qs{row,w,err:=r.runSchedule(fmt.Sprintf("parent-%s-q%d",fixture,q),q,fixture,true,true);if w!=nil{w.close()};if err!=nil{return err};if err=r.parentFlatConfig(row,fixture);err!=nil{return err};rows=append(rows,row)}
 if rows[0].Final.MachineStateRoot!=rows[1].Final.MachineStateRoot||rows[0].Final.VfsStateRoot!=rows[1].Final.VfsStateRoot||rows[0].Final.TotalJvmSteps!=rows[1].Final.TotalJvmSteps||rows[0].Final.TotalInternalSteps!=rows[1].Final.TotalInternalSteps||!reflect.DeepEqual(rows[0].HeapAudit,rows[1].HeapAudit){return fmt.Errorf("focused roots/counters/heap differ")}
 r.report.Status="fresh corrected-engine callbacks/order/collision gates passed";r.report.Schedules=rows;return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)
}
''');r=run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);assert r['exit']==0
for name in spec:
 gas=1000000000
 for attempt in range(1,7):
  label='parent-case-'+name+f'-attempt-{attempt}';report=O/label;args=[O/'driver','parent-case-'+name,B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,report,str(gas)];r=run(label,args);r['gasBudget']=gas
  if r['exit']==0:
   rr=run(label+'-reopen',[args[0],'reopen',*args[2:]]);assert rr['exit']==0;break
  p=report/'gate-failure.json';assert p.exists()and json.load(open(p))['failure']['classification']=='test-only-gas-budget',r;gas*=2
 else:raise AssertionError('finite retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','initialGas':1000000000,'runs':rows,'workerFixturesReexecutedUnderParentCorrectedEngine':True,'parentCallbackSideeffectFixture':True},indent=2)+'\n');print(json.dumps(rows,indent=2))
