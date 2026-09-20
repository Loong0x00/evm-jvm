#!/usr/bin/env python3
"""Verify the exact dynamic-root image5 Throwable delta."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
here=Path(__file__).resolve().parent;stage=here.parent;root=here.parents[4];parent=stage.parent/'print-stream-print-char-preflight'
D='MC-THROWABLE-PRINT-001';IMAGE_SHA='e0eb622a2e3f9df3989fa4793860538be9b01183d0f0911e7b7c5df578520afd';IMAGE_KECCAK='ad47871098a702ae866f30543bb5adf023c9be6abad8e0e6233a4ca652b2db9d'
image=bytes.fromhex(''.join((stage/'bootstrap/java/lang/Throwable.class.hex').read_text().split()))
assert len(image)==657 and hashlib.sha256(image).hexdigest()==IMAGE_SHA and image[:8]==bytes.fromhex('cafebabe00000034')
source=(stage/'bootstrap/java/lang/Throwable.java').read_text()
for s in ('private String detailMessage;','private Throwable cause;','public Throwable() { super(); cause = this; }','public Throwable(String message) { super(); cause = this; detailMessage = message; }','public String getMessage() { return detailMessage; }','public Throwable getCause() { return cause == this ? null : cause; }','public void printStackTrace(java.io.PrintStream stream) { if (detailMessage != null) stream.println(detailMessage); }'):
 assert source.count(s)==1,s
# Exact classfile member signatures and method Code, parsed without host class loading.
def u2(b,p):return int.from_bytes(b[p:p+2],'big'),p+2
def u4(b,p):return int.from_bytes(b[p:p+4],'big'),p+4
p=8;n,p=u2(image,p);cp=[None]*n;i=1
while i<n:
 t=image[p];p+=1
 if t==1:z,p=u2(image,p);cp[i]=image[p:p+z];p+=z
 elif t in(3,4):p+=4
 elif t in(5,6):p+=8;i+=1
 elif t in(7,8,16,19,20):p+=2
 elif t in(9,10,11,12,18):p+=4
 elif t==15:p+=3
 else:raise AssertionError(t)
 i+=1
p+=6;k,p=u2(image,p);p+=2*k
def table():
 global p
 q,p=u2(image,p);out=[]
 for _ in range(q):
  a,p=u2(image,p);ni,p=u2(image,p);di,p=u2(image,p);ac,p=u2(image,p);attrs=[]
  for _ in range(ac):
   ai,p=u2(image,p);z,p=u4(image,p);attrs.append((cp[ai],image[p:p+z]));p+=z
  out.append((a,cp[ni],cp[di],attrs))
 return out
fields=table();methods=table();tail,p=u2(image,p)
for _ in range(tail): _,p=u2(image,p);z,p=u4(image,p);p+=z
assert p==len(image)
assert [(a,x,y) for a,x,y,_ in fields]==[(2,b'detailMessage',b'Ljava/lang/String;'),(2,b'cause',b'Ljava/lang/Throwable;')]
assert [(a,x,y) for a,x,y,_ in methods]==[(1,b'<init>',b'()V'),(1,b'<init>',b'(Ljava/lang/String;)V'),(1,b'getMessage',b'()Ljava/lang/String;'),(1,b'getCause',b'()Ljava/lang/Throwable;'),(1,b'printStackTrace',b'(Ljava/io/PrintStream;)V')]
def body(m):
 d=m[3][0][1];q=0;q+=4;z,q=u4(d,q);c=d[q:q+z];return c
assert [body(m).hex() for m in methods]==['2ab700012a2ab50002b1','2ab700012a2ab500022a2bb50003b1','2ab40003b0','2ab400022aa6000701a700072ab40002b0','2ab40003c6000b2b2ab40003b60004b1']
engine=(stage/'engine/MCEntryInterpreter.sol').read_text();pre=(stage/'engine/pre-layout-MCEntryInterpreter.sol').read_text()
for x in ('h[0] = keccak256(_bootstrapObject());','h[5] = keccak256(_bootstrapThrowable());','h[83] = DBOOT_PRINT_STREAM;','new bytes32[](91)','MAX_RAW_CLASSES = 38;','MAX_RAW_BYTES = 285489;','MAX_FRAMES = 128;','COMMIT_RESERVE = 25_000_000;','return keccak256(abi.encode(DBOOT, h));'):
 assert engine.count(x)==1,x
assert 'DBOOT_THROWABLE' not in engine and 'DBOOT_THROWABLE' not in pre
assert engine.count('bytes memory image = hex"'+image.hex()+'";')==1
assert engine.count('if (image.length == type(uint256).max) return _bootstrapThrowable();')==1
assert pre.count('return hex"'+image.hex()+'";')==1 and pre.count('image.length == type(uint256).max')==0
assert engine.count('unchecked { for (uint256')==pre.count('unchecked { for (uint256')==12
base=json.loads((parent/'root-commitment.json').read_text());record=json.loads((stage/'root-commitment.json').read_text())
assert record['domain']==D and record['bootstrapCount']==91 and record['keccak256'][5]==IMAGE_KECCAK
assert [i for i,(a,b) in enumerate(zip(base['keccak256'],record['keccak256'])) if a!=b]==[5] and record['keccak256'][0]==base['keccak256'][0]
pins=json.loads((stage/'build-pins.json').read_text());assert pins['domain']==D and pins['engine']=={'bytes':389150,'initSHA256':'c40a791d2f789590d9a873d2fac951fca3bedabbc0cb264524dd85a5215a8a27','runtimeSHA256':'e5b64de8b7fea6b62f6dc4f29a147c8325d7034ccffdd1e538a42376070b491a','runtimeKeccak256':'809bbcb06332ac40cc774390022348257438f6e043228e2d810ee44c126edd57'} and pins['runtimeCap']==393216 and pins['bootstrapSHA256']['Throwable']==IMAGE_SHA
assert pins['coordinator']['runtimeKeccak256']=='f33e60d4a3a7834f957e389ec8f182bc3f0be4a909ef989a223f20f026db199b'
assert pins['engine']['runtimeKeccak256'] in (stage/'coordinator/MCEntryCoordinator.sol').read_text() and pins['engine']['runtimeSHA256'] in (stage/'tools/Go.txt').read_text() and str(pins['engine']['bytes']) in (stage/'tools/Go.txt').read_text()
assert len(sys.argv)==3 and sys.argv[1]=='--built' and Path(sys.argv[2]).resolve()==stage/'build-pins.json'
print(json.dumps({'phase':'built','domain':D,'throwableBytes':len(image),'throwableSHA256':IMAGE_SHA,'throwableKeccak256':IMAGE_KECCAK,'bootstrapRoot':record['bootstrapRoot'],'dynamicLeaf':5,'runtimeBytes':pins['engine']['bytes'],'runtimeCap':393216,'layoutGuard':'fixed-length-unreachable-recursion'},indent=2))
