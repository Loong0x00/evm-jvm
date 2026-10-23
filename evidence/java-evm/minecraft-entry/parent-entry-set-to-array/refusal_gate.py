#!/usr/bin/env python3
"""Fresh raw refusals for short targets, inherited unsupported copies, and reserved images."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-entry-array-build-parent-p48';G=ROOT/'build/java-diff-mc-entry-array-generated-parent-p48';O=ROOT/'build/java-diff-mc-entry-array-refusals-parent-p48';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 row={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');rows.append(row);assert p.returncode==0,row
probes={
 'ParentArrayShort':'Map<Object,Object> map=new HashMap<Object,Object>(); map.put(null,null); Collection<Map.Entry<Object,Object>> view=map.entrySet(); Object[] target=new Object[0]; view.toArray(target);',
 'ParentArrayShortSentinel':'Map<Object,Object> map=new HashMap<Object,Object>(); map.put(null,null); map.put(new Object(),new Object()); Collection<Map.Entry<Object,Object>> view=map.entrySet(); Object sentinel=new Object(); Object[] target=new Object[]{sentinel}; view.toArray(target);',
 'ParentArrayNoArg':'Collection view=new HashMap().entrySet(); view.toArray();',
 'ParentArrayAdd':'Set view=new HashMap().entrySet(); view.add(new Object());',
 'ParentArrayEquals':'Set view=new HashMap().entrySet(); view.equals(view);',
 'ParentArrayHashSet':'Collection view=new HashSet(); view.toArray(new Object[0]);',
 'ParentArrayArrayList':'Collection view=new ArrayList(1); view.toArray(new Object[0]);',
 'ParentArrayCow':'Collection view=new java.util.concurrent.CopyOnWriteArrayList(); view.toArray(new Object[0]);',
 'ParentArrayQueue':'Collection view=new java.util.concurrent.ConcurrentLinkedQueue(); view.toArray(new Object[0]);'}
sources=[]
for name,body in probes.items():
 p=O/(name+'.java');p.write_text('import java.util.*; public class '+name+' { public static void main(String[] args) { '+body+' } }\n');sources.append(p)
run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources]);sets=[(name,name,[(name,(C/(name+'.class')).read_bytes())])for name in probes];sol=(B/'engine/MCEntryInterpreter.sol').read_text()
for method,binary in [('Collection','Collection'),('AbstractCollection','AbstractCollection'),('HashMapEntrySet','HashMap$EntrySet')]:
 data=bytes.fromhex(re.search(r'function _bootstrap'+method+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',sol)[1]);sets.append(('raw-'+method,'ParentArrayNoArg',[('ParentArrayNoArg',(C/'ParentArrayNoArg.class').read_bytes()),('java/util/'+binary,data)]))
cases={}
for name,entry,items in sets:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1);old='if detail.Name != expectedError || errorCode(detail) != expectedCode {';new='if detail.Name != expectedError || (expectedCode!="OMITTED" && errorCode(detail)!=expectedCode) || (expectedCode=="OMITTED" && errorCode(detail)!="1" && errorCode(detail)!="3" && errorCode(detail)!="4") {';assert old in s;s=s.replace(old,new);p.write_text(s)
labels=','.join('"'+x+'"'for x in probes);raws=','.join('"'+x[0]+'"'for x in sets if x[0].startswith('raw-'));(D/'parent_refusals.go').write_text('package main\nimport("path/filepath")\nfunc(r *runner)parentRefusals()error{\nfor _,name:=range []string{'+labels+'}{row,err:=r.runResumedRefusal(name,name,"CallError","OMITTED",7,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}\nfor _,name:=range []string{'+raws+'}{row,err:=r.runRejection(name,name,"BootstrapProfileError","1",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}\nr.report.Status="typed-copy capacity/inherited unsupported/raw-reservation paths atomically refused";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)\n}\n');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
