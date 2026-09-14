#!/usr/bin/env python3
"""Archive allowlisted asSubclass parent evidence; no original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];b=root/'build/java-diff-mc-class-as-subclass-parent-build2-fdb8b3155';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed_driver.go.txt')
for n in ('java-diff-mc-class-as-subclass-parent-final.log','java-diff-mc-class-as-subclass-parent-final-watchdog.json'):shutil.copy2(root/'build'/n,here/n)
def copy_tree(src,dst):
 dst.mkdir(parents=True,exist_ok=True)
 for f in src.rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(src)
  if 'state' in rel.parts or f.suffix not in ('.json','.bin','.log','.zip','.class','.txt'):continue
  q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
for label,dirname in (('focused','java-diff-mc-class-as-subclass-parent-focused2-fdb8b3155'),('integer','java-diff-mc-class-as-subclass-parent-integer2-fdb8b3155'),('retained','java-diff-mc-class-as-subclass-parent-retained2-fdb8b3155'),('official24','java-diff-mc-class-as-subclass-parent-official24b-fdb8b3155'),('q1','java-diff-mc-class-as-subclass-parent-q1b-fdb8b3155'),('official22-cap-observation','java-diff-mc-class-as-subclass-parent-official22a-fdb8b3155')):copy_tree(root/'build'/dirname,art/label)
files=[]
for f in sorted(here.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS'):continue
 rel=f.relative_to(here);low=str(rel).lower();assert 'minecraft_server' not in low and 'leveldb' not in low and 'chaindata' not in low and 'state' not in rel.parts
 files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(here/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n')
with tarfile.open(here/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(here/x['path'],arcname=x['path'],recursive=False)
 t.add(here/'archive-files.json',arcname='archive-files.json',recursive=False)
print('Archived',len(files)+1,'allowlisted files; no original JAR/class/page/LevelDB')
