#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
h=Path(__file__).resolve().parent;r=h.parents[3];b=r/'build/java-diff-mc-system-err-parent-build2-89928ece8';a=h/'artifacts';a.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=a/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','source-verification.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):
 if (b/n).is_file():shutil.copy2(b/n,h/n)
shutil.copy2(b/'main.go',h/'executed-driver.go.txt')
g=r/'build/java-diff-mc-system-err-gate-parent3-89928ece8';shutil.copy2(g/'summary.json',a/'generated-gate-summary.json')
o=r/'build/java-diff-mc-system-err-parent-official30b-89928ece8';c=r/'build/java-diff-mc-system-err-parent-continueq7c-89928ece8';q=r/'build/java-diff-mc-system-err-parent-q1b-89928ece8'
for src,dst in [(o/'continuation/summary.json',a/'original30-initial-summary.json'),(c/'summary.json',a/'original30-continue-summary.json'),(c/'refusal.json',a/'original30-q7-refusal.json'),(q/'summary.json',a/'original30-q1-summary.json'),(q/'q1-refusal.json',a/'original30-q1-refusal.json'),(o/'official/durable-head.json',a/'original30-durable-head.json')]:assert src.is_file(),src;shutil.copy2(src,dst)
for name in ('java-diff-mc-system-err-parent-build2-89928ece8','java-diff-mc-system-err-gate-parent3-89928ece8','java-diff-mc-system-err-parent-official30b-89928ece8','java-diff-mc-system-err-parent-continueq7c-89928ece8','java-diff-mc-system-err-parent-q1b-89928ece8'):
 p=r/'build'/(name+'.monitor.json');assert p.is_file(),p;shutil.copy2(p,h/p.name)
files=[]
for f in sorted(h.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS') or f.suffix=='.pyc':continue
 rel=f.relative_to(h);assert f.suffix not in ('.class','.zip','.bin','.checkpoint');assert not any(x in str(rel).lower() for x in ('minecraft_server','leveldb','chaindata'));files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(h/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(h/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(h/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(h/x['path'],arcname=x['path'],recursive=False)
 t.add(h/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(h/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print(len(files)+2)
