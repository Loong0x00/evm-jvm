#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
h=Path(__file__).resolve().parent;r=h.parents[3];b=r/'build/java-diff-mc-classcount28-parent-build1-b985a6add';a=h/'artifacts';a.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=a/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap-queue.log','candidate-source-verification.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,h/n)
shutil.copy2(b/'main.go',h/'executed-driver.go.txt')
for name in ('java-diff-mc-classcount28-parent-build1-b985a6add','java-diff-mc-classcount28-parent-gate1-b985a6add','java-diff-mc-classcount28-parent-official28a-a1e9e0f64','java-diff-mc-classcount28-parent-q1a-b985a6add'):
 p=r/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,h/p.name)
g=r/'build/java-diff-mc-classcount28-parent-gate1-b985a6add/summary.json'
if g.is_file():shutil.copy2(g,a/'generated-summary.json')
files=[]
for f in sorted(h.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS'):continue
 rel=f.relative_to(h);assert f.suffix not in ('.class','.zip','.bin','.checkpoint');assert not any(x in str(rel).lower() for x in ('minecraft_server','leveldb','chaindata'));files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(h/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(h/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(h/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(h/x['path'],arcname=x['path'],recursive=False)
 t.add(h/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(h/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print(len(files)+2)
