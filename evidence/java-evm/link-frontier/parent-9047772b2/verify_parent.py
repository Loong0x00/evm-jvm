#!/usr/bin/env python3
"""Independent actual-field/opaque-blob checks, plus decisive cast/eager controls."""
import hashlib,json,pathlib,re,sys
out=pathlib.Path(sys.argv[1]).resolve();results=out/'results';zero='0x'+'0'*64
j=lambda name:json.loads((results/(name+'.json')).read_text())
fixture=json.loads((out/'fixture/fixture.json').read_text())
for name,h in fixture['javapSHA256'].items():assert hashlib.sha256((out/'fixture'/('javap-'+name[:-6]+'.txt')).read_bytes()).hexdigest()==h
code=(out/'fixture/javap-DemandEntry.txt').read_text()
assert re.search(r'35: checkcast\s+#3',code) and re.search(r'38: invokevirtual\s+#5',code)
castcode=(out/'fixture/javap-CastEntry.txt').read_text();castpcs=re.findall(r'(\d+): checkcast\s+',castcode);assert len(castpcs)==1;castpc=int(castpcs[0])
allpids=set();gas=[];cps=0
for f in results.glob('*.json'):
 x=json.loads(f.read_text());assert x['pid'] not in allpids;allpids.add(x['pid'])
 if x['command'] in ('slice','refusal'):
  assert 0<x['gasUsed']<=100000000;gas.append(x['gasUsed'])
  assert not x['reopenedEngineInstalled'] and not x['reopenedASOCreated']
 if x['command']=='refusal':
  b=bytes.fromhex(x['revertData'][2:]);assert len(b)==68
  assert x['selector']=='0x'+b[:4].hex() and int(x['code'])==int.from_bytes(b[4:36],'big') and int(x['detail'])==int.from_bytes(b[36:68],'big')
  for a in ('StateRoot','Epoch','CheckpointRoot'):assert x['before'+a]==x['after'+a]
  assert x['failedStateRoot']==zero and x['failedSliceSchema']==0 and x['failedCheckpointBytes']==0 and x['failedLogs']==0

def chain(world,names,q,terminal=None):
 global cps
 before=j(world+'-setup')['stateRoot'];oldj=oldi=0;rows=[]
 for at,name in enumerate(names,1):
  x=j(name);assert x['command']=='slice' and x['epoch']==at and x['nestedEngineLogs']==1
  assert x['loadedStateRoot']==before and x['stateRoot']!=before;before=x['stateRoot']
  assert 0<x['totalJvmSteps']-oldj<=q and 0<=x['totalInternalSteps']-oldi<=4096
  oldj,oldi=x['totalJvmSteps'],x['totalInternalSteps']
  setup=j(world+'-setup');assert x['packageRoot']==setup['packageRoot'] and x['as0ContentRoot']==setup['as0Root'] and x['indexRoot']==setup['indexRoot']
  cp=(out/f'world-{world}'/'checkpoints'/(x['checkpointRoot'][2:]+'.checkpoint')).read_bytes();assert 0<len(cp)<=1048576 and hashlib.sha256(cp).hexdigest()==x['checkpointSHA256'];cps+=1
  rows.append(x)
 if terminal:
  t=j(terminal)
  assert not t['reopenedEngineInstalled'] and not t['reopenedASOCreated']
  for k in ('stateRoot','epoch','lifecycle','checkpointRoot','checkpointSHA256','machineRoot','vfsRoot','packageRoot'):assert t[k]==rows[-1][k]
 return rows
for label in ('closed-direct0','closed-direct7','demand-0','eager-1','eager-2','eager-3','eager-super','eager-interface','cast-null','cast-present'):
 chain(label,[label],4096,label+'-terminal')
closed=chain('closed-q1',[f'closed-q1-{n}' for n in range(1,45)],1,'closed-q1-terminal')
assert all(x['lifecycle']==1 for x in closed[:-1]) and closed[-1]['lifecycle']==2
prior=chain('demand-q1',[f'demand-q1-{n}' for n in range(1,6)],1,'demand-q1-after')
assert all(x['lifecycle']==1 for x in prior)
fail=j('demand-q1-6');assert fail['beforeEpoch']==5 and fail['beforeStateRoot']==prior[-1]['stateRoot'] and fail['beforeCheckpointRoot']==prior[-1]['checkpointRoot']
for label in ('demand-1','demand-2','demand-3','super','interface'):
 fail=j(label+'-refusal');assert fail['beforeStateRoot']==j(label+'-setup')['stateRoot'] and fail['beforeEpoch']==0 and fail['beforeCheckpointRoot']==zero
# Direct class inclusion repairs the absent-reference cases without any demand loader.
for label,value in [('eager-1',51),('eager-2',52),('eager-super',9),('eager-interface',9),('cast-null',61)]:
 x=j(label);assert (x['lifecycle'],x['result'],x['javaKind'])==(2,value,0),(label,x)
assert (j('eager-3')['lifecycle'],j('eager-3')['javaKind'])==(3,6)
assert (j('cast-present')['lifecycle'],j('cast-present')['javaKind'])==(3,8)
x=j('cast-missing');assert (x['selector'],int(x['code']),int(x['detail']))==('0x427cfac5',4,castpc)
assert x['beforeStateRoot']==j('cast-missing-setup')['stateRoot'] and x['beforeEpoch']==0
oracle=json.loads((out/'fixture/cast-oracle.json').read_text());assert oracle=={'full-0':'R:61','full-1':'X:java.lang.ClassCastException','missing-0':'R:61','missing-1':'X:java.lang.NoClassDefFoundError'}
cap=j('fifth-capacity');assert cap['beforeStateRoot']==cap['afterStateRoot'] and cap['decoderCount']==4 and cap['gasUsed']==0
print(json.dumps({'distinctActualProcesses':len(allpids),'actualCheckpointHashes':cps,'javaCalls':len(gas),'maxJavaGas':max(gas),'gasSum':sum(gas),'originalMode3Attribution':'null checkcast at35 succeeds; refusal at38 is invokevirtual','nonnullCastPC':castpc,'castMissing':x,'castOracle':oracle,'eagerControls':{k:j(k) for k in ('eager-1','eager-2','eager-3','eager-super','eager-interface','cast-null','cast-present')}},indent=2))
