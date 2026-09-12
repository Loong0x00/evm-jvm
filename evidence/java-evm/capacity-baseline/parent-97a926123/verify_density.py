#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
out=Path(sys.argv[1]).resolve();report=json.loads((out/'report.json').read_text());zero='0x'+'0'*64;code7='0xf15d7343'+'0'*63+'7';pids=set();count=0
assert report['aggregate']==181969 and report['oracle']==23
sizes=[report['classes'][n]['bytes'] for n in ('BigPair','BigEntry','BigTwin')]
for p in out.glob('*.json'):
 j=json.loads(p.read_text())
 if 'pid' not in j:continue
 assert j['pid'] not in pids;pids.add(j['pid'])
 if j.get('command')!='java':continue
 count+=1;assert 0<j['gas']<=j['budget'] and j['budget'] in (100000000,1000000000)
 assert 0<j['wallSeconds']<=(30 if j['budget']==100000000 else 120)
 t=j['trace'];assert t['enabled'] and t['rootCalls']==1 and 0<t['maxEvmSeconds']<=j['wallSeconds']
 expected=[(i,off,min(4096,n-off)) for i,n in enumerate(sizes) for off in range(0,n,4096)]
 assert [(r['slot'],r['offset'],r['requested']) for r in t['reads']]==expected and len(expected)==47
 assert all(r['success'] and r['returned']==r['requested'] and 0<r['returned']<=4096 for r in t['reads'])
 assert sum(r['returned'] for r in t['reads'])==181969
 if 'error' in j:
  assert j['rawRevert']==code7 and j['budget']==100000000 and j['beforeRoot']==j['afterRoot'] and j['slice']['Schema']==0 and j['receiptRoot']==zero and j['logs']==0 and j['checkpointBytes']==0
 else:
  assert j['logs']==1 and j['slice']['Schema']==1 and j['afterRoot']==j['receiptRoot'] and 0<j['checkpointBytes']<=1048576
  w='world-q1' if p.name.startswith('q1-') else ('world-q7' if p.name.startswith('q7-') else 'world')
  b=(out/w/'checkpoints'/(j['slice']['CheckpointRoot'][2:]+'.checkpoint')).read_bytes();assert len(b)==j['checkpointBytes'] and hashlib.sha256(b).hexdigest()==j['checkpointSHA256']
ordinary=report['ordinary'];assert ordinary['gas']==74874471 and ordinary['head']['Java']['Epoch']==0
boundary=report['boundary'];assert boundary['budget']==1000000000 and boundary['gas']==124505990 and boundary['slice']['Result']==23 and boundary['slice']['TotalJvmSteps']==20
q=report['ordinarySliced'];assert len(q['7'])==1 and q['7'][-1]['head']['Java']['Epoch']==0
assert len(q['1'])==2 and q['1'][0]['slice']['Epoch']==1 and q['1'][0]['slice']['TotalJvmSteps']==1 and q['1'][1]['head']['Java']['Epoch']==1
assert q['1retry']['head']==q['1'][1]['head'] and q['1pending']['head']==q['1'][0]['head']
res=q['1boundaryResume'];assert res['budget']==1000000000 and res['slice']['Result']==23 and res['slice']['Epoch']==2
for k in ('MachineStateRoot','VFSStateRoot','Result','TotalJvmSteps','TotalInternalSteps'):assert res['slice'][k]==boundary['slice'][k]
assert q['1boundaryTerminal']['head']==res['head'] and q['1boundaryTerminal']['checkpointSHA256']==res['checkpointSHA256']
print(json.dumps({'densityAggregate':181969,'processes':len(pids),'javaCalls':count,'ordinaryDirectGas':ordinary['gas'],'ordinaryRefusal':'LC0ControlError(7), NOT OOG','ordinaryQ7':'no published Java checkpoint','ordinaryQ1':'epoch1 survives repeated resume refusal','boundaryDirectGas':boundary['gas'],'boundaryResumeGas':res['gas'],'boundaryResult':23,'actualReadFragmentsPerJavaCall':47,'conclusion':'one large class ordinary positive does not establish universal feasibility of the enlarged fixed package'},indent=2))
