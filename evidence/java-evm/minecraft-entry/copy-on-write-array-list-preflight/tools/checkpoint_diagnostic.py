#!/usr/bin/env python3
"""Read-only checkpoint metadata diagnostic; never a Java execution authority."""
import hashlib,json,sys
from pathlib import Path

def inspect(blob):
    assert 280 < len(blob) <= 1048576
    at=280
    def data(n):
        nonlocal at
        assert 0 <= n <= len(blob)-at
        value=blob[at:at+n]; at+=n; return value
    def u(n): return int.from_bytes(data(n),'big')
    assert data(4)==b'MR01'
    lifecycle=u(1); result=u(4); kind=u(1); ref=u(4); jvm=u(8); internal=u(8)
    assert u(1)==1
    commitment=data(32).hex(); entry_class=data(u(2)).decode(); entry=data(u(2)).decode()
    assert u(1)==0
    classes=u(2); assert classes<=100
    states=[]
    for i in range(classes):
        state=u(1); started=u(1); count=u(2)
        values=[{'fieldIndex':u(2),'packedValue':hex(u(32))} for _ in range(count)]
        if state or started: states.append({'classIndex':i,'state':state,'initializerStarted':started,'staticFields':count,'staticValues':values})
    depth=u(2); assert depth<=128; frames=[]
    for _ in range(depth):
        c,m,pc,callpc,flags,receiver,sp=u(2),u(2),u(4),u(32),u(1),u(4),u(2)
        data(sp*32); locals_count=u(2); data((locals_count+7)//8+locals_count*32)
        frames.append({'classIndex':c,'methodIndex':m,'pc':pc,'callPC':hex(callpc),'flags':flags,'receiver':receiver,'stackSize':sp,'locals':locals_count})
    return {'checkpointSHA256':hashlib.sha256(blob).hexdigest(),'lifecycle':lifecycle,'result':result,'javaKind':kind,'javaRef':ref,'javaSteps':jvm,'internalSteps':internal,'entryClass':entry_class,'entryMethod':entry,'argsCommitment':commitment,'classCount':classes,'initialization':states,'frames':frames,'scope':'diagnostic transport metadata only; no execution authority or evaluation'}

if __name__=='__main__': print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()),indent=2))
