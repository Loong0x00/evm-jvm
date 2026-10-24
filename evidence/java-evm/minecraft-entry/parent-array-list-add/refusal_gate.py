#!/usr/bin/env python3
"""Fresh unsupported ArrayList/Itr surfaces and incompatible array-argument guard controls."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-array-list-add-build-parent-p60-002';G=ROOT/'build/java-diff-mc-array-list-add-generated-parent-p60-003';O=ROOT/'build/java-diff-mc-array-list-add-refusals-parent-p60';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
probes={'Get':'list.get(0);','Set':'list.set(0,new Object());','RemoveIndex':'list.remove(0);','RemoveValue':'list.remove(value);','IndexedAdd':'list.add(0,value);','AddAll':'list.addAll(Collections.singletonList(value));','ListIterator':'list.listIterator();','NoArgArray':'list.toArray();','ShortArray':'list.toArray(new Object[0]);','Equals':'list.equals(list);','Hash':'list.hashCode();','Clone':'list.clone();','Clear':'list.clear();','IteratorRemove':'Iterator i=list.iterator();i.next();i.remove();'};sources=[]
for suffix,body in probes.items():
 name='ParentListRefusal'+suffix;p=O/(name+'.java');p.write_text('import java.util.*;public final class '+name+'{public static void main(String[]a){ArrayList list=new ArrayList();Object value=new Object();list.add(value);'+body+'}}\n');sources.append(p)
p=O/'ParentArrayArgumentMismatch.java';p.write_text('public final class ParentArrayArgumentMismatch{static void sink(Object[] a){}public static void main(String[]args){sink(new Object[1]);}}\n');sources.append(p);run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources]);sets=[];expect={}
for suffix in probes:
 name='ParentListRefusal'+suffix;sets.append((name,name,[(name,(C/(name+'.class')).read_bytes())]));expect[name]=('CallError','OMITTED')
data=(C/'ParentArrayArgumentMismatch.class').read_bytes();old=b'([Ljava/lang/Object;)V';new=b'([Ljava/lang/String;)V';assert data.count(old)==1;data=data.replace(len(old).to_bytes(2,'big')+old,len(new).to_bytes(2,'big')+new);sets.append(('array-type-mismatch','ParentArrayArgumentMismatch',[('ParentArrayArgumentMismatch',data)]));expect['array-type-mismatch']=('ReferenceError','2');sol=(B/'engine/MCEntryInterpreter.sol').read_text()
for method,binary in [('ArrayList','ArrayList'),('ArrayListItr','ArrayList$Itr')]:
 data=bytes.fromhex(re.search(r'function _bootstrap'+method+r'\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',sol)[1]);label='raw-'+method;sets.append((label,'ParentListRefusalGet',[('ParentListRefusalGet',(C/'ParentListRefusalGet.class').read_bytes()),('java/util/'+binary,data)]));expect[label]=('BootstrapProfileError','1')
cases={}
for name,entry,items in sets:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals"{if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return}\nif mode == "parent-small" || mode == "parent-matrix" {',1);old='if detail.Name != expectedError || errorCode(detail) != expectedCode {';new='if detail.Name != expectedError || (expectedCode!="OMITTED"&&errorCode(detail)!=expectedCode)||(expectedCode=="OMITTED"&&errorCode(detail)!="1"&&errorCode(detail)!="3"&&errorCode(detail)!="4") {';assert s.count(old)==1;s=s.replace(old,new);p.write_text(s);lines=[]
for name,(error,code)in expect.items():
 fn='runRejection'if name.startswith('raw-')else'runResumedRefusal';q='maxJvm'if name.startswith('raw-')else'1';lines.append('row,e=r.'+fn+'("'+name+'","'+name+'","'+error+'","'+code+'",'+q+',maxInternal);if e!=nil{return e};r.report.Controls=append(r.report.Controls,row)')
(D/'parent_refusals.go').write_text('package main\nimport("path/filepath")\nfunc(r *runner)parentRefusals()error{var row controlReport;var e error\n'+'\n'.join(lines)+'\nr.report.Status="unadmitted list/Itr surfaces and incompatible-array guard atomically refused";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)}\n');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
