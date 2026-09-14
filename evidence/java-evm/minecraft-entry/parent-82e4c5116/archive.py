#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];a=here/'parent-evidence.tar.gz';assert not a.exists();files=[]
for label in ('smoke3','official22c','q1c'):
 d=root/'build'/('java-diff-mc-boolean-parent-'+label+'-82e4c5116');assert d.is_dir()
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
b=root/'build/java-diff-mc-boolean-parent-build3-82e4c5116'
for kind in ('engine','coordinator'):shutil.copytree(b/kind,here/kind)
for n in ('main.go','pins.json','strip-platform.log','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log'):shutil.copy2(b/n,here/('executed_driver.go.txt' if n=='main.go' else n))
for stem in ('java-diff-mc-boolean-parent','java-diff-mc-boolean-parent2','java-diff-mc-boolean-parent3'):
 for suffix in ('.log','-watchdog.json','-monitor.log'):
  f=root/'build'/(stem+suffix)
  if f.is_file():shutil.copy2(f,here/f.name)
shutil.copy2(root/'build/java-diff-boolean-integration.log',here/'integration.log');shutil.copy2(root/'build/java-diff-mc-boolean-parent-smoke3-82e4c5116/canonical.log',here/'verified-generated.json')
print('Archived',len(files),'allowlisted files; no original JAR/class/page/LevelDB')
