#!/usr/bin/env python3
"""Archive allowlisted Integer parent evidence; exclude original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];b=root/'build/java-diff-mc-integer-parent-build2-661331e3d';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed_driver.go.txt')
for n in ('java-diff-mc-integer-parent-final.log','java-diff-mc-integer-parent-final-watchdog.json'):shutil.copy2(root/'build'/n,here/n)
def copy_tree(src,dst):
 dst.mkdir(parents=True,exist_ok=True)
 for f in src.rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(src)
  if 'state' in rel.parts or f.suffix not in ('.json','.bin','.log','.zip','.class','.txt'):continue
  q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
for label,dirname in (('focused','java-diff-mc-integer-parent-focused2-661331e3d'),('retained','java-diff-mc-integer-parent-retained2-661331e3d'),('official22','java-diff-mc-integer-parent-official22b-661331e3d'),('q1','java-diff-mc-integer-parent-q1b-661331e3d')):copy_tree(root/'build'/dirname,art/label)
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
