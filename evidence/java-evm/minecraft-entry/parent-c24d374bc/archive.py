#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];a=here/'parent-evidence.tar.gz';assert not a.exists();files=[]
for label in ('regression','regression2','smoke','official20','q1','reserved'):
 d=root/'build'/('java-diff-mc-properties-parent-'+label+'-c24d374bc');assert d.is_dir()
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(n in ('state','tmp','__pycache__') for n in rel.parts):continue
  ok=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or (f.suffix=='.bin' and 'checkpoints' in rel.parts)
  if label in ('regression','regression2','smoke','reserved') and f.suffix=='.zip':ok=True # generated TEST only
  if ok:files.append((f,label+'/'+str(rel)))
with tarfile.open(a,'w:gz') as t:
 for f,n in files:t.add(f,arcname=n,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in files],indent=2)+'\n')
b=root/'build/java-diff-mc-properties-parent-fixed-c24d374bc'
for kind in ('engine','coordinator','bootstrap'):shutil.copytree(b/kind,here/kind)
shutil.copy2(b/'pins.json',here/'pins.json');shutil.copy2(b/'main.go',here/'executed_bounded_driver.go.txt')
shutil.copy2(root/'build/java-diff-mc-properties-parent-q1-c24d374bc/main.go',here/'executed_smaller_driver.go.txt')
for mode in ('candidate','fixed'):
 b=root/'build'/('java-diff-mc-properties-parent-'+mode+'-c24d374bc')
 for n in ('bootstrap-build.log','engine-build.log','coordinator-build.log','pins.json'):shutil.copy2(b/n,here/(mode+'-'+n))
for f in list((root/'build').glob('java-diff-mc-properties-parent*.log'))+list((root/'build').glob('java-diff-mc-properties-parent*-watchdog.json')):
 if f.is_file():shutil.copy2(f,here/f.name)
shutil.copy2(root/'build/java-diff-properties-recovery.log',here/'recovery.log')
for label in ('regression2','smoke'):
 b=root/'build'/('java-diff-mc-properties-parent-'+label+'-c24d374bc');shutil.copy2(b/'summary.json',here/(label+'-summary.json'));shutil.copy2(b/'verify-canonical.log',here/(label+'-verified.json'))
shutil.copy2(root/'build/java-diff-mc-properties-parent-q1-c24d374bc/verified-receipts.json',here/'original20-verified.json')
print('Archived',len(files),'metadata/checkpoint/generated fixture files; no original images/pages/JAR or any LevelDB')
