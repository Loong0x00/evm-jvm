#!/usr/bin/env python3
"""Parent checks fresh shared-world runs, not the interrupted draft's counters."""
import json,hashlib,sys
from pathlib import Path
b=Path(sys.argv[1]);out=Path(sys.argv[2])
def load(p):return json.loads(p.read_text())
world_names=['direct','q1','q7','input9','memory1','memory7','boundary']
world={n:load(b/n/'durable-head.json') for n in world_names[:-1]}
reference=world['direct']
for n,m in world.items():
 assert m['checkpointSHA256'] and m['lifecycle']==2 and m['javaKind']==0 and m['jvmSteps']==36 and m['internalSteps']==5,(n,m)
 assert m['result']==(299 if n=='input9' else 317)
 if n!='input9':
  for key in ['packageRoot','indexRoot','resourceRoots','classSizes','machineRoot','vfsRoot','jvmSteps','internalSteps']:assert m[key]==reference[key],(n,key)
 expected={'direct':1,'q1':36,'q7':6,'input9':1,'memory1':36,'memory7':6}[n]
 assert m['slices']==expected and m['epoch']==expected
 if not n.startswith('memory'):
  rep=load(b/n/'world-report.json');assert rep['engineHeadOwner']==m['coordinator'] and rep['engineHeadLifecycle']==2
  assert len(set(m['processPids']))>=2
 else:assert m['stage']=='memory-final'
 f=load(b/n/'java-write-refusal.json')
 assert f['before']==f['afterBeforeHostRestore'] and f['completedChangedSstores']>=1
 assert f['code']==7 and f['selector']=='0xf15d7343' and not f['nestedOOG']
assert len(set(world['q1']['processPids']))>=4
assert (b/'oracle.log').read_text().splitlines()==['7=317','9=299']
negative=load(b/'q1/negative-report.json');assert [x['name'] for x in negative['failures']]==['CoordinatorError','CoordinatorError','LC0ControlError']
assert [x['code'] for x in negative['failures']]==[17,18,3]
assert all(x['rootEqualBeforeHostRestore'] for x in negative['failures'])
pub=load(b/'q1/publication-failure.json')
assert pub['oldRoot']==pub['restoredRoot']!=pub['unpublishedCandidateRoot']
assert pub['retryOutputIdentical'] and not pub['failedOutputConsumed']
page_fail=load(b/'q1/direct-evm-failure.json');assert page_fail['code']==8 and page_fail['createOpcodes']>=1 and page_fail['rootEqualBeforeHostRestore']
boundary=load(b/'boundary/boundary-report.json')
assert [x['count'] for x in boundary['constructors']]==[1,2,3,4]
assert boundary['constructors'][-1]['total']==65536
assert boundary['paging']['result']==9 and boundary['paging']['lifecycle']==2
assert boundary['paging']['actualReadCount']==18 and sum(boundary['paging']['actualReadSizes'])==65536
assert all(0<x<=4096 for x in boundary['paging']['actualReadSizes'])
assert boundary['pins']['runtimeBytes']<=24576 and boundary['pins']['maximumCompleteInitBytes']<=49152
want={'empty-package':2,'empty-class-name':6,'aggregate-65537':12,'wrong-decoder-ref':4,'wrong-raw-name':8,'wrong-resource-F':10,'non-final':7,'decoder-owner-mismatch':14,'wrong-package-assertion':16,'duplicate-decoder':5,'duplicate-name-distinct-decoder':5,'five-class-count':2,'wrong-index-root':9}
found={x['label']:x.get('code') for x in boundary['failures'] if x['name']=='CoordinatorError'}
assert found==want,(found,want)
assert any(x['label']=='declared-class-name-mismatch' and x['name']=='LinkError' for x in boundary['failures'])
# CREATE creator nonces are outside its child call frame; failed-CREATE probes
# normalize to the published root afterward. Do NOT claim those raw roots equal.
assert boundary['counts']['reorderingChangesRoot']
# Cross-process totals are sums of ACTUAL counter changes within each process.
# No fsync/rename is inferred merely because a manifest was readable on reopen.
keys=['evmCalls','ordinaryCreates','successfulEvmMutations','commitReloads','trieCodeSyncs','manifestFileSyncs','manifestRenames','directorySyncs','checkpointFileSyncs','checkpointRenames','checkpointDirectorySyncs','actualNestedFrames','actualNestedCreateOpcodes','actualSstoreOpcodes','gas']
stats={};all_pids=set()
for n in world_names:
 d={k:0 for k in keys};reads=[];pids=[];maxgas=0;maxms=0
 for f in sorted((b/n).glob('process-*.json')):
  r=load(f);a=r['initialCounters'];z=r['finalCounters'];pids.append(r['pid']);assert r['pid'] not in all_pids;all_pids.add(r['pid'])
  for k in keys:assert z[k]>=a[k];d[k]+=z[k]-a[k]
  a_reads=a['actualDI0ReadSizes'] or [];z_reads=z['actualDI0ReadSizes'] or [];assert z_reads[:len(a_reads)]==a_reads;reads+=z_reads[len(a_reads):]
  maxgas=max(maxgas,z['maxGas']);maxms=max(maxms,z['maxCallMs'])
 assert d['commitReloads']==d['successfulEvmMutations']+1,(n,d) # explicit LOCAL install
 assert d['trieCodeSyncs']==d['commitReloads']+(1 if n=='q1' else 0),(n,d)
 assert d['manifestFileSyncs']==d['manifestRenames']==d['directorySyncs']
 assert maxgas<100000000 and maxms<30000
 assert all(0<x<=4096 for x in reads)
 if n!='boundary':
  # Every chain has a failed low-gas start (2 reads). q1 additionally has
  # failed epoch-CAS (2 reads) and successful-EVM/unpublished retry (2 reads).
  want_reads=2*world[n]['slices']+2+(4 if n=='q1' else 0)
  assert len(reads)==want_reads,(n,len(reads),want_reads)
 stats[n]={'actualProcessDeltas':d,'pids':pids,'readCountIncludingFailedCalls':len(reads),'maxCallGas':maxgas,'maxCallMillis':maxms}
summary={'status':'PARENT-VERIFIED DISPOSABLE SHARED-WORLD PREFLIGHT, NOT PRODUCTION ACCEPTANCE','results':{n:{k:m[k] for k in ['result','slices','epoch','jvmSteps','internalSteps','packageRoot','checkpointRoot','machineRoot','vfsRoot','trieRoot']} for n,m in world.items()},'actualProcessStats':stats,'constructorPins':boundary['pins'],'boundary':boundary,'publicationFailure':pub,'negativeCalls':negative,'coordinatorArtifactSHA256':hashlib.sha256((b/'coordinator.json').read_bytes()).hexdigest(),'limits':'ordinary100M/30s; no1Bcalls; no accepted engine/image/heap/VFS quota changes','authority':'generated ZIP bytes and assertions only; EVM derives class bytes; no reflection/private Session/host class or ZIP parser in driver; LOCAL install exact engine only'}
out.write_text(json.dumps(summary,indent=2)+'\n')
print('PARENT STRICT PASS: shared-world direct/q1/q7 and memory/disk equality, two input results, exact64KiB, actual process continuation/IO and post-write coded rollback')
print('results317/299; Java36/internal5; slices1/36/6; processes',len(all_pids))
