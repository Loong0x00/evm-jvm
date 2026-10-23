#!/usr/bin/env python3
"""Parent generated SAM/bridge fixture plus exact150-input/256-class case."""
from pathlib import Path
import json,hashlib,os,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-arraylist-default-fixtures-parent-')and not O.exists();O.mkdir();C=O/'classes';C.mkdir();F=O/'filler-src';F.mkdir();J='/usr/lib/jvm/java-8-openjdk/bin/';src=[H/'ParentArrayListDefault.java']
# Four meaningful classes (main+3 nested);146 generated fillers reach raw150.
for i in range(149):
 p=F/f'ArrayListDefaultFiller{i:03d}.java';p.write_text(f'package generated; public final class ArrayListDefaultFiller{i:03d} {{ }}\n');src.append(p)
p=subprocess.run([J+'javac','-g:none','-source','8','-target','8','-d',str(C),*map(str,src)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'compile.log').write_text(p.stdout);assert p.returncode==0,p.stdout
p=subprocess.run([J+'java','-cp',str(C),'ParentArrayListDefault'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'java8-oracle.log').write_text(p.stdout);assert p.returncode==0,p.stdout
base=[C/'ParentArrayListDefault.class',*sorted(C.glob('ParentArrayListDefault$*.class'))];assert len(base)==1;cases={}
for name,files in [('ParentArrayListDefault',base),('ParentArrayListDefaultWide',base+sorted((C/'generated').glob('*.class')))]:
 D=O/'bundles'/name;D.mkdir(parents=True);rs=[]
 for i,p in enumerate(files):
  data=p.read_bytes();file=f'{i:03d}.class';(D/file).write_bytes(data);rs.append({'index':i,'binaryName':str(p.relative_to(C))[:-6],'file':file,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':'ParentArrayListDefault','rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
assert cases['ParentArrayListDefaultWide']['rawCount']==150 and cases['ParentArrayListDefaultWide']['rawBytes']<=1063930
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'stockJava8OracleExit':0,'oracleNeverExecutionInput':True,'cases':cases},indent=2)+'\n');print(json.dumps({k:{'rawCount':v['rawCount'],'rawBytes':v['rawBytes']}for k,v in cases.items()},indent=2))
