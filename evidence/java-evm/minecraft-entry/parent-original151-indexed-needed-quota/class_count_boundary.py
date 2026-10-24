#!/usr/bin/env python3
"""Generated-only EVM proof that the current LOCAL profile rejects a 151-class envelope."""
from pathlib import Path
import json,hashlib,subprocess,os,shutil
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-supplier-link-build-parent-p61-002';G=ROOT/'build/java-diff-mc-supplier-link-generated-parent-p61';O=ROOT/'build/java-diff-mc-p61-raw151-count-boundary-parent';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();S=O/'sources';S.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');sources=[]
for i in range(151):
 name='CountEntry'if i==0 else f'CountFiller{i:03d}';p=S/(name+'.java');p.write_text('public final class '+name+(' {public static void main(String[]a){}}\n'if i==0 else' {}\n'));sources.append(p)
subprocess.run(list(map(str,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources])),cwd=ROOT,env=env,check=True);rs=[];Q=O/'bundles/raw151';Q.mkdir(parents=True)
for i,source in enumerate(sources):
 b=(C/(source.stem+'.class')).read_bytes();fn=f'{i:03d}.class';(Q/fn).write_bytes(b);rs.append({'index':i,'binaryName':source.stem,'file':fn,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':{'raw151':{'entryClass':'CountEntry','rawCount':151,'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}}},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode=="parent-count-boundary"{if err=r.parentCountBoundary();err!=nil{os.Exit(writeFailure(r,err))};return}\nif mode == "parent-small" || mode == "parent-matrix" {',1);p.write_text(s);(D/'parent_count_boundary.go').write_text('''package main
import("fmt";"path/filepath")
func(r *runner)parentCountBoundary()error{row,e:=r.runRejection("generated-raw151","raw151","LinkError","1",65536,maxInternal);if e!=nil{return e};if len(row.ErrorArgs)<2||row.ErrorArgs[1]!="151"{return fmt.Errorf("wrong raw-count boundary argument")};r.report.Controls=append(r.report.Controls,row);r.report.Status="valid generated151-class input atomically refused by current150-class profile";return writeJSON(filepath.Join(r.reportDir,"parent-count-boundary.json"),r.report)}
''');subprocess.run(['go','build','-trimpath','-o',str(O/'driver'),'./'+str(D.relative_to(ROOT))],cwd=ROOT,env=env,check=True)
with(O/'boundary.log').open('w')as f:subprocess.run(list(map(str,[O/'driver','parent-count-boundary',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000'])),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
shutil.copy2(O/'controls/parent-count-boundary.json',H/'artifacts/generated-raw151-current150-boundary.json');print((H/'artifacts/generated-raw151-current150-boundary.json').read_text())
