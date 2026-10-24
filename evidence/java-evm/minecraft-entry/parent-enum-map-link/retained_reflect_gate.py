#!/usr/bin/env python3
"""Reexecute the independent P53 dynamic-array/Poison/native controls on fresh P54 code."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-enum-map-link-build-parent-p58-002';O=ROOT/'build/java-diff-mc-enum-map-link-retained-reflect-parent-p58';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();D=O/'driver-src';shutil.copytree(ROOT/'build/java-diff-mc-enum-map-link-generated-parent-p58/driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
src=H.parent/'parent-reflect-array/ParentReflectReferenceArray.java';run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,src]);run('stock-java8',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',C,'ParentReflectReferenceArray']);name='ParentReflectReferenceArray';bundle=O/'bundles'/name;bundle.mkdir(parents=True);files=[C/(name+'.class'),*sorted(C.glob(name+'$*.class'))];assert len(files)==5;rs=[]
for i,p in enumerate(files):
 data=p.read_bytes();fn=f'{i:03d}.class';(bundle/fn).write_bytes(data);rs.append({'index':i,'binaryName':p.stem,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':{name:{'entryClass':name,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}}},indent=2)+'\n');p=D/'parent_gate.go';s=p.read_text().replace('ParentEnumMapLink',name).replace('quanta:=[]uint64{7,1}','quanta:=[]uint64{4096,65536}');p.write_text(s);run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);args=[O/'driver','parent-small',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'parent-retained-reflect','1000000000'];run('reflect-controls',args);run('reopen',[args[0],'reopen',*args[2:]]);(O/'summary.json').write_text(json.dumps({'status':'PASS','budget':1000000000,'freshP54Artifact':True,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
