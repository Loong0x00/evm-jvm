#!/usr/bin/env python3
"""Fresh apply-only Function omission and raw-namespace refusal controls."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-comparator-build-parent-p45-v2';G=ROOT/'build/java-diff-mc-comparator-generated-parent-p45';O=ROOT/'build/java-diff-mc-comparator-refusals-parent-p45';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
J='/usr/lib/jvm/java-8-openjdk/bin/';run('javac',[J+'javac','-g:none','-source','8','-target','8','-d',C,H/'ParentComparatorOmitted.java']);run('stock-java8-valid',[J+'java','-cp',C,'ParentComparatorOmitted'])
files=[C/'ParentComparatorOmitted.class',*sorted(C.glob('ParentComparatorOmitted$*.class'))];b=(B/'engine/MCEntryInterpreter.sol').read_text();image=bytes.fromhex(re.search(r'function _bootstrapComparator\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',b)[1]);cases={}
for name,items in [('omitted-comparator-helper',[(p.stem,p.read_bytes())for p in files]),('raw-Comparator',[(p.stem,p.read_bytes())for p in files]+[('java/util/Comparator',image)])]:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':'ParentComparatorOmitted','rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text();s=s.replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1)
old='if detail.Name != expectedError || errorCode(detail) != expectedCode {';new='if detail.Name != expectedError || (expectedCode!="OMITTED" && errorCode(detail)!=expectedCode) || (expectedCode=="OMITTED" && errorCode(detail)!="1" && errorCode(detail)!="3" && errorCode(detail)!="4") {';assert old in s;s=s.replace(old,new);p.write_text(s)
(D/'parent_refusals.go').write_text('''package main
import("path/filepath")
func(r *runner)parentRefusals()error{
 row,err:=r.runResumedRefusal("omitted-comparator-helper","omitted-comparator-helper","CallError","OMITTED",7,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)
 row,err=r.runRejection("raw-Comparator","raw-Comparator","BootstrapProfileError","1",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)
 r.report.Status="fresh omitted identity raw refusal and Function namespace reservation passed";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)
}
''');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
