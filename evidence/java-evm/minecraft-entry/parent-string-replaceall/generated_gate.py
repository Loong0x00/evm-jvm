#!/usr/bin/env python3
"""Fresh parent tests. Full matrix q65536/q4096 at16B; small q1/q7 at1B.
The worker full q1/q7 matrix is separately provenance-audited, not rerun here.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];T=H.parent/'pattern-compile-bootstrap/tools/string-replaceall-bounded'
build=ROOT/'build/java-diff-mc-string-replaceall-build-parent-p38'
fixtures=ROOT/'build/java-diff-mc-string-replaceall-bounded-fixtures-parent-p38d'
out=ROOT/'build/java-diff-mc-string-replaceall-generated-parent-p38d'
assert not out.exists();out.mkdir();(out/'driver-src').mkdir()
env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1')
def run(label,args,timeout=1200):
 t=time.monotonic()
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 row={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(out/(label+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==0,row
 return row
run('fixtures',[sys.executable,'-B',T/'generate_fixtures.py',fixtures],900)
manifest=json.load(open(fixtures/'fixture-manifest.json'))
run('small-compile',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',fixtures/'fixtures',H/'ParentReplaceAllSmall.java'])
run('small-java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',fixtures/'fixtures','ParentReplaceAllSmall'])
b=(fixtures/'fixtures/ParentReplaceAllSmall.class').read_bytes()
smallbundle=fixtures/'bundles/ParentReplaceAllSmall';smallbundle.mkdir();(smallbundle/'000-ParentReplaceAllSmall.class').write_bytes(b)
manifest['cases']['ParentReplaceAllSmall']={'entryClass':'ParentReplaceAllSmall','rawCount':1,'rawBytes':len(b),'rawClasses':[{'index':0,'binaryName':'ParentReplaceAllSmall','file':'000-ParentReplaceAllSmall.class','bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()}]}
(out/'fixture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
s=(T/'evm_driver.go').read_text();s=s.replace('if mode == "gate" {','if mode == "parent-large" || mode == "parent-small" {\n if err = r.parentGate(mode); err != nil { os.Exit(writeFailure(r,err)) }; return\n }\n if mode == "gate" {',1)
anchor='if len(entries) == 1 && stringReplaceAll != nil {'
assert s.count(anchor)==1
s=s.replace('if name == "q1-raw150" ||', 'if strings.HasPrefix(name, "parent-") || name == "q1-raw150" ||',1)
s=s.replace(anchor,'if strings.Contains(filepath.Base(r.reportDir), "parent-") {\n return writeJSON(filepath.Join(r.reportDir, "reopen-summary.json"), map[string]any{"status":"fresh-process parent checkpoint reopens passed", "reopenCount":len(rows), "reopens":rows})\n }\n '+anchor,1)
(out/'driver-src/evm_driver.go').write_text(s)
for p in T.glob('*.go'):
 if p.name!='evm_driver.go':shutil.copy2(p,out/'driver-src'/p.name)
(out/'driver-src/parent_gate.go').write_text('''package main
import("fmt";"path/filepath";"reflect")
func(r *runner)parentGate(mode string)error{
 var rows []scheduleReport
 fixture:="StringReplaceAllMatrix";quanta:=[]uint64{65536,4096}
 if mode=="parent-small"{fixture="ParentReplaceAllSmall";quanta=[]uint64{7,1}}
 for _,q:=range quanta{
 row,w,err:=r.runSchedule(fmt.Sprintf("parent-%s-q%d",fixture,q),q,fixture,true,true)
 if w!=nil{w.close()};if err!=nil{return err};rows=append(rows,row)
 }
 if rows[0].Final.MachineStateRoot!=rows[1].Final.MachineStateRoot || rows[0].Final.VfsStateRoot!=rows[1].Final.VfsStateRoot || rows[0].Final.TotalJvmSteps!=rows[1].Final.TotalJvmSteps || !reflect.DeepEqual(rows[0].HeapAudit,rows[1].HeapAudit){return fmt.Errorf("parent cross-quantum roots/counters/heap mismatch")}
 r.report.Schedules=rows;r.report.Status="fresh parent generated void schedules and exact cross-quantum roots/heap passed";r.report.Mode=mode
 return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)
}
''')
shutil.copy2(out/'driver-src/parent_gate.go',H/'parent_gate.go.txt')
run('driver-build',['go','build','-trimpath','-o',out/'driver','./'+str((out/'driver-src').relative_to(ROOT))],600)
rows=[]
for mode,gas,wall in [('parent-large',16000000000,1200),('parent-small',1000000000,1200),('replaceall-controls',16000000000,1200),('array-clone',1000000000,1200),('coordinator',1000000000,1200)]:
 report=out/mode
 args=[out/'driver',mode,build/'engine/MCEntryInterpreter.json',build/'coordinator/MCEntryCoordinator.json',out/'fixture-manifest.json',fixtures,report,str(gas)]
 rows.append(run(mode,args,wall))
 if mode in ('parent-large','parent-small','array-clone'):
  rows.append(run(mode+'-reopen',[args[0],'reopen',*args[2:]],wall))
(out/'summary.json').write_text(json.dumps({'status':'passed','freshParentRuns':rows,'fullWorkerQ1MatrixRerun':False,'largeMatrixGas':16000000000,'smallQ1Gas':1000000000},indent=2)+'\n')
print(json.dumps({'status':'passed','freshParentRuns':rows},indent=2))
