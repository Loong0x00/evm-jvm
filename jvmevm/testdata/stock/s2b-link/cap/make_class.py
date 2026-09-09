#!/usr/bin/env python3
import struct, pathlib, hashlib
u1=lambda x:struct.pack('>B',x);u2=lambda x:struct.pack('>H',x);u4=lambda x:struct.pack('>I',x)
cp=[None]
def utf(s):
 b=s.encode();cp.append(u1(1)+u2(len(b))+b);return len(cp)-1
def clazz(i):cp.append(u1(7)+u2(i));return len(cp)-1
def nat(n,d):cp.append(u1(12)+u2(n)+u2(d));return len(cp)-1
def mref(c,n):cp.append(u1(10)+u2(c)+u2(n));return len(cp)-1
def integer(v):cp.append(u1(3)+struct.pack('>i',v));return len(cp)-1
UClass=utf('S2bValidCaps');UObj=utf('java/lang/Object');UInit=utf('<init>');UVoid=utf('()V');UInt=utf('()I');UCode=utf('Code');UStackMap=utf('StackMapTable');UHelper=utf('helper')
CClass=clazz(UClass);CObj=clazz(UObj);NInit=nat(UInit,UVoid);MObj=mref(CObj,NInit);NHelper=nat(UHelper,UInt);MHelper=mref(CClass,NHelper)
ints=[integer(1_000_000+i) for i in range(256)]
names=[utf(f'm{i}') for i in range(6)]+[utf('root')]+[utf(f'spare{i}') for i in range(23)]
def code_attr(stack,locals_,code,nested=b''):
 attrs=(u2(1)+u2(UStackMap)+u4(len(nested))+nested) if nested else u2(0)
 body=u2(stack)+u2(locals_)+u4(len(code))+code+u2(0)+attrs
 return u2(UCode)+u4(len(body))+body
def method(flags,name,desc,stack,locals_,code,nested=b''):return u2(flags)+u2(name)+u2(desc)+u2(1)+code_attr(stack,locals_,code,nested)
methods=[]
methods.append(method(0x0001,UInit,UVoid,1,1,b'\x2a\xb7'+u2(MObj)+b'\xb1'))
methods.append(method(0x000a,UHelper,UInt,1,0,b'\x03\xac'))
counts=[43,43,43,43,42,42];at=0;vis=[0x0008,0x000a,0x000c,0x0009,0x0008,0x000a]
for i,n in enumerate(counts):
 dead=b''
 for idx in ints[at:at+n]: dead+=(b'\x12'+u1(idx) if idx<=255 else b'\x13'+u2(idx))+b'\x57'
 target=3+len(dead);c=b'\xa7'+u2(target)+dead+b'\x03\xac';at+=n;assert len(c)<=256
 # JVM52 verifier frames: dead block at pc3, and branch target after it.
 sm=u2(2)+u1(3)+u1(251)+u2(target-4)
 methods.append(method(vis[i],names[i],UInt,1,0,c,sm))
c=(b'\xb8'+u2(MHelper)+b'\x57')*32+b'\x03\xac';methods.append(method(0x0009,names[6],UInt,1,0,c))
for i in range(23): methods.append(method(vis[i%len(vis)],names[7+i],UInt,1,0,b'\x03\xac'))
assert len(methods)==32 and at==256
out=u4(0xcafebabe)+u2(0)+u2(52)+u2(len(cp))+b''.join(cp[1:])+u2(0x0021)+u2(CClass)+u2(CObj)+u2(0)+u2(0)+u2(len(methods))+b''.join(methods)+u2(0)
p=pathlib.Path(__file__).parent/'classes'/'S2bValidCaps.class';p.parent.mkdir(exist_ok=True);p.write_bytes(out)
print(len(out),len(cp),hashlib.sha256(out).hexdigest(),counts)
