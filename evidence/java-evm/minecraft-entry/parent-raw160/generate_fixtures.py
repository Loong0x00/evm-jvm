#!/usr/bin/env python3
"""Trusted Java8 raw-count/byte frontiers, including valid ignored attributes; no original input."""
from pathlib import Path
import json,hashlib,subprocess,sys,zipfile
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-raw160-fixtures-parent-')and not O.exists();O.mkdir();C=O/'classes';C.mkdir();S=O/'sources';S.mkdir();src=[H/'ParentRaw160.java']
for i in range(157):
 p=S/f'Raw160Filler{i:03d}.java';p.write_text(f'package generated;public final class Raw160Filler{i:03d}{{}}\n');src.append(p)
p=S/'EmptyCountMain.java';p.write_text('public final class EmptyCountMain{public static void main(String[]args){}}\n');src.append(p)
q=subprocess.run(list(map(str,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*src])),capture_output=True,text=True);(O/'javac.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr;q=subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',str(C),'ParentRaw160'],capture_output=True,text=True);(O/'stock-oracle.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
base=[C/'ParentRaw160.class',*sorted(C.glob('ParentRaw160$*.class'))];fill=sorted((C/'generated').glob('*.class'));assert len(base)==4 and len(fill)==157;cases={}
def emit(label,entry,items):
 d=O/'bundles'/label;d.mkdir(parents=True);rs=[]
 for i,(name,data)in enumerate(items):
  f=f'{i:03d}.class';(d/f).write_bytes(data);rs.append({'index':i,'binaryName':name,'file':f,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[label]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
def items(files):return[(p.relative_to(C).as_posix()[:-6],p.read_bytes())for p in files]
emit('ParentRaw160','ParentRaw160',items(base))
for n,label in[(150,'ParentRaw160Count150'),(151,'ParentRaw160Count151'),(160,'ParentRaw160Wide'),(161,'raw161')]:emit(label,'ParentRaw160',items(base+fill[:n-4]))
# A separate empty-main envelope has159 generated fillers, for genuine coordinator CREATE160.
extra=[]
for i in range(157,159):
 p=S/f'Raw160Filler{i:03d}.java';p.write_text(f'package generated;public final class Raw160Filler{i:03d}{{}}\n');extra.append(p)
subprocess.run(list(map(str,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*extra])),check=True)
# Rewrite this case's manifest/data in a new distinct label rather than replacing a prior run.
emit('Empty160Constructor','EmptyCountMain',items([C/'EmptyCountMain.class']+sorted((C/'generated').glob('*.class'))))
assert cases['Empty160Constructor']['rawCount']==160

def padded(b,want):
 # Only trusted javac output. Add an unknown class attribute with fresh UTF8 CP entry.
 u=lambda at,n:int.from_bytes(b[at:at+n],'big');count=u(8,2);at=10;i=1
 while i<count:
  tag=u(at,1);at+=1
  if tag==1:at+=2+u(at,2)
  elif tag in(7,8,16):at+=2
  elif tag in(3,4,9,10,11,12,18):at+=4
  elif tag in(5,6):at+=8;i+=1
  elif tag==15:at+=3
  else:raise AssertionError(tag)
  i+=1
 cpEnd=at;at+=6;at+=2+2*u(at,2)
 for _ in range(2):
  num=u(at,2);at+=2
  for _ in range(num):
   n=u(at+6,2);at+=8
   for _ in range(n):at+=6+u(at+2,4)
 attr=at;n=u(at,2);at+=2
 for _ in range(n):at+=6+u(at+2,4)
 assert at==len(b);name=b'Padding';cp=bytes([1])+len(name).to_bytes(2,'big')+name;growth=want-len(b)-len(cp)-6;assert growth>=0
 out=b[:8]+(count+1).to_bytes(2,'big')+b[10:cpEnd]+cp+b[cpEnd:attr]+(n+1).to_bytes(2,'big')+b[attr+2:]+count.to_bytes(2,'big')+growth.to_bytes(4,'big')+bytes(growth);assert len(out)==want;return out
exact=items(base+fill[:156]);remaining=1063930-sum(len(v)for _,v in exact)
for k in range(4):
 pos=len(base)+k;name,b=exact[pos];inc=min(262144-len(b),remaining);assert inc>=16;exact[pos]=(name,padded(b,len(b)+inc));remaining-=inc
assert remaining==0;emit('bytes-exact','ParentRaw160',exact)
# For exactly+1, change the last Padding attribute's declared payload length and append one byte.
name,b=exact[7];payload=len(b)-len(items(base+fill[:156])[7][1])-16;assert payload>=0;new=b[:len(b)-payload-4]+(payload+1).to_bytes(4,'big')+b[len(b)-payload:]+b'\0';assert len(new)==len(b)+1;over=exact.copy();over[7]=(name,new);emit('bytes-over','ParentRaw160',over);assert cases['bytes-exact']['rawBytes']==1063930 and cases['bytes-over']['rawBytes']==1063931
empty=cases['Empty160Constructor'];z=O/'empty160-constructor.zip'
with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_STORED)as archive:
 for r in empty['rawClasses']:
  info=zipfile.ZipInfo(r['binaryName']+'.class',(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED;archive.writestr(info,(O/'bundles/Empty160Constructor'/r['file']).read_bytes())
(O/'empty160-bindings.json').write_text(json.dumps([r['binaryName']+'.class'for r in empty['rawClasses']],indent=2)+'\n');(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'oracleNeverGuestExecutionInput':True,'validPaddingAttributeByteBoundary':True,'cases':cases},indent=2)+'\n');print(json.dumps({n:{'rawCount':v['rawCount'],'rawBytes':v['rawBytes']}for n,v in cases.items()},indent=2))
