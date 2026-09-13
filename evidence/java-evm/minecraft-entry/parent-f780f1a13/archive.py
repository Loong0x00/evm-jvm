#!/usr/bin/env python3
"""Archive an explicit metadata/checkpoint allowlist; never original payloads/DBs."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];archive=here/'parent-evidence.tar.gz';assert not archive.exists()
worlds={k:root/'build'/('java-diff-mc-entry-parent-arraycopy-'+k+'-f780f1a13') for k in ('repro','smoke','edges','official13','official13q7','official16','bootstrap','verifier')}
selected=[]
for label,d in worlds.items():
 assert d.is_dir(),d
 for f in sorted(d.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(d)
  if any(x in ('state','tmp','__pycache__') for x in rel.parts):continue
  allow=f.suffix in ('.json','.log','.checkpoint') or f.name=='STORE-FORMAT' or ('checkpoints' in rel.parts and f.suffix=='.bin')
  if label in ('smoke','edges','repro') and rel.as_posix()=='fixtures/arraycopy.zip':allow=True # generated TEST fixture only
  if allow:selected.append((f,label+'/'+rel.as_posix()))
with tarfile.open(archive,'w:gz') as t:
 for f,name in selected:t.add(f,arcname=name,recursive=False)
(here/'archive-files.json').write_text(json.dumps([{'path':n,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f,n in selected],indent=2)+'\n')
for name in ('advance.log','advance-watchdog.json','advance-monitor.log','verifier.log','verifier-watchdog.json','q7.log','q7-watchdog.json','q7-monitor.log','official16.log','official16-watchdog.json','official16-monitor.log'):
 shutil.copy2(root/'build'/('arraycopy-parent-'+name),here/name)
print('Archived',len(selected),'metadata/checkpoint/generated-fixture files; no original archive/class/resource-page/LevelDB payloads')
