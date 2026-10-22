#!/usr/bin/env python3
"""Fresh parent typed-refusal and raw regex-class namespace controls."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-regex-build-parent-p42-fixed';G=ROOT/'build/java-diff-mc-regex-generated-parent-p42-fixed';O=ROOT/'build/java-diff-mc-regex-refusals-parent-p42-fixed';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,H/'ParentRegexRefusal.java',H/'ParentRegexMutationRefusal.java'])
manifest={'generatedOnly':True,'cases':{}};bundles=O/'bundles';bundles.mkdir()
def case(name,entry,files):
 d=bundles/name;d.mkdir();rs=[]
 for i,(binary,data)in enumerate(files):
  f=f'{i:03d}.class';(d/f).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':f,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 manifest['cases'][name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
for name in('ParentRegexRefusal','ParentRegexMutationRefusal'):
 files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];case(name,name,[(p.stem,p.read_bytes())for p in files])
engine=(B/'engine/MCEntryInterpreter.sol').read_text();root=(C/'ParentRegexRefusal.class').read_bytes()
for name in('Pattern','Matcher'):
 data=bytes.fromhex(re.search(r'function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',engine)[1]);case('raw-'+name,'ParentRegexRefusal',[('ParentRegexRefusal',root),('java/util/regex/'+name,data)])
(O/'fixture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
p=D/'evm_driver.go';s=p.read_text();s=s.replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1)
# Both declared unbound-refusal codes are recorded, never confused with Java PSE or a gas failure.
old='if detail.Name != expectedError || errorCode(detail) != expectedCode {';new='if detail.Name != expectedError || (expectedCode!="3or4" && errorCode(detail)!=expectedCode) || (expectedCode=="3or4" && errorCode(detail)!="3" && errorCode(detail)!="4") {';assert s.count(old)>=1;s=s.replace(old,new);p.write_text(s)
(D/'parent_refusals.go').write_text('''package main
import("path/filepath")
func(r *runner)parentRefusals()error{
 for _,c:=range []struct{name,fixture string}{{"valid-quantified-anchor","ParentRegexRefusal"},{"mutable-surrogate","ParentRegexMutationRefusal"}}{row,err:=r.runResumedRefusal(c.name,c.fixture,"CallError","3or4",7,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}
 for _,name:=range []string{"raw-Pattern","raw-Matcher"}{row,err:=r.runRejection(name,name,"BootstrapProfileError","1",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}
 r.report.Status="fresh parent regex valid-outofsubset/mutation raw refusal and namespace controls passed";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)
}
''')
run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
