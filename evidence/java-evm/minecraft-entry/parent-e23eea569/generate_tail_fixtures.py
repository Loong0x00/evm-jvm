#!/usr/bin/env python3
"""Copy generated P5 controls and add generated Java8 packed-float tail controls."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-packed-float-bulk-u32-fixtures-') and not out.exists();src=root/'evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures';shutil.copytree(src,out);base=json.loads((out/'packed-array-oracle.json').read_text());classes=out/'oracle-classes';classes.mkdir();oracle=here.parent/'packed-float-bulk-u32/tools/RawFloatOracle.java';subprocess.run(['javac','--release','8','-d',classes,oracle],cwd=root,check=True);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
def sha(b):return hashlib.sha256(b).hexdigest()
for length in (1024,1025,1031):
 label=f'float-tail-{length}';zp=out/(label+'.zip');cp=out/(label+'-classes');cp.mkdir()
 with zipfile.ZipFile(out/'packed-array-oracle.zip') as a,zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_STORED) as z:
  assert set(a.namelist())==set(base['entries'])
  for name in a.namelist():
   data=a.read(name);needle=b'\x11\x04\x00'
   if length!=1024:assert data.count(needle)==1;data=data.replace(needle,b'\x11'+length.to_bytes(2,'big'),1)
   z.writestr(name,data);(cp/name).write_bytes(data)
 proc=subprocess.run(['java','-cp',str(cp)+os.pathsep+str(classes),'RawFloatOracle'],cwd=root,env=env,text=True,capture_output=True,check=True);values=[x.strip().lower() for x in proc.stdout.splitlines() if x.strip()];assert len(values)==length and values[:1024]==base['hostOutput'] and all(x=='00000000' for x in values[1024:]);
 with zipfile.ZipFile(zp) as z:entries={n:z.read(n) for n in z.namelist()}
 row={'entries':base['entries'],'bindingCount':base['bindingCount'],'bootstrapCount':base['bootstrapCount'],'totalClassBytes':sum(map(len,entries.values())),'classBytes':{n:len(v) for n,v in entries.items()},'classSHA256':{n:sha(v) for n,v in entries.items()},'zipSHA256':sha(zp.read_bytes()),'java8HostOracle':True,'tailLength':length,'hostOutput':values};(out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({'generatedOnly':True,'tailLengths':[1024,1025,1031],'fixtureFiles':len(list(out.iterdir()))}))
