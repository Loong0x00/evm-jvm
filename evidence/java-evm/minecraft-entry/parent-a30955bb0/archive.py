#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];a=here/'parent-evidence.tar.gz';assert not a.exists();files=[]
for label in ('smoke','official22','q1'):
 d=root/'build'/('java-diff-mc-privileged-action-parent-'+label+'-a30955bb0');assert d.is_dir()
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(n in ('state','tmp','classes','__pycache__') for n in rel.parts):continue
  ok=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or (f.suffix=='.bin' and 'checkpoints' in rel.parts)
  if label=='smoke' and f.suffix=='.zip':ok=True
  if ok:files.append((f,label+'/'+str(rel)))
with tarfile.open(a,'w:gz') as t:
 for f,n in files:t.add(f,arcname=n,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in files],indent=2)+'\n')
b=root/'build/java-diff-mc-privileged-action-parent-build-a30955bb0'
for kind in ('engine','coordinator'):shutil.copytree(b/kind,here/kind)
for n in ('main.go','pins.json','bootstrap-build.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):shutil.copy2(b/n,here/('executed_driver.go.txt' if n=='main.go' else n))
for suffix in ('.log','-watchdog.json','-monitor.log'):
 f=root/'build'/('java-diff-mc-privileged-action-parent'+suffix)
 if f.is_file():shutil.copy2(f,here/f.name)
shutil.copy2(root/'build/java-diff-privileged-action-integration.log',here/'integration.log')
shutil.copy2(root/'build/java-diff-mc-privileged-action-parent-smoke-a30955bb0/canonical.log',here/'verified-generated.json')
print('Archived',len(files),'metadata/checkpoint/generated files; no original JAR/class/pages/LevelDB')
