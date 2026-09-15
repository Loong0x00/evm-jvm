#!/usr/bin/env python3
"""Generate Java-8-only reachable ACC_ENUM flag fixtures; no original input."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir(); (out/'src').mkdir(); (out/'classes').mkdir()
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; java='/usr/lib/jvm/java-8-openjdk/bin/java'
def access_offset(b):
 assert b[:4]==b'\xca\xfe\xba\xbe'; i=10; count=int.from_bytes(b[8:10],'big'); j=1
 while j<count:
  tag=b[i]; i+=1
  if tag==1:i+=2+int.from_bytes(b[i:i+2],'big')
  elif tag in (3,4,9,10,11,12,18):i+=4
  elif tag in (5,6):i+=8;j+=1
  elif tag in (7,8,16,19,20):i+=2
  elif tag==15:i+=3
  else:raise ValueError(tag)
  j+=1
 return i
def compile_case(label,sources,entries,patches=()):
 d=out/'src'/label; c=out/'classes'/label; d.mkdir(); c.mkdir()
 for n,s in sources.items():(d/n).write_text(s)
 subprocess.run([javac,'-source','8','-target','8','-g:none','-d',str(c),*map(str,sorted(d.glob('*.java')))],check=True)
 for n,bits in patches:
  p=c/n; b=bytearray(p.read_bytes()); at=access_offset(b); before=int.from_bytes(b[at:at+2],'big'); b[at:at+2]=(before|bits).to_bytes(2,'big'); p.write_bytes(b)
  assert int.from_bytes(b[at:at+2],'big')==before|bits
 # The host JVM oracle is limited to unpatched ordinary Java source. Patched classfiles
 # are parser/link controls; the EVM alone supplies their observed terminal receipt.
 if not patches: subprocess.run([java,'-cp',str(c),entries[0][:-6]],check=True)
 z=out/(label+'.zip')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
  for n in entries:
   info=zipfile.ZipInfo(n,(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED;f.writestr(info,(c/n).read_bytes())
 flags={}
 for n in entries:
  b=(c/n).read_bytes();at=access_offset(b);flags[n]={'offset':at,'accessFlags':'0x%04x'%int.from_bytes(b[at:at+2],'big'),'sha256':hashlib.sha256(b).hexdigest()}
 r={'java8TESTOnly':True,'entries':entries,'bindingCount':len(entries),'zipSHA256':hashlib.sha256(z.read_bytes()).hexdigest(),'classFlags':flags,'totalClassBytes':sum((c/n).stat().st_size for n in entries)}
 (out/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n');return r
plain={'FlagMain.java':'public final class FlagMain { static int x; public static void main(String[] a) { x=new Flagged().touch(); if(x!=7) throw new Error(); } }\n','Flagged.java':'final class Flagged { int touch() { return 7; } }\n'}
rows={}
rows['ordinary']=compile_case('ordinary',plain,['FlagMain.class','Flagged.class'])
for label,bits in [('enum-marker',0x4000),('annotation',0x2000),('module',0x8000),('annotation-enum',0x6000),('module-enum',0xc000)]:
 rows[label]=compile_case(label,plain,['FlagMain.class','Flagged.class'],[('Flagged.class',bits)])
iface={'FlagMain.java':'public final class FlagMain implements FlagIface { public int touch(){return 7;} public static void main(String[] a) { int x=new FlagMain().touch(); if(x!=7) throw new Error(); } }\n','FlagIface.java':'interface FlagIface { int touch(); }\n'}
rows['interface-ordinary']=compile_case('interface-ordinary',iface,['FlagMain.class','FlagIface.class'])
for label,bits in [('interface-enum',0x4000),('interface-annotation',0x2000)]:
 rows[label]=compile_case(label,iface,['FlagMain.class','FlagIface.class'],[('FlagIface.class',bits)])
enum={'EnumMain.java':'public final class EnumMain { public static void main(String[] a) { if (TestLevel.values().length != 8) throw new Error(); } }\n','TestLevel.java':'public enum TestLevel { OFF, FATAL, ERROR, WARN, INFO, DEBUG, TRACE, ALL; }\n'}
rows['java8-enum']=compile_case('java8-enum',enum,['EnumMain.class','TestLevel.class'])
ann={'AnnotationMain.java':'public final class AnnotationMain implements Ann { public Class annotationType() { return Ann.class; } public static void main(String[] a) { if (new AnnotationMain().annotationType() == null) throw new Error(); } }\n','Ann.java':'public @interface Ann { }\n'}
rows['java8-annotation']=compile_case('java8-annotation',ann,['AnnotationMain.class','Ann.class'])
assert rows['java8-enum']['classFlags']['TestLevel.class']['accessFlags']=='0x4031'
assert rows['enum-marker']['classFlags']['Flagged.class']['accessFlags']=='0x4030'
assert rows['annotation']['classFlags']['Flagged.class']['accessFlags']=='0x2030'
assert rows['module']['classFlags']['Flagged.class']['accessFlags']=='0x8030'
assert rows['annotation-enum']['classFlags']['Flagged.class']['accessFlags']=='0x6030'
assert rows['module-enum']['classFlags']['Flagged.class']['accessFlags']=='0xc030'
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:{'flags':v['classFlags'],'bytes':v['totalClassBytes']} for k,v in rows.items()},indent=2))
