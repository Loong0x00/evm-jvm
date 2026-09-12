#!/usr/bin/env python3
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]).resolve();fixture=json.loads((out/'fixture/fixture.json').read_text())
assert fixture['javac']=='javac 1.8.0_504'
assert fixture['oracle']=='0:R:341\n1:R:-266910634\n2:R:-821743102\n3:X:java.lang.NullPointerException\n'
for name,h in fixture['files'].items():
 p=out/'fixture'/('classes' if name.endswith('.class') else '')/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
finals={};pids=set();peak=0;counts={}
for label,want in {'mode0-direct':341,'mode1-direct':-266910634,'mode2-direct':-821743102,'mode2-q7':-821743102,'mode3-null':0}.items():
 setup=json.loads((out/'results'/f'{label}-setup.json').read_text());assert setup['classCount']==2 and 0<setup['totalClassBytes']<=65536
 assert setup['pid'] not in pids;pids.add(setup['pid'])
 assert all(0<x['gas']<=100000000 for x in setup['mutationReceipts'])
 bad=setup['packageRefusal'];assert bad['publishedRootBefore']==bad['publishedRootAfter'] and bad['revertData']=='0x27cad659'+'0'*62+'10'
 rows=[json.loads(p.read_text()) for p in sorted((out/'results').glob(label+'-[0-9]*.json'),key=lambda p:int(p.stem.rsplit('-',1)[1]))]
 q=7 if label.endswith('q7') else 4096;before=setup['stateRoot'];j=i=0
 for n,r in enumerate(rows,1):
  assert r['pid'] not in pids;pids.add(r['pid'])
  assert 0<r['gasUsed']<=100000000;peak=max(peak,r['gasUsed'])
  assert not r['reopenedEngineInstalled'] and not r['reopenedASOCreated'] and r['nestedEngineLogs']==1
  assert r['epoch']==n and r['loadedStateRoot']==before and r['stateRoot']!=before;before=r['stateRoot']
  assert r['packageRoot']==setup['packageRoot'] and r['as0ContentRoot']==setup['as0Root'] and r['indexRoot']==setup['indexRoot']
  assert 0<r['totalJvmSteps']-j<=q and 0<=r['totalInternalSteps']-i<=4096;j,i=r['totalJvmSteps'],r['totalInternalSteps']
  assert r['lifecycle']==(1 if n<len(rows) else (3 if label=='mode3-null' else 2))
  cp=(out/f'world-{label}'/'checkpoints'/(r['checkpointRoot'][2:]+'.checkpoint')).read_bytes();assert 0<len(cp)<=1048576 and hashlib.sha256(cp).hexdigest()==r['checkpointSHA256']
 last=rows[-1];assert last['result']==want and last['javaKind']==(6 if label=='mode3-null' else 0)
 assert len(rows)==((j+q-1)//q)
 t=json.loads((out/'results'/f'{label}-terminal.json').read_text());assert t['pid'] not in pids;pids.add(t['pid'])
 for k in ('stateRoot','epoch','lifecycle','checkpointRoot','checkpointSHA256','machineRoot','vfsRoot','packageRoot'):assert t[k]==last[k]
 assert not t['reopenedEngineInstalled'] and not t['reopenedASOCreated']
 finals[label]=last;counts[label]=len(rows)
for k in ('machineRoot','vfsRoot','packageRoot','as0ContentRoot','indexRoot','decoderRoots','totalJvmSteps','totalInternalSteps'):assert finals['mode2-direct'][k]==finals['mode2-q7'][k]
print(json.dumps({'fixture':fixture,'content':'real String.charAt over ASCII, NUL, U+03BB, surrogate pair D83D DE00, U+2603','distinctProcesses':len(pids),'maxJavaGas':peak,'sliceCounts':counts,'finals':finals},indent=2))
