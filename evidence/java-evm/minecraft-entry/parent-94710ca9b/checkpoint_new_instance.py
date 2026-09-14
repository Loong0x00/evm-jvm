#!/usr/bin/env python3
"""Read-only proof of q1 initialization/retry and constructor UNINIT checkpoints."""
from pathlib import Path
import hashlib,json,sys
world=Path(sys.argv[1]);reports=Path(sys.argv[2]);out=Path(sys.argv[3]);rows=[]
def inspect(b):
 at=280
 def data(n):
  nonlocal at
  assert 0<=n<=len(b)-at;r=b[at:at+n];at+=n;return r
 def u(n):return int.from_bytes(data(n),'big')
 assert data(4)==b'MR01'; lifecycle=u(1);u(4);u(1);u(4);jvm=u(8);internal=u(8);assert u(1)==1;data(32);data(u(2));data(u(2));data(u(1)*4)
 count=u(2);assert count<=96;states=[]
 for ci in range(count):
  state=u(1);started=u(1);n=u(2);values=[]
  for _ in range(n):values.append({'field':u(2),'kind':(v:=u(32))>>64,'payload':v&((1<<64)-1)})
  if state or started:states.append({'class':ci,'state':state,'started':started,'values':values})
 depth=u(2);assert depth<=128;frames=[]
 for _ in range(depth):
  c,m,pc,callpc,flags,this,sp=u(2),u(2),u(4),u(32),u(1),u(4),u(2);stack=[]
  for _ in range(sp):v=u(32);stack.append({'kind':v>>64,'payload':v&((1<<64)-1)})
  lc=u(2);bitmap=data((lc+7)//8);locals=[]
  for i in range(lc):
   v=u(32);locals.append({'initialized':bool(bitmap[i//8]&(1<<(i&7))),'kind':v>>64,'payload':v&((1<<64)-1)})
  frames.append({'class':c,'method':m,'pc':pc,'callPC':hex(callpc),'flags':flags,'this':this,'stack':stack,'locals':locals})
 return {'sha256':hashlib.sha256(b).hexdigest(),'lifecycle':lifecycle,'jvm':jvm,'internal':internal,'states':states,'frames':frames}
for epoch in range(1,65):
 r=json.loads((reports/f'slice-{epoch:020d}.json').read_text());cp=world/'checkpoints'/(r['checkpointSHA256']+'.bin');x=inspect(cp.read_bytes());assert x['sha256']==r['checkpointSHA256'] and x['jvm']==epoch
 target=next((s for s in x['states'] if s['class']==1),None);uninit=[]
 for fi,f in enumerate(x['frames']):
  for area in ('stack','locals'):
   for slot,v in enumerate(f[area]):
    if v.get('initialized',True) and v['kind']==3:uninit.append({'frame':fi,'area':area,'slot':slot,'handle':v['payload']})
 if (target and target['state']==1) or uninit:
  rows.append({'epoch':epoch,'target':target,'frames':[{k:f[k] for k in ('class','method','pc','callPC','flags','this')} for f in x['frames']],'uninitializedAliases':uninit})
assert any(r['target']['state']==1 and any(f['flags']==2 and f['class']==1 for f in r['frames']) for r in rows)
assert any(r['target']['started']==1 and any((f['flags']&17)==17 and f['class']==1 for f in r['frames']) for r in rows)
construct=[r for r in rows if r['uninitializedAliases'] and any((f['flags']&20)==20 and f['class']==1 and f['this']!=0 for f in r['frames'])];assert len(construct)>=2
for r in construct:
 handles={x['handle'] for x in r['uninitializedAliases']};assert any(f['this'] in handles for f in r['frames'] if (f['flags']&20)==20 and f['class']==1)
last_sha=json.loads((world/'durable-head.json').read_text())['checkpointSHA256'];last=inspect((world/'checkpoints'/(last_sha+'.bin')).read_bytes());target=next(s for s in last['states'] if s['class']==1);assert target['state']==2 and target['started']==1;values={v['field']:v['payload'] for v in target['values']};assert values=={0:1,1:2}
result={'scope':'read-only checkpoint transport metadata; no execution authority','pendingInitializationObserved':True,'initializerFrameObserved':True,'constructorUninitializedAliasObserved':True,'constructorCheckpointCount':len(construct),'interesting':rows,'terminalTargetStatics':values};out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('pendingInitializationObserved','initializerFrameObserved','constructorUninitializedAliasObserved','constructorCheckpointCount','terminalTargetStatics')},indent=2))
