#!/usr/bin/env python3
"""Read-only wire/heap consistency checks and P39 parent evidence archive."""
from pathlib import Path
import hashlib,json,shutil,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];A=H/'artifacts';A.mkdir(exist_ok=True)
B=ROOT/'build/java-diff-mc-hash-map-put-build-parent-p39';G=ROOT/'build/java-diff-mc-hash-map-put-generated-parent-p39';C=ROOT/'build/java-diff-mc-hash-map-put-controls-parent-p39';CO=ROOT/'build/java-diff-mc-hash-map-put-coordinator-parent-p39b';P=ROOT/'build/java-diff-mc-hash-map-put-original90-precise-parent-p39';W=ROOT/'build/java-diff-mc-hash-map-put-original90-parent-p39/official'
read=lambda p:json.load(open(p));sha=lambda b:hashlib.sha256(b).hexdigest()
sys.path.insert(0,str(H));import checkpoint_diagnostic as d

def ref(cell):
 v=int(cell,16);assert v>>64==2;return v&((1<<64)-1)
def jint(cell):
 v=int(cell,16);assert v>>64==1;v&=0xffffffff;return v if v<0x80000000 else v-0x100000000
def audit(blob,raw,expected,handle=None):
 x=d.inspect(blob);assert x['classCount']==raw+105;objects={r['handle']:r for r in x['heap']};maps=[r for r in x['heap'] if r['classIndex']==raw+100 and int(r['metadata'],16)>>255]
 if handle is None:
  state=next(s for s in x['initialization'] if s['classIndex']==0);handle=ref(next(r['packedValue']for r in state['staticValues'] if r['fieldIndex']==0))
 m=objects[handle];assert m in maps and m['count']==6
 f=m['cells'];size,mod,threshold=map(jint,f[2:5]);table=objects[ref(f[0])];assert ref(f[1])==0 and f[5]=='0x6000000003f400000'
 assert (size,mod,threshold,table['count'])==expected,(size,mod,threshold,table['count'],expected)
 assert table['rank']==1 and table['metadata']==hex(0x100+raw+104) and not table['sparse'] and not table['packedFloat']
 seen=set();nodes=[];lengths=[]
 for index,head in enumerate(table['cells']):
  h=int(head,16);chain=0
  while h:
   assert h not in seen;seen.add(h);node=objects[h];assert node['classIndex']==raw+104 and node['count']==4 and int(node['metadata'],16)>>255
   hashcode=jint(node['cells'][0]);assert (hashcode&(table['count']-1))==index
   key,value,nxt=map(ref,node['cells'][1:]);nodes.append({'handle':h,'hashBits':f'{hashcode&0xffffffff:08x}','key':key,'value':value,'next':nxt,'bucket':index});h=nxt;chain+=1
  lengths.append(chain)
 assert len(nodes)==size
 allnodes=[r for r in x['heap'] if r['classIndex']==raw+104 and int(r['metadata'],16)>>255];assert len(allnodes)==size
 return x,objects,{'mapHandle':handle,'tableHandle':table['handle'],'tableRuntimeType':'[Ljava/util/HashMap$Node;','tableLength':table['count'],'size':size,'modCount':mod,'threshold':threshold,'loadFactorBits':'3f400000','entrySetNull':True,'normalEagerDenseTable':True,'allNodesRealAndReachableExactlyOnce':True,'nodes':nodes,'bucketLengths':lengths,'checkpointSHA256':sha(blob)}

all_generated=[]
for directory,raw,want in [('parent-small-attempt-1',1,(3,3,12,16)),('parent-resize-attempt-2',2,(32,32,48,64))]:
 report=read(G/directory/'parent-summary.json');assert report['engineRuntimeSHA256']=='694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6'
 for row in report['schedules']:
  assert row['final']['lifecycle']==row['final']['outcome']==2 and row['final']['javaKind']==0
  cp=G/directory/'checkpoints'/(row['name']+'.checkpoint.bin');x,o,m=audit(cp.read_bytes(),raw,want);assert m['checkpointSHA256']==row['checkpointSHA256'];all_generated.append({'schedule':row['name'],'quantum':row['quantum'],'jvmSteps':row['final']['totalJvmSteps'],**m})
controls=read(C/'parent-controls/parent-controls-summary.json');assert len(controls['controls'])==4 and all(r['atomic'] for r in controls['controls'])
for name,raw,want in [('tree',2,(10,10,48,64)),('get',1,(1,1,12,16))]:
 x,o,m=audit((C/'parent-controls'/('successful-before-refusal-'+name+'.bin')).read_bytes(),raw,want);all_generated.append({'lastSuccessfulBeforeExplicitRefusal':name,**m})
(A/'generated-map-heap-proof.json').write_text(json.dumps({'status':'PASS','scope':'read-only generated checkpoint diagnostics; no execution authority','maps':all_generated},indent=2)+'\n')

head=read(W/'durable-head.json');blob=(W/'checkpoints'/(head['checkpointSHA256']+'.bin')).read_bytes();x,o,m=audit(blob,90,(22,22,24,32),5980)
assert x['lifecycle']==1 and head['jvmSteps']==1974606 and head['internalSteps']==98 and head['epoch']==36
assert any(s['classIndex']==83 and s['state']==2 and s['initializerStarted']==1 for s in x['initialization'])
assert not any(f['classIndex'] in (83,190,194) for f in x['frames'])
def text(handle):
 s=o[handle];assert s['classIndex']==116 and s['count']==2;a=o[ref(s['cells'][0])];assert a['metadata']=='0x43';return ''.join(chr(int(v,16))for v in a['cells'])
for n in m['nodes']:
 key=text(n['key']);h=0
 for ch in key:h=(31*h+ord(ch))&0xffffffff
 assert n['hashBits']==f'{(h^(h>>16)):08x}';n['keyText']=key
assert {n['value'] for n in m['nodes']}=={int(v,16)for v in o[5970]['cells']} and len(o[5970]['cells'])==22
assert sorted(n['keyText']for n in m['nodes'])==sorted(['black','darkblue','darkgreen','darkaqua','darkred','darkpurple','gold','gray','darkgray','blue','green','aqua','red','lightpurple','yellow','white','obfuscated','bold','strikethrough','underline','italic','reset'])
old_tables=[r for r in x['heap'] if r['metadata']==hex(0x100+194) and r['count']==16];assert len(old_tables)==1 and all(int(c,16)==0 for c in old_tables[0]['cells'])
# Read-only P38 comparison; no old checkpoint is continued or migrated.
oldw=ROOT/'build/java-diff-mc-string-replaceall-original90-parent-p38/official';oldh=read(oldw/'durable-head.json');old=d.inspect((oldw/'checkpoints'/(oldh['checkpointSHA256']+'.bin')).read_bytes())
def sine(t):
 a=[r for r in t['heap'] if r['metadata']=='0x46' and r['count']==65536];assert len(a)==1;return sha(b''.join(int(v,16).to_bytes(4,'big')for v in a[0]['cells']))
assert sine(x)==sine(old)=='87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2'
m.update(genuineOriginal=True,all22PutCallsReturned=True,enumInitializerCompleted=True,noMapOrEnumInitializerFrameRemaining=True,valuesEqualAll22OriginalEnumRefs=True,storedHashesAndBucketsConsistent=True,old16SlotTableCleared=True,full65536SineBitsEqualAcceptedReadOnlyOracleVerifiedTable=True,sineRawBitsSHA256=sine(x),checkpointBytes=len(blob),jvmSteps=head['jvmSteps'],internalSteps=head['internalSteps'],classCount=x['classCount'],heapCounts=x['heapCounts'])
(A/'original-map-put-return-proof.json').write_text(json.dumps(m,indent=2)+'\n')
(A/'original-frontier-frames.json').write_text(json.dumps({'checkpointSHA256':head['checkpointSHA256'],'classCount':x['classCount'],'frames':x['frames'],'scope':'read-only metadata, never execution authority'},indent=2)+'\n')

for role in ('engine','coordinator'):
 (A/role).mkdir(exist_ok=True)
 for p in (B/role).iterdir():
  if p.is_file() and p.suffix in ('.sol','.json','.js') and not p.name.endswith('.abi.json'):shutil.copy2(p,A/role/p.name)
for src,name in [(B/'pins.json','parent-build-pins.json'),(B/'root-audit.json','root-audit.json'),(P/'summary.json','original90-replay-summary.json'),(P/'verified-original90.json','verified-original90.json'),(W/'durable-head.json','original90-last-head.json'),(W.parent/'reports/official/resume-refusal.json','original90-q1-refusal.json'),(G/'summary.json','parent-generated-summary.json'),(G/'parent-small-attempt-1/parent-summary.json','small-summary-1B.json'),(G/'parent-resize-attempt-2/parent-summary.json','resize-summary-2B.json'),(G/'parent-resize-attempt-1/gate-failure.json','preserved-resize-1B-shortage.json'),(C/'parent-controls/parent-controls-summary.json','refusal-controls-summary-1B.json'),(CO/'coordinator/coordinator-summary.json','coordinator-summary-1B.json'),(CO/'process.json','coordinator-process.json'),(C/'coordinator/gate-failure.json','preserved-coordinator-old-namespace-refusal.json')]:shutil.copy2(src,A/name)
for src,name in [(B/'product-driver.go.txt','canonical-driver.go.txt'),(ROOT/'build/java-diff-mc-hash-map-put-original-authorized-parent-p39/main.go','max-gas-driver.go.txt')]:shutil.copy2(src,H/name)
for source,label in [(G/'parent-small-attempt-1/reopen-summary.json','small'),(G/'parent-resize-attempt-2/reopen-summary.json','resize')]:shutil.copy2(source,A/(label+'-fresh-process-reopen.json'))
receipts=[{'file':p.name,'sha256':sha(p.read_bytes())}for p in sorted((W.parent/'reports/official').glob('slice-*.json'))];assert len(receipts)==36;(A/'ordered-original-receipt-hashes.json').write_text(json.dumps(receipts,indent=2)+'\n')
rs=read(P/'summary.json');refusal=read(A/'original90-q1-refusal.json');assert refusal['diagnostic']['name']=='bdc' and refusal['rootUnchanged']
summary={'profile':'MC-HASH-MAP-PUT-BOUNDED-P39','candidateCommit':'a1ff3e3d3de56d38cf102aa2746372f5f6bea02c','runtimeBytes':418986,'runtimeSHA256':'694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6','bootstrapCount':105,'bootstrapRoot':read(B/'pins.json')['bootstrapRoot'],'changedPriorLeaf':100,'newNodeLeaf':104,'unchangedPriorLeaves':103,'nativeBindings':21,'newOperationalNativeBindings':0,'runtimeCap':1048576,'checkpointCap':2097152,'rawLimits':[150,1063930],'diagnosticClassBound':255,'gethEvmGasStateConsensusUnchanged':True,'localPreinstalledNotStandardCreate':True,'independentSourceReview':'PASS source3b195082b4c7ca83610274b18b9b13149b7749e6c6cba690549fb583041a9ae0, sa_a2bea9ac1a44468e; no files changed','generated':read(G/'summary.json'),'controlsSeconds':read(C/'parent-controls-process.json')['wallSeconds'],'coordinatorSeconds':read(CO/'process.json')['wallSeconds'],'coordinatorMaxCallGas':read(CO/'coordinator/coordinator-summary.json')['maxCallGas'],'coordinatorCalls':3224,'original':{'jvmSteps':head['jvmSteps'],'internalSteps':head['internalSteps'],'epoch':head['epoch'],'lifecycle':head['lifecycle'],'checkpointSHA256':head['checkpointSHA256'],'checkpointBytes':len(blob),'verifiedSuccessfulReceipts':36,'preciseReplaySeconds':rs['wallSeconds'],'progressFromP38Jvm':head['jvmSteps']-1923759,'actualMapSize':22,'actualTableLength':32,'actualThreshold':24,'actualModCount':22,'all22PutCallsReturned':True},'nextMeasuredBlocker':{'name':'bdc','error':'MCEntryMissingClass','selector':refusal['selector'],'diagnostic':refusal['diagnostic'],'resourceNotMeasuredOrAdded':True,'notImplementedByUserStopBoundary':True},'stopAfterCurrentBlockerForReboot':True,'noP40Started':True,'notReached':['main argument processing','world preparation','accepted EULA/configuration startup','listening server','Done']}
(A/'bdc-resource-blocker.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':'PASS parent P39 evidence collected','original':summary['original'],'next':summary['nextMeasuredBlocker']},indent=2))
