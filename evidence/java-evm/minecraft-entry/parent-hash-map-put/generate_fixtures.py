#!/usr/bin/env python3
"""Build parent-owned generated-only HashMap fixtures and read-only Java8 oracle."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-hash-map-put-fixtures-parent-') and not O.exists();O.mkdir();C=O/'classes';C.mkdir()
env=dict(os.environ,GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
J='/usr/lib/jvm/java-8-openjdk/bin/'
sources=[H/(n+'.java') for n in ('ParentMapPutSmall','ParentMapPutResize','ParentMapPutOracle')]
p=subprocess.run([J+'javac','-g:none','-source','8','-target','8','-d',str(C),*map(str,sources)],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'compile.log').write_text(p.stdout);assert p.returncode==0,p.stdout
p=subprocess.run([J+'java','-cp',str(C),'ParentMapPutOracle'],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'java8-oracle.log').write_text(p.stdout);assert p.returncode==0,p.stdout
assert p.stdout.splitlines()==['small:size=3,modCount=3,threshold=12,table=16,nodes=3','resize:size=32,modCount=32,threshold=48,table=64,nodes=32'],p.stdout
cases={}
for name in ('ParentMapPutSmall','ParentMapPutResize'):
 files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];bundle=O/'bundles'/name;bundle.mkdir(parents=True)
 rows=[]
 for i,p in enumerate(files):
  b=p.read_bytes();file=f'{i:03d}-{p.name}';(bundle/file).write_bytes(b);rows.append({'index':i,'binaryName':p.stem,'file':file,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 cases[name]={'entryClass':name,'rawCount':len(rows),'rawBytes':sum(r['bytes'] for r in rows),'rawClasses':rows}
manifest={'generatedOnly':True,'originalInputsRead':False,'hostOracleNotExecutionInput':True,'cases':cases,'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'oracleOutput':p.stdout if hasattr(p,'stdout') else (O/'java8-oracle.log').read_text()}
(O/'fixture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'cases':cases,'java8OracleExit':0},indent=2))
