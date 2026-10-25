#!/usr/bin/env python3
"""New LOCAL count150/151/160 and valid exact-byte cap/+1 boundary gates; generated-only."""
from pathlib import Path
import json,subprocess,os,shutil,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-raw160-build-parent-p62';F=ROOT/'build/java-diff-mc-raw160-fixtures-parent-p62';G=ROOT/'build/java-diff-mc-raw160-generated-parent-p62-002';O=ROOT/'build/java-diff-mc-raw160-boundaries-parent-p62-002';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');runs=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');runs.append(r);return r
manifest=json.load(open(F/'fixture-manifest.json'));P=O/'padding-oracle';P.mkdir();src=O/'PaddingOracle.java';src.write_text('public final class PaddingOracle {public static void main(String[]names)throws Exception{for(String n:names)Class.forName(n);}}\n');r=run('compile-padding-oracle',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',P,src]);assert r['exit']==0
for label in('bytes-exact','bytes-over'):
 Q=O/('oracle-'+label);Q.mkdir();names=[]
 for row in manifest['cases'][label]['rawClasses']:
  p=Q/(row['binaryName']+'.class');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((F/'bundles'/label/row['file']).read_bytes());names.append(row['binaryName'].replace('/','.'))
 r=run('stock-valid-padding-'+label,['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',str(Q)+os.pathsep+str(P),'PaddingOracle',*names]);assert r['exit']==0
p=D/'evm_driver.go';s=p.read_text();needle='if mode == "parent-small" || mode == "parent-matrix" {';assert s.count(needle)==1;s=s.replace(needle,'if mode=="parent-bound-counts"||mode=="parent-bound-bytes"||mode=="parent-bound-negative"{if err=r.parentBoundaries(mode);err!=nil{os.Exit(writeFailure(r,err))};return}\n'+needle,1);p.write_text(s)
(D/'parent_boundaries.go').write_text('''package main
import("fmt";"path/filepath")
func(r *runner)parentBoundaries(mode string)error{
 if mode=="parent-bound-negative"{for _,s:=range []struct{name,code,arg string}{{"raw161","1","161"},{"bytes-over","1","1063931"}}{row,e:=r.runRejection(s.name,s.name,"LinkError",s.code,65536,maxInternal);if e!=nil{return e};if len(row.ErrorArgs)<2||row.ErrorArgs[1]!=s.arg{return fmt.Errorf("boundary argument differs")};r.report.Controls=append(r.report.Controls,row)};r.report.Status="new161 and unchanged-byte-cap+1 atomically refused";return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)}
 fixtures:=[]string{"ParentRaw160Count150","ParentRaw160Count151"};if mode=="parent-bound-bytes"{fixtures=[]string{"bytes-exact"}}
 for _,f:=range fixtures{row,w,e:=r.runSchedule("parent-boundary-"+f,65536,f,true,true);if w!=nil{w.close()};if e!=nil{return e};if e=r.parentFlatConfig(row,"ParentRaw160");e!=nil{return e};r.report.Schedules=append(r.report.Schedules,row)}
 r.report.Status="positive raw counts and exact raw-byte cap passed";return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)
}
''');r=run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);assert r['exit']==0
for mode in('parent-bound-negative','parent-bound-counts','parent-bound-bytes'):
 gas=1000000000
 for attempt in range(1,8):
  name=mode+f'-attempt-{attempt}';report=O/name;args=[O/'driver',mode,B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',F/'fixture-manifest.json',F,report,str(gas)];r=run(name,args);r['gasBudget']=gas
  if r['exit']==0:
   if mode!='parent-bound-negative':rr=run(name+'-reopen',[args[0],'reopen',*args[2:]]);assert rr['exit']==0
   break
  p=report/'gate-failure.json';assert p.exists()and json.load(open(p))['failure']['classification']=='test-only-gas-budget',r;gas*=2
 else:raise AssertionError('finite boundary retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','initialGas':1000000000,'generatedPaddingClassfilesStockJava8Loadable':True,'runs':runs},indent=2)+'\n');print(json.dumps(runs,indent=2))
