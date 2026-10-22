#!/usr/bin/env python3
"""Fresh bounded-profile refusal/namespace and coordinator controls on P39 only."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-hash-map-put-build-parent-p39';G=ROOT/'build/java-diff-mc-hash-map-put-generated-parent-p39';F=ROOT/'build/java-diff-mc-hash-map-put-fixtures-parent-p39b';O=ROOT/'build/java-diff-mc-hash-map-put-controls-parent-p39';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir()
env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with (O/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
sources=[H/(n+'.java') for n in ('ParentMapPutTreeRefusal','ParentMapGetRefusal','ParentMapNoop')]
J='/usr/lib/jvm/java-8-openjdk/bin/';run('compile',[J+'javac','-g:none','-source','8','-target','8','-d',C,*sources])
for name in ('ParentMapPutTreeRefusal','ParentMapGetRefusal'):run('java8-'+name,[J+'java','-cp',C,name])
manifest={'cases':{},'generatedOnly':True,'oracleNeverExecutionInput':True};bundles=O/'bundles';bundles.mkdir()
def case(name,entry,files):
 d=bundles/name;d.mkdir();rs=[]
 for i,(binary,b) in enumerate(files):
  file=f'{i:03d}.class';(d/file).write_bytes(b);rs.append({'index':i,'binaryName':binary,'file':file,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 manifest['cases'][name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
for name in ('ParentMapPutTreeRefusal','ParentMapGetRefusal'):
 files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];case(name,name,[(p.stem,p.read_bytes())for p in files])
s=(B/'engine/MCEntryInterpreter.sol').read_text();root=(C/'ParentMapNoop.class').read_bytes()
for label,materializer,binary in [('raw-node','HashMapNode','java/util/HashMap$Node'),('raw-map','HashMap','java/util/HashMap')]:
 b=bytes.fromhex(re.search(r'function _bootstrap'+materializer+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',s)[1]);case(label,'ParentMapNoop',[('ParentMapNoop',root),(binary,b)])
# Reuse unchanged generated input BYTES, never checkpoints, from accepted P38 clone transport control.
old=ROOT/'build/java-diff-mc-string-replaceall-bounded-fixtures-parent-p38d';fm=json.load(open(old/'fixture-manifest.json'));fc=fm['cases']['raw-bytes-exact'];shutil.copytree(old/'bundles/raw-bytes-exact',bundles/'raw-bytes-exact');manifest['cases']['raw-bytes-exact']=fc
(O/'fixture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
p=D/'evm_driver.go';s=p.read_text();s=s.replace('if mode == "parent-small" || mode == "parent-resize" {','if mode == "parent-controls" {\n if err=r.parentControls();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-resize" {',1)
# Save only the last successful checkpoint for diagnostic heap proof, never failed output.
a='''return controlReport{Name: name,
				Expectation: "typed EVM refusal after successful checkpoints; prior running Head/root preserved",'''
b='''cpPath:=filepath.Join(r.reportDir,"successful-before-refusal-"+name+".bin")
            if err=os.WriteFile(cpPath,last.Checkpoint,0600);err!=nil{return controlReport{},err}
            return controlReport{Name: name,
                Expectation: "typed EVM refusal after successful checkpoints; prior running Head/root preserved",'''
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
p=D/'coordinator_route.go';s=p.read_text();s=re.sub(r'\b104\b','105',s);s=re.sub(r'\b254\b','255',s);s=s.replace('MC-STRING-REPLACEALL-BOUNDED-P38','MC-HASH-MAP-PUT-BOUNDED-P39');p.write_text(s)
(D/'parent_controls.go').write_text('''package main
import("path/filepath")
func(r *runner)parentControls()error{
 for _,c:=range []struct{name,fixture string}{{"tree","ParentMapPutTreeRefusal"},{"get","ParentMapGetRefusal"}}{
  row,err:=r.runResumedRefusal(c.name,c.fixture,"CallError","4",7,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)
 }
 for _,name:=range []string{"raw-node","raw-map"}{row,err:=r.runRejection(name,name,"BootstrapProfileError","1",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)}
 r.report.Mode="parent-controls";r.report.Status="fresh tree/get resumed atomic refusal and raw Node/HashMap namespace controls passed"
 return writeJSON(filepath.Join(r.reportDir,"parent-controls-summary.json"),r.report)
}
''')
run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600)
for mode in ('parent-controls','coordinator'):
 run(mode,[O/'driver',mode,B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/mode,'1000000000'])
(O/'summary.json').write_text(json.dumps({'status':'PASS','gas':1000000000,'generatedOnly':True,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
