#!/usr/bin/env python3
"""Archive allowlisted newInstance parent evidence without original payload/state."""
from pathlib import Path
import hashlib,json,shutil,tarfile
here=Path(__file__).resolve().parent;root=here.parents[3];b=root/'build/java-diff-mc-class-new-instance-parent-build1-94710ca9b';art=here/'artifacts';art.mkdir(exist_ok=True)
for sub,names in {'engine':('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.abi.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','build.js'),'coordinator':('MCEntryCoordinator.sol','MCEntryCoordinator.json','MCEntryCoordinator.abi.json','MCEntryCoordinator.runtime.hex','MCEntryCoordinator.init.hex','build.js')}.items():
 d=art/sub;d.mkdir(exist_ok=True)
 for n in names:shutil.copy2(b/sub/n,d/n)
for n in ('pins.json','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','strip-platform.log'):
 if (b/n).is_file():shutil.copy2(b/n,here/n)
shutil.copy2(b/'main.go',here/'executed-driver.go.txt')
# Build envelope.
p=root/'build/java-diff-mc-class-new-instance-parent-build1-94710ca9b.monitor.json'
if p.is_file():shutil.copy2(p,here/p.name)
# Generated and retained gates: results/canonical logs/diagnostics plus monitor only.
rows=[('new-instance','java-diff-mc-class-new-instance-parent-gate1-94710ca9b'),('oom','java-diff-mc-class-new-instance-parent-oom1-94710ca9b'),('failures','java-diff-mc-class-new-instance-parent-failures1-94710ca9b'),('focused','java-diff-mc-class-new-instance-parent-focused1-94710ca9b'),('integer','java-diff-mc-class-new-instance-parent-integer1-94710ca9b'),('retained','java-diff-mc-class-new-instance-parent-retained1-94710ca9b')]
for label,name in rows:
 d=art/label;d.mkdir(exist_ok=True);src=root/'build'/name
 for n in ('summary.json','canonical.log','checkpoint-states.json'):
  if (src/n).is_file():shutil.copy2(src/n,d/n)
 p=root/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,d/p.name)
# Original worlds were verified in place. Archive only concise derived metadata/monitors;
# raw receipts and checkpoint ABI can contain the original Program and are excluded.
for name in ('java-diff-mc-class-new-instance-parent-official25a-94710ca9b','java-diff-mc-class-new-instance-parent-q1a-94710ca9b'):
 p=root/'build'/(name+'.monitor.json')
 if p.is_file():shutil.copy2(p,here/p.name)
files=[]
for f in sorted(here.rglob('*')):
 if not f.is_file() or f.name in ('parent-evidence.tar.gz','archive-files.json','SHA256SUMS'):continue
 rel=f.relative_to(here);low=str(rel).lower();assert 'minecraft_server' not in low and 'leveldb' not in low and 'chaindata' not in low;assert f.suffix not in ('.class','.zip','.bin','.checkpoint')
 files.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(here/'archive-files.json').write_text(json.dumps(files,indent=2)+'\n');(here/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
with tarfile.open(here/'parent-evidence.tar.gz','w:gz') as t:
 for x in files:t.add(here/x['path'],arcname=x['path'],recursive=False)
 t.add(here/'archive-files.json',arcname='archive-files.json',recursive=False);t.add(here/'SHA256SUMS',arcname='SHA256SUMS',recursive=False)
print('Archived',len(files)+2,'allowlisted files; no original JAR/class/page/checkpoint/LevelDB or Go binary')
