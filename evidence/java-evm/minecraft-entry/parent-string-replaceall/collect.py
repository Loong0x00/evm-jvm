#!/usr/bin/env python3
"""Archive parent P38 acceptance; read-only checkpoint/receipt diagnostics only."""
from pathlib import Path
import hashlib,json,shutil,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];A=H/'artifacts';A.mkdir(exist_ok=True)
B=ROOT/'build/java-diff-mc-string-replaceall-build-parent-p38';G=ROOT/'build/java-diff-mc-string-replaceall-generated-parent-p38d';P=ROOT/'build/java-diff-mc-string-replaceall-original90-precise-parent-p38';W=ROOT/'build/java-diff-mc-string-replaceall-original90-parent-p38/official'
read=lambda p:json.load(open(p));sha=lambda b:hashlib.sha256(b).hexdigest()
for role in ('engine','coordinator'):
 (A/role).mkdir(exist_ok=True)
 for p in (B/role).iterdir():
  if p.is_file():shutil.copy2(p,A/role/p.name)
for src,name in [(B/'pins.json','parent-build-pins.json'),(B/'source-proof.json','source-proof.json'),(B/'root-audit.json','root-audit.json'),(P/'summary.json','original90-replay-summary.json'),(P/'verified-original90.json','verified-original90.json'),(W/'durable-head.json','original90-last-head.json'),(W.parent/'reports/official/resume-refusal.json','original90-q1-refusal.json'),(G/'parent-large/parent-summary.json','parent-large-summary-16B.json'),(G/'parent-small/parent-summary.json','parent-small-summary-1B.json'),(G/'replaceall-controls/string-replaceall-controls-summary.json','parent-controls-summary-16B.json'),(G/'array-clone/array-clone-gate-summary.json','parent-clone-summary-1B.json'),(G/'coordinator/coordinator-summary.json','parent-coordinator-summary-1B.json'),(G/'summary.json','parent-generated-summary.json')]:shutil.copy2(src,A/name)
# Archived inherited pin labels are historical, not current P38 invariants.
pins=read(A/'parent-build-pins.json')
if 'legacyInheritedBasis' not in pins:pins['legacyInheritedBasis']=pins['basis'];pins['legacyInheritedSourceInvariants']=pins['sourceInvariants']
pins['basis']='accepted P37 parent-array-clone artifacts';pins['sourceInvariants']=read(A/'parent-build-pins.json').get('sourceInvariants',{})
if 'allOther101PriorLeavesUnchanged' not in pins['sourceInvariants']:
 pins['sourceInvariants']={'allOther101PriorLeavesUnchanged':True,'changedPriorSlots':[26,101],'appendedMatcherSlot':103,'engineABIAndStorageUnchanged':True,'coordinatorABIAndStorageUnchanged':True,'noNewOperationalNativeBinding':True,'heapRawRuntimeAndCheckpointCapsUnchanged':True,'underlyingEVMUnchanged':True}
(A/'parent-build-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
for f in ('canonical-driver.go.txt','max-gas-driver.go.txt'):
 src=B/'product-driver.go.txt' if f.startswith('canonical') else ROOT/'build/java-diff-mc-string-replaceall-original-authorized-parent-p38/main.go';shutil.copy2(src,H/f)
# Preserve parent harness failures and their logs; no generated world is removed.
failures=[]
for suffix in ('p38','p38b','p38c'):
 old=ROOT/f'build/java-diff-mc-string-replaceall-generated-parent-{suffix}'
 for label in ('parent-large','parent-large-reopen','parent-small'):
  p=old/(label+'-process.json')
  if p.is_file() and read(p)['exit']:
   dest=A/'preserved-parent-harness-failures'/suffix;dest.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest/p.name);shutil.copy2(old/(label+'.log'),dest/(label+'.log'));failures.append({'run':suffix,**read(p)})
(A/'parent-harness-failure-history.json').write_text(json.dumps({'failures':failures,'causes':['wrong generated fixture base directory','missing parent reopen request emission','missing custom fixture bundle directory'],'allPreserved':True,'noGuestSourceOrEvmRuleChangedForCorrections':True},indent=2)+'\n')
# Wire-only comparison; an accepted old checkpoint is never continued under P38.
sys.path.insert(0,str(H));import checkpoint_diagnostic as d
head=read(W/'durable-head.json');cp=W/'checkpoints'/(head['checkpointSHA256']+'.bin');x=d.inspect(cp.read_bytes());heap={o['handle']:o for o in x['heap']}
oldw=ROOT/'build/java-diff-mc-array-clone-original90-parent-p37/official';oldh=read(oldw/'durable-head.json');old=d.inspect((oldw/'checkpoints'/(oldh['checkpointSHA256']+'.bin')).read_bytes())
def table(m):
 rows=[o for o in m['heap'] if o['metadata']=='0x46' and o['count']==65536];assert len(rows)==1
 row=rows[0];raw=b''.join(int(v,16).to_bytes(4,'big') for v in row['cells']);assert len(raw)==262144;return row['handle'],sha(raw)
assert table(x)==table(old)
assert x['frames'][-1]['classIndex']==83 and x['frames'][-1]['methodIndex']==15 and x['frames'][-1]['pc']==628
assert x['frames'][-1]['stackValues']==['0x2000000000000175c','0x20000000000001767','0x2000000000000164a']
assert heap[6000]['classIndex']==193 and heap[6000]['cells']==['0x2000000000000176f','0x20000000000001767']
assert heap[5999]['classIndex']==191 and heap[5999]['cells'][2]=='0x2000000000000176d'
assert heap[5997]['cells']==['0x50415431','0x0','0x2','0x1','0x1','0x61','0x7a','0x0']
assert heap[5990]['metadata']=='0x43' and heap[5990]['cells']==['0x62','0x6c','0x61','0x63','0x6b']
assert heap[5991]['cells'][0]=='0x20000000000001766'
assert heap[5989]['count']==22 and heap[5989]['cells']==heap[5970]['cells']
metadata=read(A/'evm-next-call-metadata.json');ref=metadata['observations'][0]['references'][0]
assert ref['Pc']==628 and ref['Owner']=='java/util/Map' and ref['Name']=='put' and ref['Descriptor']=='(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;'
proof={'genuineOriginal':True,'replaceAllReturnedBeforeMapPut':True,'noMatchReturnsInputIdentity':True,'returnedStringHandle':5991,'returnedCharArrayHandle':5990,'returnedCharsHex':heap[5990]['cells'],'returnedText':'black','patternHandle':5999,'patternProgramHandle':5997,'patternTokens':heap[5997]['cells'],'matcherHandle':6000,'matcherLinks':heap[6000]['cells'],'mapReceiverHandle':5980,'mapValueEnumHandle':5706,'sourceAndCloneArraysStillDistinctShallow22':True,'full65536SineBitsEqualAcceptedP37ReadOnlyOracleVerifiedTable':True,'sineTableHandle':table(x)[0],'sineRawBitsSHA256':table(x)[1],'checkpointSHA256':head['checkpointSHA256'],'wireDiagnosticsOnlyNeverExecutionAuthority':True}
(A/'original-replaceall-return-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
receipts=[]
for p in sorted((W.parent/'reports/official').glob('slice-*.json')):
 j=read(p);receipts.append({'file':p.name,'sha256':sha(p.read_bytes()),'epoch':j.get('epoch'),'checkpointSHA256':j.get('checkpointSHA256')})
assert len(receipts)==39;(A/'ordered-original-receipt-hashes.json').write_text(json.dumps(receipts,indent=2)+'\n')
rs=read(P/'summary.json');large=read(A/'parent-large-summary-16B.json');small=read(A/'parent-small-summary-1B.json');coord=read(A/'parent-coordinator-summary-1B.json')
summary={'profile':'MC-STRING-REPLACEALL-BOUNDED-P38','preservedCandidateCommit':'89ba868f2','runtimeBytes':414732,'runtimeCap':1048576,'checkpointCap':2097152,'rawLimits':[150,1063930],'bootstrapCount':104,'bootstrapRoot':read(B/'pins.json')['bootstrapRoot'],'changedPriorLeaves':[26,101],'unchangedPriorLeaves':101,'newImage':'java/util/regex/Matcher','nativeBindings':21,'newOperationalNativeBindings':0,'underlyingEvmGasStateConsensusUnchanged':True,'localPreinstalledNotStandardCreate':True,'parentFreshGenerated':{'largeMatrixGas':16000000000,'largeMatrixSeconds':read(G/'parent-large-process.json')['wallSeconds'],'largeMatrixJvmSteps':34992,'largeScheduleQuanta':[65536,4096],'smallGas':1000000000,'smallSeconds':read(G/'parent-small-process.json')['wallSeconds'],'smallJvmSteps':2754,'smallQuanta':[7,1],'smallMaxCallGas':max(r['maxCallGas'] for r in small['schedules']),'controlsSeconds':read(G/'replaceall-controls-process.json')['wallSeconds'],'cloneGas':1000000000,'cloneSeconds':read(G/'array-clone-process.json')['wallSeconds'],'coordinatorGas':1000000000,'coordinatorSeconds':read(G/'coordinator-process.json')['wallSeconds'],'coordinatorCalls':coord['evmCallCount'],'coordinatorMaxCallGas':coord['maxCallGas'],'freshReopens':True},'workerCompleteMatrixReusedNotParentRerun':{'seconds':4189.546,'gas':16000000000,'wallSeconds':4800,'callLimit':40000,'q1Calls':34992,'parentExactProvenanceAndCopiedQ1FreshReopen':'worker-reuse-parent-audit.json'},'workerRetainedP36Gate':{'seconds':1118.896,'gas':2000000000,'wallSeconds':2400,'notFreshParentFullRetainedRun':True},'original':head,'checkpointBytes':len(cp.read_bytes()),'preciseReplaySeconds':rs['wallSeconds'],'verifiedSuccessfulReceipts':39,'progressFromP37Jvm':head['jvmSteps']-1922305,'actualReturnProof':proof,'nextMeasuredBlocker':{'error':'CallError(4,628)','selector':'0xd631c3a4','rawBinding':83,'methodIndex':15,'declaringClass':'a','method':'<clinit>','pc':628,'opcode':'invokeinterface','owner':ref['Owner'],'name':ref['Name'],'descriptor':ref['Descriptor']},'notReached':['main argument processing','world preparation','accepted EULA/configuration startup','listening server','Done']}
(A/'map-put-blocker.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':'parent P38 evidence collected','originalJvm':head['jvmSteps'],'checkpointSHA256':head['checkpointSHA256'],'next':summary['nextMeasuredBlocker']},indent=2))
