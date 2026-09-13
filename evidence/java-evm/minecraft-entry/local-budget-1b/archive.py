#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];a=here/'evidence.tar.gz';assert not a.exists();files=[]
dirs={'first':root/'build/java-diff-mc-local1b-8bbbd8b55','continue':root/'build/java-diff-mc-local1b-continue-8bbbd8b55','original20':root/'build/java-diff-mc-properties-parent-official20-c24d374bc','original21':root/'build/java-diff-mc-local1b-official21-8bbbd8b55'}
for label,d in dirs.items():
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(n in ('state','tmp','engine','coordinator','__pycache__') for n in rel.parts):continue
  ok=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or (f.suffix=='.bin' and 'checkpoints' in rel.parts)
  if ok:files.append((f,label+'/'+str(rel)))
with tarfile.open(a,'w:gz') as t:
 for f,n in files:t.add(f,arcname=n,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in files],indent=2)+'\n')
shutil.copy2(dirs['first']/'main.go',here/'executed_driver.go.txt')
shutil.copy2(dirs['first']/'pins.json',here/'pins.json')
for f in list((root/'build').glob('java-diff-mc-local1b*.log'))+list((root/'build').glob('java-diff-mc-local1b*-watchdog.json')):
 if f.is_file():shutil.copy2(f,here/f.name)
print('Archived',len(files),'metadata/checkpoint files, no original images/pages/JAR or LevelDB')
