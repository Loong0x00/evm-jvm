#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];a=here/'parent-evidence.tar.gz';assert not a.exists();files=[]
for label in ('smoke3','official22d','q1c'):
 d=root/'build'/('java-diff-mc-linked-hash-set-parent-'+label+'-7625023ff');assert d.is_dir()
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(n in ('state','tmp','classes','__pycache__') for n in rel.parts):continue
  ok=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or (f.suffix=='.bin' and 'checkpoints' in rel.parts)
  if label=='smoke3' and f.suffix=='.zip':ok=True
  if ok:files.append((f,label+'/'+str(rel)))
with tarfile.open(a,'w:gz') as t:
 for f,n in files:t.add(f,arcname=n,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in files],indent=2)+'\n')
b=root/'build/java-diff-mc-linked-hash-set-parent-build3-7625023ff'
for kind in ('engine','coordinator'):shutil.copytree(b/kind,here/kind)
for n in ('main.go','pins.json','bootstrap-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):shutil.copy2(b/n,here/('executed_driver.go.txt' if n=='main.go' else n))
for stem in ('java-diff-mc-linked-hash-set-parent','java-diff-mc-linked-hash-set-parent2','java-diff-mc-linked-hash-set-parent3','java-diff-mc-linked-hash-set-parent-final','java-diff-mc-linked-hash-set-parent-final2'):
 for suffix in ('.log','-watchdog.json','-monitor.log'):
  f=root/'build'/(stem+suffix)
  if f.is_file():shutil.copy2(f,here/f.name)
shutil.copy2(root/'build/java-diff-linked-hash-set-integration.log',here/'integration.log');shutil.copy2(root/'build/java-diff-mc-linked-hash-set-parent-smoke3-7625023ff/canonical.log',here/'verified-generated.json')
print('Archived',len(files),'allowlisted files; no original JAR/class/page/LevelDB')
