#!/usr/bin/env python3
"""Write the durable candidate manifest; excludes disposable/failed DB spam while retaining it on disk."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = set()
def add(path):
    path = Path(path)
    if path.is_file(): files.add(path.relative_to(ROOT).as_posix())
def add_glob(pattern):
    for path in ROOT.glob(pattern):
        if path.is_file(): add(path)
def add_tree(path):
    path = ROOT / path
    for f in path.rglob('*'):
        if f.is_file(): add(f)

for pattern in (
    'engine/*.sol','engine/*.js','engine/*.json','engine/*.hex',
    'coordinator/*.sol','coordinator/*.js','coordinator/*.json','coordinator/*.hex',
    'bootstrap/java/util/LinkedHashMap.java','bootstrap/java/util/LinkedHashMap.class',
    'classes/**/*','tests/java/*.java','tests/high-index-src/*.java',
    'tools/Go.txt','tools/canonical_driver.go','tools/root_helper.py','tools/verify_candidate.py','tools/write_manifest.py',
    '.gitignore','INHERITED_API_AUDIT.md','README.md','results/reproduction.md','results/pins-base-p48.json','results/source-base-p48-manifest.json',
    'results/pins.json','results/root-commitment.json','results/gate-summary.json','results/guest-api-refusal-results.json',
    'results/attempts.md','results/engine-build.log','results/coordinator-build.log','results/go-build.log','results/java-build.log','results/source-verification.log',
    'results/generated-empty-api.zip','results/generated-raw150-high-array.zip','results/fixtures/*.zip',
    'results/logs/**/*.log',
): add_glob(pattern)
for name in ('q1-empty','q7-empty','q16-empty','high-array-q16'):
    add_tree(f'results/{name}')
    add_tree(f'results/reports/{name}')
for name in ('LinkedHashMapPutDirect-q16','LinkedHashMapPutHashTyped-q16-clean','LinkedHashMapPutMapTyped-q16-clean',
             'LinkedHashMapMissingIntConstructor-q16-clean','LinkedHashMapUnsupportedInheritedApi-q16-clean',
             'LinkedHashMapUnsupportedEquals-q16-clean','LinkedHashMapUnsupportedHash-q16-clean',
             'LinkedHashMapUnsupportedClone-q16-clean','LinkedHashMapUnsupportedDefault-q16-clean','LinkedHashMapRawReplacement-q16-clean'):
    add_tree(f'results/refusals/{name}')
for name in ('LinkedHashMapPutDirect-q16','LinkedHashMapPutHashTyped-q16-clean','LinkedHashMapPutMapTyped-q16-clean',
             'LinkedHashMapMissingIntConstructor-q16-clean','LinkedHashMapUnsupportedInheritedApi-q16-clean',
             'LinkedHashMapUnsupportedEquals-q16-clean','LinkedHashMapUnsupportedHash-q16-clean',
             'LinkedHashMapUnsupportedClone-q16-clean','LinkedHashMapUnsupportedDefault-q16-clean','LinkedHashMapRawReplacement-q16-clean'):
    path = ROOT / f'results/refusals/reports/{name}'
    if path.exists():
        for f in path.glob('*refusal.json'): add(f)
for name in ('source-verification.log',):
    add(ROOT / 'results' / name)
records = {}
for rel in sorted(files):
    data = (ROOT / rel).read_bytes()
    records[rel] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest = {
  'profile': 'LinkedHashMap constructor-only P49 candidate; no acceptance claim',
  'baseCommit': 'c27816b557433e9ed6fdaa1a66464425896f6311',
  'baseEvidence': 'evidence/java-evm/minecraft-entry/linked-hash-map-source-base-p48/source-manifest.json',
  'included': 'source, pinned Solidity artifacts, reproducible Java fixtures, actual generated-EVM heads/receipts, and selected refusal witnesses',
  'excludedButPreservedOnDisk': 'failed/incomplete process attempts and their bulk observer receipts under results/refusals/reports/ and contaminated workspaces; see results/attempts.md',
  'files': records,
}
(ROOT / 'results/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'files':len(records),'bytes':sum(x['bytes'] for x in records.values()),'manifest':'results/manifest.json'},indent=2))
