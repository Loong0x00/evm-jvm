#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
h=Path(__file__).resolve().parent;r=h.parents[3];b=r/'build/java-diff-mc-enum-set-parent-build2-3ed302a92';a=h/'artifacts';a.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=a/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','source-verification.log','java8-enumset-build.log','javap-enumset.log','strip-enumset.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):
 if (b/n).is_file():shutil.copy2(b/n,h/n)
shutil.copy2(b/'main.go',h/'executed-driver.go.txt')
worlds=[('java-diff-mc-enum-set-parent-build2-3ed302a92',None),('java-diff-mc-enum-set-parent-gate2-3ed302a92','enumset-summary.json'),('java-diff-mc-enum-bootstrap-enumsetparent-enum2-3ed302a92','retained-enum-summary.json'),('java-diff-mc-enum-bootstrap-enumsetparent-oom2-3ed302a92','quota-summary.json'),('java-diff-mc-enum-bootstrap-enumsetparent-cap3-3ed302a92','retained-cap-summary.json'),('java-diff-mc-enum-bootstrap-enumsetparent-flag2-3ed302a92','retained-flag-summary.json'),('java-diff-mc-enum-set-parent-official29a-3ed302a92',None),('java-diff-mc-enum-set-parent-q1a-3ed302a92',None)]
for name,summary in worlds:
 p=r/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,h/p.name)
 p=r/'build'/name/'summary.json'
 if summary and p.is_file():shutil.copy2(p,a/summary)
files=[]
for f in sorted(h.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS') or f.suffix=='.pyc':continue
 rel=f.relative_to(h);assert f.suffix not in ('.class','.zip','.bin','.checkpoint');assert not any(x in str(rel).lower() for x in ('minecraft_server','leveldb','chaindata'));files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(h/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(h/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(h/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(h/x['path'],arcname=x['path'],recursive=False)
 t.add(h/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(h/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print(len(files)+2)
