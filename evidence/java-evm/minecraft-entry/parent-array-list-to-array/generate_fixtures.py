#!/usr/bin/env python3
"""Parent generated SAM/bridge fixture plus exact150-input/256-class case."""
from pathlib import Path
import json,hashlib,os,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-arraylist-to-array-fixtures-parent-')and not O.exists();O.mkdir();C=O/'classes';C.mkdir();F=O/'filler-src';F.mkdir();J='/usr/lib/jvm/java-8-openjdk/bin/';src=[H/'ParentArrayListTypedArray.java']
# Four meaningful classes (main+3 nested);146 generated fillers reach raw150.
for i in range(148):
 p=F/f'ArrayListToArrayFiller{i:03d}.java';p.write_text(f'package generated; public final class ArrayListToArrayFiller{i:03d} {{ }}\n');src.append(p)
p=subprocess.run([J+'javac','-g:none','-source','8','-target','8','-d',str(C),*map(str,src)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'compile.log').write_text(p.stdout);assert p.returncode==0,p.stdout
p=subprocess.run([J+'java','-cp',str(C),'ParentArrayListTypedArray'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'java8-oracle.log').write_text(p.stdout);assert p.returncode==0,p.stdout
base=[C/'ParentArrayListTypedArray.class',*sorted(C.glob('ParentArrayListTypedArray$*.class'))];assert len(base)==2;cases={}
for name,files in [('ParentArrayListTypedArray',base),('ParentArrayListTypedArrayWide',base+sorted((C/'generated').glob('*.class')))]:
 D=O/'bundles'/name;D.mkdir(parents=True);rs=[]
 for i,p in enumerate(files):
  data=p.read_bytes();file=f'{i:03d}.class';(D/file).write_bytes(data);rs.append({'index':i,'binaryName':str(p.relative_to(C))[:-6],'file':file,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':'ParentArrayListTypedArray','rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
assert cases['ParentArrayListTypedArrayWide']['rawCount']==150 and cases['ParentArrayListTypedArrayWide']['rawBytes']<=1063930
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'stockJava8OracleExit':0,'oracleNeverExecutionInput':True,'cases':cases},indent=2)+'\n');print(json.dumps({k:{'rawCount':v['rawCount'],'rawBytes':v['rawBytes']}for k,v in cases.items()},indent=2))
