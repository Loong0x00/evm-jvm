#!/usr/bin/env python3
"""Authenticate reused generated schedules and independently reopen copied q1 world.
No original Minecraft inputs are read. This does not claim a fresh full q1 run.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=H.parent/'pattern-compile-bootstrap/reference/string-replaceall-bounded/results'
B=ROOT/'build/java-diff-mc-string-replaceall-build-parent-p38'
G=ROOT/'build/java-diff-mc-string-replaceall-generated-parent-p38d'
F=ROOT/'build/java-diff-mc-string-replaceall-bounded-fixtures-parent-p38d'
W=Path('/home/user/evm-jvm/string-replaceall-bounded/build/java-diff-mc-string-replaceall-bounded-build-p38-final-v2/string-replaceall-attempt-1')
O=ROOT/'build/java-diff-mc-string-replaceall-parent-worker-q1-reopen-p38';assert not O.exists();O.mkdir()
read=lambda p:json.load(open(p));sha=lambda b:hashlib.sha256(b).hexdigest()
x=read(R/'p38-final-v2/string-replaceall-attempt-1/gate-failure.json');proof=read(B/'source-proof.json');wp=read(R/'p38-final-v2/source-proof.json');fresh=read(G/'parent-large/parent-summary.json')
assert x['failure']['error']=='smaller-quantum replaceAll schedule used fewer calls: q65536-string-replaceall-matrix=1 q4096-string-replaceall-matrix=9'
for k in ('candidateBootstrapRoot','bootstrapCount'):assert proof[k]==wp[k]
for role in ('engine','coordinator'):assert proof[role]['runtimeSHA256']==wp[role]['runtimeSHA256']
fm=read(F/'fixture-manifest.json');wm=read(R/'p38-final-v2/fixture-manifest.json')
assert fm['cases']['StringReplaceAllMatrix']==wm['cases']['StringReplaceAllMatrix']
rowkeys=('machineStateRoot','vfsStateRoot','totalJvmSteps','totalInternalSteps')
for old,new in zip(x['schedules'][:2],fresh['schedules']):
 for k in rowkeys:assert old['final'][k]==new['final'][k]
 assert old['readOnlyCheckpointHeapAudit']==new['readOnlyCheckpointHeapAudit']
for row,q,calls in zip(x['schedules'],(65536,4096,7,1),(1,9,4999,34992)):
 assert row['quantum']==q and row['callCount']==calls and row['rawCount']==1 and row['rawBytes']==2446 and row['bootstrapCount']==104
 assert row['final']['lifecycle']==row['final']['outcome']==2 and row['final']['javaKind']==0
 for k in rowkeys:assert row['final'][k]==x['schedules'][0]['final'][k]
 assert row['readOnlyCheckpointHeapAudit']==x['schedules'][0]['readOnlyCheckpointHeapAudit']
req=read(W/'reopen-requests/q1-string-replaceall-matrix.json');cp=(W/'checkpoints'/req['checkpoint']).read_bytes();assert sha(cp)==x['schedules'][-1]['checkpointSHA256']
env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'))
k=subprocess.check_output(['node','-e','const f=require("fs"),{keccak256}=require("js-sha3");console.log("0x"+keccak256(f.readFileSync(process.argv[1])))',str(W/'checkpoints'/req['checkpoint'])],env=env,text=True).strip();assert k==req['checkpointRoot']==x['schedules'][-1]['final']['checkpointRoot']
(O/'checkpoints').mkdir();(O/'checkpoints'/req['checkpoint']).write_bytes(cp);(O/'reopen-requests').mkdir();(O/'original-worker-request.json').write_text(json.dumps(req,indent=2)+'\n')
shutil.copytree(req['stateDir'],O/'world');req['stateDir']=str(O/'world');(O/'reopen-requests/q1-string-replaceall-matrix.json').write_text(json.dumps(req,indent=2)+'\n')
args=[G/'driver','reopen',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',G/'fixture-manifest.json',F,O,'16000000000']
with (O/'reopen.log').open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
reopen=read(O/'reopen-summary.json');assert reopen['reopenCount']==1 and reopen['reopens'][0]['distinctProcess'] and reopen['reopens'][0]['epoch']==34992
measurement=read(R/'p38-final-v1/measurement-record.json');assert measurement['selectedGasBudget']==16000000000
result={'status':'PASS','engineRuntimeSHA256':proof['engine']['runtimeSHA256'],'bootstrapRoot':proof['candidateBootstrapRoot'],'sameGeneratedMatrixClassBytes':True,'independentFreshLargeSchedulesEqualWorkerTerminalMachineVfsCountersAndHeap':True,'workerCompleteSchedulesReusedNotFreshParentRuns':True,'workerCompleteSchedulesSeconds':4189.546,'workerScheduleCalls':[1,9,4999,34992],'testOnlyFullMatrixGas':16000000000,'testOnlyFullMatrixWallSeconds':4800,'callLimit':40000,'cleanOneBProbeAndEarlierDiagnosticTwoBFourBEightBProbesDistinct':True,'parentCopiedWorkerQ1FreshProcessReopen':reopen,'checkpointBytes':len(cp),'checkpointSHA256':sha(cp),'sourceFailureReportSHA256':sha((R/'p38-final-v2/string-replaceall-attempt-1/gate-failure.json').read_bytes()),'budgetMeasurementSHA256':sha((R/'p38-final-v1/measurement-record.json').read_bytes()),'originalMinecraftInputsRead':False}
(H/'artifacts/worker-reuse-parent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='parentCopiedWorkerQ1FreshProcessReopen'},indent=2))
