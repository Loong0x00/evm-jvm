#!/usr/bin/env python3
"""Archive allowlisted cap26 parent evidence without original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];b=root/'build/java-diff-mc-classcount26-parent-build1-252da3536';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap-lock.log','candidate-source-verification.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed-driver.go.txt')
p=root/'build/java-diff-mc-classcount26-parent-build1-252da3536.monitor.json'
if p.is_file():shutil.copy2(p,here/p.name)
for label,name in [('classcount','java-diff-mc-classcount26-parent-gate1-252da3536'),('locks','java-diff-mc-classcount26-parent-lock1-252da3536')]:
 d=art/label;d.mkdir(exist_ok=True);src=root/'build'/name
 for n in ('summary.json','canonical.log'):
  if (src/n).is_file():shutil.copy2(src/n,d/n)
 p=root/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,d/p.name)
for name in ('java-diff-mc-classcount26-parent-official26a-252da3536','java-diff-mc-classcount26-parent-q1a-252da3536'):
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
