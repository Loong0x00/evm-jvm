#!/usr/bin/env python3
"""Fresh typed omissions and both reserved raw Set-hierarchy names."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-entry-set-build-parent-p47-v2';G=ROOT/'build/java-diff-mc-entry-set-generated-parent-p47-v2';O=ROOT/'build/java-diff-mc-entry-set-refusals-parent-p47-v2';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
roots=[]
for name,body in [('ParentEntrySetEquals','view.equals(view);'),('ParentEntrySetRawAdd','((java.util.Set)view).add(new Object());'),('ParentEntrySetClear','view.clear();'),('ParentEntryIteratorRemove','view.iterator().remove();')]:
 p=O/(name+'.java');p.write_text('import java.util.*; public class '+name+' { public static void main(String[] args) { Set<Map.Entry<Object,Object>> view = new HashMap<Object,Object>().entrySet(); '+body+' } }\n');roots.append(p)
run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*roots])
source=(B/'engine/MCEntryInterpreter.sol').read_text();sets=[]
for name in('ParentEntrySetEquals','ParentEntrySetRawAdd','ParentEntrySetClear','ParentEntryIteratorRemove'):sets.append((name,[(name,(C/(name+'.class')).read_bytes())]))
for method,binary in [('HashMap','HashMap'),('HashMapEntrySet','HashMap$EntrySet'),('HashMapEntryIterator','HashMap$EntryIterator'),('ConcurrentModificationException','ConcurrentModificationException')]:
 data=bytes.fromhex(re.search(r'function _bootstrap'+method+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',source)[1]);sets.append(('raw-'+binary,[('ParentEntrySetEquals',(C/'ParentEntrySetEquals.class').read_bytes()),('java/util/'+binary,data)]))
cases={}
for name,items in sets:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':('ParentEntrySetEquals'if name.startswith('raw-')else name),'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text();s=s.replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1);old='if detail.Name != expectedError || errorCode(detail) != expectedCode {';new='if detail.Name != expectedError || (expectedCode!="OMITTED" && errorCode(detail)!=expectedCode) || (expectedCode=="OMITTED" && errorCode(detail)!="1" && errorCode(detail)!="3" && errorCode(detail)!="4") {';assert old in s;s=s.replace(old,new);p.write_text(s)
(D/'parent_refusals.go').write_text('package main\nimport("path/filepath")\nfunc(r *runner)parentRefusals()error{\n for _,name:=range []string{"ParentEntrySetEquals","ParentEntrySetRawAdd","ParentEntrySetClear","ParentEntryIteratorRemove"}{row,err:=r.runResumedRefusal(name,name,"CallError","OMITTED",7,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}\n for _,name:=range []string{"raw-HashMap","raw-HashMap$EntrySet","raw-HashMap$EntryIterator","raw-ConcurrentModificationException"}{row,err:=r.runRejection(name,name,"BootstrapProfileError","1",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}\n r.report.Status="unimplemented entry view APIs and all reserved raw names atomically refused";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)\n}\n');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
