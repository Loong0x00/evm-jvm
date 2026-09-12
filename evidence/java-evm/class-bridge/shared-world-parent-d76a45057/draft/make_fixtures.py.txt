#!/usr/bin/env python3
"""Build deterministic ZIPs from trusted generated javac8 fixture outputs only.
The padding edit is test-fixture construction and is never used by the EVM driver.
"""
from pathlib import Path
import struct,sys,zipfile
classes,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)

def u2(b,p): return int.from_bytes(b[p:p+2],'big')
def u4(b,p): return int.from_bytes(b[p:p+4],'big')
def padded(b,size):
    count=u2(b,8);p=10;i=1
    while i<count:
        t=b[p];p+=1
        if t==1:p+=2+u2(b,p)
        elif t in (3,4,9,10,11,12,17,18):p+=4
        elif t in (5,6):p+=8;i+=1
        elif t in (7,8,16,19,20):p+=2
        elif t==15:p+=3
        else:raise ValueError(t)
        i+=1
    cp_end=p;p+=6;p+=2+2*u2(b,p)
    def attrs(q,n):
        for _ in range(n):q+=6+u4(b,q+2)
        return q
    for _ in range(2):
        n=u2(b,p);p+=2
        for _ in range(n):na=u2(b,p+6);p=attrs(p+8,na)
    class_attrs=p;n=u2(b,p);assert attrs(p+2,n)==len(b)
    name=b'SharedWorldPadding';extra=b'\x01'+struct.pack('>H',len(name))+name
    pad=size-len(b)-len(extra)-6
    assert pad>=0
    raw=b[:8]+struct.pack('>H',count+1)+b[10:cp_end]+extra+b[cp_end:class_attrs]+struct.pack('>H',n+1)+b[class_attrs+2:]+struct.pack('>HI',count,pad)+bytes(pad)
    assert len(raw)==size
    return raw

def writezip(path, entries):
    with zipfile.ZipFile(path,'w') as z:
        for name,raw in entries:
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0;z.writestr(info,raw)

main=[(n+'.class',(classes/(n+'.class')).read_bytes()) for n in ('SharedEntry','SharedHelper')]
writezip(out/'shared-two.zip',main)
targets={'P1':4097,'P2':8193,'P3':16384,'P4':36862,'P4B':36863}
bound=[]
for n,size in targets.items():
    raw=padded((classes/(n+'.class')).read_bytes(),size)
    (out/(n+'.class')).write_bytes(raw);bound.append((n+'.class',raw))
# Two extra negative-only resources share this same accepted index: Alias bytes
# declare P1, while Unfinal is left in DI0 phase 1 by the driver.
boundary=bound+[('Alias.class',bound[0][1]),('Unfinal.class',(classes/'Unfinal.class').read_bytes())]
writezip(out/'boundary-seven.zip',boundary)
print('main',[(n,len(x)) for n,x in main])
print('boundary',[(n,len(x)) for n,x in bound])
