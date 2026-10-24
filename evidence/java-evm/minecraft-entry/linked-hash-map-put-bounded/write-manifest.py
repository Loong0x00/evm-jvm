#!/usr/bin/env python3
"""Manifest parent-corrected source/artifacts only; never include world DBs/checkpoints."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
pins=json.loads((root/'pins.json').read_text())
files=[]
for p in sorted(root.rglob('*')):
 if not p.is_file()or p.name=='candidate-manifest.json':continue
 q=p.relative_to(root)
 if any(x in('state','checkpoints','build','__pycache__','reports')or x.startswith('world-')for x in q.parts):continue
 files.append({'path':q.as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
out={'profile':pins['profile'],'workerCommit':'a6e059a42bd1d30d6180ba52fa83f487d0d1b4da','parentCorrectedArtifacts':True,'historicalWorkerManifest':'../parent-linked-hash-map-put/review/worker-candidate-manifest.json','authoritativeParentReview':'JAVA_EVM_MC_LINKED_HASH_MAP_PUT_PARENT_PREFLIGHT.md','bootstrapCount':127,'raw150ClassCount':277,'maxClassIndexAtRaw150':276,'bootstrapRoot':pins['bootstrapRoot'],'engineRuntimeSHA256':pins['engine']['runtimeSHA256'],'files':files}
(root/'candidate-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print('parent-corrected source/artifact manifest',len(files),'files')
