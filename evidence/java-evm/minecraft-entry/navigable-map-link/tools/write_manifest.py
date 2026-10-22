#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
files=[
 'PLAN-early.md','RESULT.md','build-pins.json','.gitignore',
 'bootstrap/Map.java','bootstrap/SortedMap.java','bootstrap/NavigableMap.java',
 'engine/MCEntryInterpreter.sol','engine/build.js','engine/MCEntryInterpreter.json',
 'coordinator/MCEntryCoordinator.sol','coordinator/build.js','coordinator/MCEntryCoordinator.json',
 'tools/canonical-driver.go','tools/checkpoint_frames.py','tools/generate_fixture.py','tools/generate_refusal_fixtures.py','tools/root_helper.py','tools/summarize_results.py','tools/verify_source.py','tools/write_manifest.py',
 'generatedfixtures/NavigableMap.javap.txt','generatedfixtures/java/util/NavigableMap.class','generatedfixtures/navigable-map-raw150.json','generatedfixtures/navigable-map-raw150.zip','generatedfixtures/raw-navigable-map-v1-different-image.zip','generatedfixtures/raw-navigable-map-v2-exact-image.zip','generatedfixtures/omitted-navigation-api-v1-untyped-call.zip','generatedfixtures/omitted-navigation-api-v2.zip',
 'generatedfixtures/refusal-fixtures.json',
 'results/root-commitment.json','results/selected-results.json',
 'results/receipts/omitted-api-v1-invokevirtual-not-a-negative.json','results/receipts/omitted-navigation-api-refusal.json','results/receipts/raw150-checkpoint-class-index-diagnostic.json','results/receipts/raw150-q4096-reopen.json','results/receipts/raw150-q4096-start.json','results/receipts/raw-reserved-different-image-refusal.json','results/receipts/raw-reserved-exact-refusal.json','results/receipts/small-q1-final-slice.json','results/receipts/small-q4096-final-slice.json','results/receipts/small-q7-final-slice.json'
]
rows={}
for name in files:
 p=root/name; b=p.read_bytes(); rows[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
manifest={'scope':'owned NavigableMap link-only implementation outputs; no original Minecraft input','sourceBaseCommit':'b4b50fe3bf0b9d70be99a64a3563431c24e49aec','sourceOnlyBaselineManifestSHA256':hashlib.sha256((root.parent/'navigable-map-source-base-p43/source-manifest.json').read_bytes()).hexdigest(),'files':rows}
(root/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f"manifest entries={len(rows)}")
