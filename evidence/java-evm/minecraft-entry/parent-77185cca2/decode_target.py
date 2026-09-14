#!/usr/bin/env python3
"""Read-only checkpoint layout diagnostic: decode active loadClass String local."""
from pathlib import Path
import json,sys
w=Path(sys.argv[1]);h=json.loads((w/'durable-head.json').read_text());b=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();at=280
def data(n):
 global at
 r=b[at:at+n];assert len(r)==n;at+=n;return r
def u(n):return int.from_bytes(data(n),'big')
assert data(4)==b'MR01';data(1+4+1+4+8+8+1+32);data(u(2));data(u(2));assert u(1)==0;classes=u(2)
for _ in range(classes):data(2);data(u(2)*34)
depth=u(2);frames=[]
for _ in range(depth):
 c,m,pc=u(2),u(2),u(4);data(32+1+4);stack=[u(32) for _ in range(u(2))];n=u(2);bits=data((n+7)//8);loc=[u(32) for _ in range(n)];frames.append({'class':c,'method':m,'pc':pc,'stack':stack,'locals':loc})
next_h=u(4);data(2+2+4+4+4+2+4);heap={}
for _ in range(next_h):
 handle=u(4);meta=u(32);ci=u(2);rank=u(1);n=u(4);kind=1 if meta < 1<<255 else 2;heap[handle]={'kind':kind,'class':ci,'cells':[u(8 if kind==1 else 32) for _ in range(n)]}
f=frames[-1];assert f['class']==71 and f['method']==4 and f['pc']==1 and len(f['locals'])>=2;handle=f['locals'][1]&((1<<64)-1);obj=heap[handle];assert obj['kind']==2;backing=obj['cells'][0]&((1<<64)-1);arr=heap[backing];assert arr['kind']==1;name=''.join(chr(x) for x in arr['cells']);out={'checkpointSHA256':h['checkpointSHA256'],'frame':{'classIndex':f['class'],'methodIndex':f['method'],'pc':f['pc']},'stringHandle':handle,'binaryName':name};print(json.dumps(out,indent=2));assert name=='javax.servlet.Servlet'
