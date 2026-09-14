#!/usr/bin/env python3
"""Archive allowlisted Class.forName parent evidence, never original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3]
# Successful source-built artifacts and logs.
b=root/'build/java-diff-mc-class-for-name-parent-build2-69ea5129d';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub in ('engine','coordinator'):
 d=art/sub;d.mkdir(exist_ok=True)
 for n in ('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js') if sub=='engine' else ('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js'):
  shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed_driver.go.txt')
# Successful whole process-tree gate.
for n in ('java-diff-mc-class-for-name-parent.log','java-diff-mc-class-for-name-parent-watchdog.json'):
 shutil.copy2(root/'build'/n,here/n)
# Generated gate: Java sources are already in this directory. Preserve generated
# classes/resources, canonical log, reports and opaque checkpoints, not LevelDB.
s=root/'build/java-diff-mc-class-for-name-parent-smoke2-69ea5129d';dst=art/'generated';dst.mkdir(exist_ok=True)
for dname in ('classes',):
 for f in (s/dname).rglob('*'):
  if f.is_file():q=dst/dname/f.relative_to(s/dname);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
for f in s.iterdir():
 if f.is_file() and f.suffix in ('.zip','.log','.json'):shutil.copy2(f,dst/f.name)
for d in s.iterdir():
 if not d.is_dir() or d.name in ('tmp','classes') or d.name.startswith('replace-'):continue
 for f in d.rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if 'state' in rel.parts or f.suffix not in ('.json','.bin','.log'):continue
  q=dst/'worlds'/d.name/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
shutil.copy2(s/'canonical.log',here/'verified-generated.json')
# Original22 receipts/checkpoints only; no source JAR, raw class/resource pages or DB.
for label,dirname in (('official22','java-diff-mc-class-for-name-parent-official22b-69ea5129d'),('q1','java-diff-mc-class-for-name-parent-q1b-69ea5129d')):
 src=root/'build'/dirname;dst=art/label;dst.mkdir(exist_ok=True)
 for f in src.rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(src)
  if 'state' in rel.parts:continue
  ok=f.suffix in ('.json','.bin','.log')
  if not ok:continue
  q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
# Reproducible inventory and tar. Explicitly scan names before write.
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
