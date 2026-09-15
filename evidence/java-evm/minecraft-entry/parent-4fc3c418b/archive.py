#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,tarfile
h=Path(__file__).resolve().parent
excluded={'parent-evidence.tar.gz','archive-files.json','SHA256SUMS'}
files=sorted(p for p in h.rglob('*') if p.is_file() and p.name not in excluded and '__pycache__' not in p.parts)
for p in files:
 q=str(p.relative_to(h));assert not q.endswith(('.class','.jar','.checkpoint','.bin')) and 'leveldb' not in q.lower() and '/official/' not in q and '/checkpoints/' not in q
manifest=[{'path':str(p.relative_to(h)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(h/'archive-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(h/'parent-evidence.tar.gz','w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(h)))
print(json.dumps({'files':len(files),'archiveBytes':(h/'parent-evidence.tar.gz').stat().st_size}))
