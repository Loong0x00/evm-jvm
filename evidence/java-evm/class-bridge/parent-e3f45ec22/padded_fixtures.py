#!/usr/bin/env python3
"""Trusted generated fixture construction ONLY: add an ignored class attribute."""
from pathlib import Path
import struct,sys,zipfile
base,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
b=(base/'BridgeAlpha.class').read_bytes()
def u2(b,p):return int.from_bytes(b[p:p+2],'big')
def u4(b,p):return int.from_bytes(b[p:p+4],'big')
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
cp_end=p
p+=6;p+=2+2*u2(b,p)
def attrs(p,n):
 for _ in range(n):p+=6+u4(b,p+2)
 return p
for _ in range(2):
 n=u2(b,p);p+=2
 for _ in range(n):na=u2(b,p+6);p=attrs(p+8,na)
class_attrs=p;n=u2(b,p);assert attrs(p+2,n)==len(b)
name=b'ParentPadding';extra=b'\x01'+struct.pack('>H',len(name))+name
for size in (4096,4097,8193,65536,65537):
 pad=size-len(b)-len(extra)-6;assert pad>=0
 raw=b[:8]+struct.pack('>H',count+1)+b[10:cp_end]+extra+b[cp_end:class_attrs]+struct.pack('>H',n+1)+b[class_attrs+2:]+struct.pack('>HI',count,pad)+bytes(pad)
 assert len(raw)==size
 d=out/str(size);d.mkdir(exist_ok=True);(d/'BridgeAlpha.class').write_bytes(raw)
 with zipfile.ZipFile(out/f'alpha-{size}.zip','w') as z:
  info=zipfile.ZipInfo('BridgeAlpha.class',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
