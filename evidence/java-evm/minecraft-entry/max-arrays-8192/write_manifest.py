#!/usr/bin/env python3
"""Refresh the P41 evidence-directory content manifest (excluding itself)."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
rows={}
for p in sorted(HERE.rglob('*')):
 if not p.is_file() or p.name=='source-manifest.json': continue
 rel=p.relative_to(HERE).as_posix(); b=p.read_bytes(); rows[rel]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
record={'schema':1,'profile':'MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192','sourceBaseCommit':'9456cf9ad7116f0436acaf53416c51f74d7f3428','sourceOnlyP39BaseManifest':'source-base-manifest.json','noOriginalInputs':True,'files':rows}
(HERE/'source-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'files':len(rows),'manifest':str(HERE/'source-manifest.json')},indent=2))
