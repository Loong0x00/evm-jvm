#!/usr/bin/env python3
"""Parent checks actual per-process receipts and retained opaque EVM checkpoints."""
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]).resolve()
expected={'mode1-direct':(381,54,4,1,4096),'mode1-q7':(381,54,4,8,7),'mode1-q1':(381,54,4,54,1),'mode0-direct':(341,24,4,1,4096),'mode2-direct':(351,57,4,1,4096),'mode3-null':(0,22,5,1,4096)}
all_pids=set();finals={};all_gas=[];blob_count=0
for label,(value,jvm,internal,slices,q) in expected.items():
 setup=json.loads((out/'results'/f'{label}-setup.json').read_text());assert setup['classCount']==2 and setup['totalClassBytes']==795
 ops=setup['mutationReceipts'];assert {x['method'] for x in ops}=={'InitialAS0Create','Append','Seal','CreateIndex','DiscoverIndex','ScanIndex','FinishIndex','CreateDecoder','StepDecoder','PublishDecoder','CreateCoordinator'}
 assert ops[-1]['stateRoot']==setup['stateRoot']
 for x in ops:assert 0<x['gas']<=100000000;all_gas.append(x['gas'])
 refused=setup['packageRefusal'];assert refused['publishedRootBefore']==refused['publishedRootAfter'] and refused['revertData']=='0x27cad659'+'0'*62+'10' and 0<refused['gas']<=100000000;all_gas.append(refused['gas'])
 assert setup['pid'] not in all_pids;all_pids.add(setup['pid'])
 rows=[json.loads(p.read_text()) for p in sorted((out/'results').glob(label+'-[0-9]*.json'),key=lambda p:int(p.stem.rsplit('-',1)[1]))];assert len(rows)==slices,(label,len(rows))
 before=setup['stateRoot'];prevj=previ=0
 for n,r in enumerate(rows,1):
  assert 0<r['gasUsed']<=100000000,(label,'gas');all_gas.append(r['gasUsed'])
  assert r['pid'] not in all_pids;all_pids.add(r['pid'])
  assert not r['reopenedEngineInstalled'] and not r['reopenedASOCreated']
  assert r['loadedStateRoot']==before and r['stateRoot']!=before;before=r['stateRoot']
  assert r['epoch']==n and r['packageRoot']==setup['packageRoot'] and r['nestedEngineLogs']==1
  assert 0<r['totalJvmSteps']-prevj<=q and 0<=r['totalInternalSteps']-previ<=4096
  prevj,previ=r['totalJvmSteps'],r['totalInternalSteps']
  assert r['lifecycle']==(1 if n<slices else (3 if label=='mode3-null' else 2))
  assert all(r[k]!='0x'+'0'*64 for k in ('machineRoot','vfsRoot','checkpointRoot','packageRoot','as0ContentRoot','indexRoot'))
  assert r['as0ContentRoot']==setup['as0Root'] and r['indexRoot']==setup['indexRoot'] and len(r['decoderRoots'])==2
  cp=(out/f'world-{label}'/'checkpoints'/(r['checkpointRoot'][2:]+'.checkpoint')).read_bytes()
  assert 0<len(cp)<=1048576 and hashlib.sha256(cp).hexdigest()==r['checkpointSHA256'];blob_count+=1
 last=rows[-1];assert (last['result'],prevj,previ)==(value,jvm,internal)
 assert last['javaKind']==(6 if label=='mode3-null' else 0) and last.get('javaClass','')==''
 terminal=json.loads((out/'results'/f'{label}-terminal.json').read_text())
 assert terminal['pid'] not in all_pids;all_pids.add(terminal['pid'])
 for k in ('stateRoot','epoch','lifecycle','checkpointRoot','checkpointSHA256','machineRoot','vfsRoot','packageRoot'):assert terminal[k]==last[k],(label,k)
 assert not terminal['reopenedEngineInstalled'] and not terminal['reopenedASOCreated']
 finals[label]=last
for label in ('mode1-q7','mode1-q1'):
 for k in ('packageRoot','machineRoot','vfsRoot','as0ContentRoot','indexRoot','decoderRoots'):assert finals[label][k]==finals['mode1-direct'][k]
print(json.dumps({'distinctProcesses':len(all_pids),'actualOpaqueCheckpointHashesChecked':blob_count,'recordedMutationCalls':len(all_gas),'maxMutationGas':max(all_gas),'gasSum':sum(all_gas),'finals':finals},indent=2))
