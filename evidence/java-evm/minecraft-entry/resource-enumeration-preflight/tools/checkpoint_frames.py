#!/usr/bin/env python3
"""READ-ONLY public checkpoint transport diagnostics; never execution/resume authority.
Layout is _encodeMachine in the pinned MCEntryInterpreter. No Java instruction,
class file or ZIP is parsed/evaluated. Resume uses the original opaque EVM blob.
"""
import hashlib,json,sys
from pathlib import Path
def inspect(b):
 assert 280<len(b)<=1048576
 at=280
 def data(n):
  nonlocal at
  assert 0<=n<=len(b)-at
  r=b[at:at+n];at+=n;return r
 def u(n):return int.from_bytes(data(n),'big')
 assert data(4)==b'MR01'
 lifecycle=u(1);result=u(4);kind=u(1);ref=u(4);jvm=u(8);internal=u(8);rootKind=u(1);assert rootKind==1;commit=data(32).hex()
 ec=data(u(2)).decode();method=data(u(2)).decode();argc=u(1);assert argc==0
 classes=u(2);assert classes<=85;states=[]
 for i in range(classes):
  state=u(1);started=u(1);n=u(2);values=[{'fieldIndex':u(2),'packedValue':hex(u(32))} for _ in range(n)]
  if state or started:states.append({'classIndex':i,'state':state,'initializerStarted':started,'staticFields':n,'staticValues':values})
 depth=u(2);assert depth<=128;frames=[]
 for _ in range(depth):
  c,m,pc,callpc,flags,receiver,sp=u(2),u(2),u(4),u(32),u(1),u(4),u(2);data(sp*32);locals=u(2);data((locals+7)//8+locals*32)
  frames.append({'classIndex':c,'methodIndex':m,'pc':pc,'callPC':hex(callpc),'flags':flags,'receiver':receiver,'stackSize':sp,'locals':locals})
 return {'checkpointSHA256':hashlib.sha256(b).hexdigest(),'lifecycle':lifecycle,'result':result,'javaKind':kind,'javaRef':ref,'javaSteps':jvm,'internalSteps':internal,'rootKind':rootKind,'argsCommitment':commit,'entryClass':ec,'entryMethod':method,'classCount':classes,'initialization':states,'frames':frames,'scope':'diagnostic transport metadata only; no execution authority or evaluation'}
if __name__=='__main__':print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()),indent=2))
