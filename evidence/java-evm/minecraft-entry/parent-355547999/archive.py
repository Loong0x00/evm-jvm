#!/usr/bin/env python3
"""Archive allowlisted reentrant-lock parent evidence without original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];b=root/'build/java-diff-mc-reentrant-locks-parent-build1-355547999';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap-lock.log','javap-readwrite.log','candidate-source-verification.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed-driver.go.txt')
p=root/'build/java-diff-mc-reentrant-locks-parent-build1-355547999.monitor.json'
if p.is_file():shutil.copy2(p,here/p.name)
rows=[('locks','java-diff-mc-reentrant-locks-parent-gate1-355547999'),('cow-oom','java-diff-mc-reentrant-locks-parent-cow-oom1-355547999'),('new-instance','java-diff-mc-reentrant-locks-parent-newinstance1-355547999'),('new-instance-oom','java-diff-mc-reentrant-locks-parent-newinstance-oom1-355547999'),('new-instance-failures','java-diff-mc-reentrant-locks-parent-newinstance-failures1-355547999'),('focused','java-diff-mc-reentrant-locks-parent-focused1-355547999'),('integer','java-diff-mc-reentrant-locks-parent-integer1-355547999'),('retained','java-diff-mc-reentrant-locks-parent-retained1-355547999')]
for label,name in rows:
 d=art/label;d.mkdir(exist_ok=True);src=root/'build'/name
 for n in ('summary.json','canonical.log','checkpoint-states.json'):
  if (src/n).is_file():shutil.copy2(src/n,d/n)
 p=root/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,d/p.name)
for name in ('java-diff-mc-reentrant-locks-parent-official25a-355547999','java-diff-mc-reentrant-locks-parent-q1a-355547999'):
 p=root/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,here/p.name)
files=[]
for f in sorted(here.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS'):continue
 rel=f.relative_to(here);low=str(rel).lower();assert 'minecraft_server' not in low and 'leveldb' not in low and 'chaindata' not in low;assert f.suffix not in ('.class','.zip','.bin','.checkpoint')
 files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(here/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(here/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(here/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(here/x['path'],arcname=x['path'],recursive=False)
 t.add(here/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(here/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print('Archived',len(files)+2,'allowlisted files; no original JAR/class/page/checkpoint/LevelDB or Go binary')
