#!/usr/bin/env python3
"""Allowlist parent evidence; excludes original JAR/class/pages and all LevelDB."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];archive=here/'parent-evidence.tar.gz';assert not archive.exists()
labels=('worlds','official18','official19','official20','dependencies','fixtures','gate')
files=[]
for label in labels:
 d=root/'build'/('java-diff-mc-classcount-parent-'+label+'-6748eb593');assert d.is_dir(),d
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(x in ('state','tmp','original-execution','__pycache__') for x in rel.parts):continue
  allowed=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or (f.suffix=='.bin' and 'checkpoints' in rel.parts)
  if label=='fixtures' and f.suffix in ('.java','.zip'):allowed=True # generated TEST only
  if allowed:files.append((f,label+'/'+rel.as_posix()))
with tarfile.open(archive,'w:gz') as t:
 for f,n in files:t.add(f,arcname=n,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in files],indent=2)+'\n')
build=root/'build/java-diff-mc-classcount-parent-build-6748eb593'
for kind in ('engine','coordinator'):shutil.copytree(build/kind,here/kind)
for name in ('engine-build.log','coordinator-build.log','pins.json'):shutil.copy2(build/name,here/name)
e=root/'build/java-diff-mc-classcount-parent-gate-6748eb593/original-execution/main.go';shutil.copy2(e,here/'executed_bounded_driver.go.txt')
g=root/'build/java-diff-mc-classcount-parent-gate-6748eb593';shutil.copy2(g/'gate.py',here/'executed_gate.py.txt')
for name in ('source-build.log','verify-generated.log','verify-original18.log','verify-original18-all.log'):shutil.copy2(g/name,here/name)
shutil.copy2(root/'build/java-diff-mc-classcount-parent-dependencies-6748eb593/official20-bindings.json',here/'official20-bindings.json')
for f in sorted((root/'build').glob('java-diff-mc-classcount-*.log'))+sorted((root/'build').glob('java-diff-mc-classcount-*-watchdog.json')):
 if f.is_file():shutil.copy2(f,here/f.name)
shutil.copy2(root/'build/java-diff-classcount-integration.log',here/'integration.log')
print('Archived',len(files),'allowlisted files')
