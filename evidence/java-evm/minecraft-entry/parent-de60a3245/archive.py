#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
h=Path(__file__).resolve().parent;r=h.parents[3];b=r/'build/java-diff-mc-classcount30-parent-build1-de60a3245';a=h/'artifacts';a.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=a/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','source-verification.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):
 if (b/n).is_file():shutil.copy2(b/n,h/n)
shutil.copy2(b/'main.go',h/'executed-driver.go.txt')
# Generated parent gate.
g=r/'build/java-diff-mc-classcount30-parent-gate1-de60a3245'
shutil.copy2(g/'summary.json',a/'generated-gate-summary.json')
# Original30 metadata only; never archive original JAR/classes, Program checkpoints, binaries or LevelDB.
old='580a2c43e'
for src,dst in [
 (r/f'build/java-diff-mc-classcount30-parent-official30a-{old}/continuation/summary.json',a/'original30-initial-summary.json'),
 (r/f'build/java-diff-mc-classcount30-parent-continueq7a-{old}/summary.json',a/'original30-continue-summary.json'),
 (r/f'build/java-diff-mc-classcount30-parent-continueq7a-{old}/refusal.json',a/'original30-q7-refusal.json'),
 (r/f'build/java-diff-mc-classcount30-parent-q1a-{old}/summary.json',a/'original30-q1-summary.json'),
 (r/f'build/java-diff-mc-classcount30-parent-q1a-{old}/q1-refusal.json',a/'original30-q1-refusal.json'),
 (r/f'build/java-diff-mc-classcount30-parent-official30a-{old}/official/durable-head.json',a/'original30-durable-head.json'),
]:
 assert src.is_file(),src;shutil.copy2(src,dst)
for n in ('build1-de60a3245','gate1-de60a3245'):
 p=r/f'build/java-diff-mc-classcount30-parent-{n}.monitor.json';shutil.copy2(p,h/p.name)
for n in ('official30a','continueq7a','q1a'):
 p=r/f'build/java-diff-mc-classcount30-parent-{n}-{old}.monitor.json';shutil.copy2(p,h/p.name.replace(old,'de60a3245'))
files=[]
for f in sorted(h.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS') or f.suffix=='.pyc':continue
 rel=f.relative_to(h);assert f.suffix not in ('.class','.zip','.bin','.checkpoint');assert not any(x in str(rel).lower() for x in ('minecraft_server','leveldb','chaindata'));files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(h/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(h/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(h/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(h/x['path'],arcname=x['path'],recursive=False)
 t.add(h/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(h/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print(len(files)+2)
