#!/usr/bin/env python3
"""Fresh parent HashMap tests, finite explicit budgets; no original input.
Small q7/q1 and larger q4096/q65536 use different fixtures. Reopen is a new process.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];T=H.parent/'pattern-compile-bootstrap/tools/string-replaceall-bounded'
B=Path(sys.argv[1]).resolve();F=Path(sys.argv[2]).resolve();O=Path(sys.argv[3]).resolve()
assert B.parent==F.parent==O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-arraylist-iterator-generated-parent-') and not O.exists();O.mkdir();D=O/'driver-src';D.mkdir()
env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');rows=[]
def run(label,args,timeout=1200):
 start=time.monotonic();timed=False
 try:
  with (O/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  rc=p.returncode
 except subprocess.TimeoutExpired:rc=-1;timed=True
 row={'label':label,'exit':rc,'timedOut':timed,'wallSeconds':time.monotonic()-start,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');return row
s=(T/'evm_driver.go').read_text();s=re.sub(r'\b104\b','116',s);s=re.sub(r'\b254\b','266',s);s=s.replace('expected104','expected116').replace('raw+104','raw+116').replace('MC-STRING-REPLACEALL-BOUNDED-P38','MC-ARRAYLIST-ITERATOR-BOUNDED-1')
s=re.sub(r'\b105\b','116',s);s=re.sub(r'\b255\b','266',s);s=s.replace('expected105','expected116').replace('raw+105','raw+116')
s=s.replace('len(cp) > 1048576','len(cp) > 2097152')
old='''if !bytes.Equal(value[0:23], make([]byte, 23)) || value[23] != 1 ||
				binary.BigEndian.Uint64(value[24:32]) != 0 {
				return out, fmt.Errorf("HashMap handle %d primitive field[%d] was not Java int zero", o.handle, fieldIndex)
			}'''
new='''if !bytes.Equal(value[0:23], make([]byte, 23)) || value[23] != 1 {
                return out, fmt.Errorf("HashMap handle %d primitive field[%d] not a Java int",o.handle,fieldIndex)
            }'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('if mode == "gate" {','if mode == "parent-small" || mode == "parent-matrix" {\n if err=r.parentGate(mode);err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "gate" {',1)
s=s.replace('if name == "q1-raw150" ||','if strings.HasPrefix(name,"parent-") || name == "q1-raw150" ||',1)
a='if len(entries) == 1 && stringReplaceAll != nil {';assert s.count(a)==1;s=s.replace(a,'if strings.Contains(filepath.Base(r.reportDir),"parent-") {\n return writeJSON(filepath.Join(r.reportDir,"reopen-summary.json"),map[string]any{"status":"fresh-process parent checkpoint reopens passed","reopenCount":len(rows),"reopens":rows})\n }\n '+a,1)
(D/'evm_driver.go').write_text(s)
for p in T.glob('*.go'):
 if p.name!='evm_driver.go':
  extra=p.read_text().replace('MC-STRING-REPLACEALL-BOUNDED-P38','MC-ARRAYLIST-ITERATOR-BOUNDED-1');extra=re.sub(r'\b104\b','116',extra);extra=re.sub(r'\b254\b','266',extra);(D/p.name).write_text(extra)
(D/'parent_gate.go').write_text('''package main
import("fmt";"path/filepath";"reflect")
func(r *runner)parentGate(mode string)error{
 fixture:="ParentArrayListIterator";quanta:=[]uint64{7,1}
 if mode=="parent-matrix"{fixture="ParentArrayListIteratorWide";quanta=[]uint64{4096,65536}}
 var rows []scheduleReport
 for _,q:=range quanta{
  row,w,err:=r.runSchedule(fmt.Sprintf("parent-%s-q%d",fixture,q),q,fixture,true,true)
  if w!=nil{w.close()};if err!=nil{return err};rows=append(rows,row)
 }
 if rows[0].Final.MachineStateRoot!=rows[1].Final.MachineStateRoot||rows[0].Final.VfsStateRoot!=rows[1].Final.VfsStateRoot||rows[0].Final.TotalJvmSteps!=rows[1].Final.TotalJvmSteps||rows[0].Final.TotalInternalSteps!=rows[1].Final.TotalInternalSteps||!reflect.DeepEqual(rows[0].HeapAudit,rows[1].HeapAudit){return fmt.Errorf("parent roots/counters/heap differ across quantum")}
 r.report.Mode=mode;r.report.Status="fresh parent genuine void schedules and exact roots/counters/heap passed";r.report.Schedules=rows
 return writeJSON(filepath.Join(r.reportDir,"parent-summary.json"),r.report)
}
''')
row=run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);assert row['exit']==0,row
# Every retry has a fresh report/world; no failed call state is continued.
for mode in ('parent-small','parent-matrix'):
 gas=1000000000;wall=1200
 for attempt in range(1,7):
  report=O/f'{mode}-attempt-{attempt}';args=[O/'driver',mode,B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',F/'fixture-manifest.json',F,report,str(gas)]
  row=run(f'{mode}-attempt-{attempt}',args,wall);row.update(gasBudget=gas,wallBudget=wall);rows.append(row)
  if row['exit']==0:
   rr=run(f'{mode}-reopen-{attempt}',[args[0],'reopen',*args[2:]],wall);assert rr['exit']==0,rr;rows.append(rr);break
  failure=report/'gate-failure.json'
  if row['timedOut']:wall*=2
  elif failure.exists() and json.load(open(failure)).get('failure',{}).get('classification')=='test-only-gas-budget':gas*=2
  else:raise AssertionError(row)
 else:raise AssertionError('test retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','generatedOnly':True,'initialGas':1000000000,'attempts':rows,'transportDiagnosticDelta':'116 bootstrap/266 derived classes; CP2MiB; constructor-only int-zero audit generalized to typed ints, specific full map heap checked separately','noEvmOrGuestCodeModificationByParentDriver':True},indent=2)+'\n');print(json.dumps(rows,indent=2))
