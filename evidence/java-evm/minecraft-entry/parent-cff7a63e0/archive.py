#!/usr/bin/env python3
"""Archive allowlisted cap25 parent evidence; never original class/page/checkpoint/world data."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3]
b=root/'build/java-diff-mc-classcount25-parent-build1-cff7a63e0';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed-driver.go.txt')
# Generated and retained gates: concise results, canonical verifier output and monitored envelope.
rows=[
 ('generated','java-diff-mc-classcount25-parent-gate2-cff7a63e0'),
 ('focused','java-diff-mc-classcount25-parent-focused1-cff7a63e0'),
 ('integer','java-diff-mc-classcount25-parent-integer1-cff7a63e0'),
 ('retained','java-diff-mc-classcount25-parent-retained1-cff7a63e0'),
]
for label,name in rows:
 d=art/label;d.mkdir(exist_ok=True);src=root/'build'/name
 for n in ('summary.json','canonical.log'):
  if (src/n).is_file():shutil.copy2(src/n,d/n)
 for suffix in ('.monitor.json','.whole.log'):
  p=root/'build'/(name+suffix)
  if p.is_file():shutil.copy2(p,d/p.name)
# Original execution archive is deliberately metadata-only. Receipts/checkpoints can
# contain the opaque original Program and are verified in place but never copied.
for name in ('java-diff-mc-classcount25-parent-official25a-cff7a63e0','java-diff-mc-classcount25-parent-q1a-cff7a63e0'):
 for suffix in ('.monitor.json','.whole.log'):
  p=root/'build'/(name+suffix)
  if p.is_file():shutil.copy2(p,here/p.name)
files=[]
for f in sorted(here.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS'):continue
 rel=f.relative_to(here);low=str(rel).lower()
 assert 'minecraft_server' not in low and 'leveldb' not in low and 'chaindata' not in low
 assert f.suffix not in ('.class','.zip','.bin','.checkpoint')
 files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(here/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n')
(here/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(here/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(here/x['path'],arcname=x['path'],recursive=False)
 t.add(here/'archive-files.json',arcname='archive-files.json',recursive=False)
 t.add(here/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print('Archived',len(files)+2,'allowlisted files; no original JAR/class/page/checkpoint/LevelDB or Go binary')
