#!/usr/bin/env python3
"""Archive already-observed independent generated/original/diagnostic evidence; never execution input."""
from pathlib import Path
import hashlib, json, shutil, sys

here = Path(__file__).resolve().parent
root = here.parents[3]
art = here / 'artifacts'
art.mkdir(exist_ok=True)
build = root / 'build/java-diff-mc-math-cos-build-parent-cd8122975'
original = root / 'build/java-diff-mc-math-cos-original71-4p2b-parent-cd8122975'
authorized = root / 'build/java-diff-mc-math-cos-original-authorized-parent-cd8122975'
gate = root / 'build/java-diff-mc-math-cos-gate-parent-cd8122975'
for origin, dest in [(build/'pins.json', art/'parent-build-pins.json'),
                     (build/'root-audit.json', art/'root-audit.json'),
                     (gate/'summary.json', art/'generated-gate-summary.json'),
                     (original/'official/durable-head.json', art/'original71-durable-head.json'),
                     (original/'reports/official/resume-refusal.json', art/'original71-q1-refusal.json'),
                     (original/'reports/official/slice-00000000000000002083.json', art/'last-successful-original71-receipt.json'),
                     (original/'setup-process.json', art/'original71-setup-process.json'),
                     (authorized/'main.go', here/'authorized-driver.go.txt'),
                     (authorized/'authorization.json', art/'original71-authorization.json')]:
    assert origin.is_file(), origin
    shutil.copyfile(origin, dest)
for n in range(1, 12):
    shutil.copyfile(root/f'build/java-diff-mc-math-cos-dynamic{n}-parent-cd8122975/summary.json',
                    art/f'dynamic-{n}-summary.json')
for sub in ('engine','coordinator'):
    src = build/sub
    dest = art/sub
    dest.mkdir(exist_ok=True)
    for name in (('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','MCEntryInterpreter.abi.json','build.js') if sub == 'engine' else ('MCEntryCoordinator.sol','MCEntryCoordinator.json','build.js')):
        assert (src/name).is_file(), src/name
        shutil.copyfile(src/name, dest/name)
shutil.copyfile(build/'main.go', here/'canonical-driver.go.txt')
head=json.loads((original/'official/durable-head.json').read_text());assert head['jvmSteps']==1273130 and head['internalSteps']==81 and head['epoch']==2083 and head['lifecycle']==1
reports=sorted((original/'reports/official').glob('slice-*.json'));assert len(reports)==head['epoch'];ordered=[]
for n,p in enumerate(reports,1):
    b=p.read_bytes();d=json.loads(b);assert d['epoch']==n and d['checkpointSHA256'];ordered.append({'epoch':n,'reportSHA256':hashlib.sha256(b).hexdigest(),'checkpointSHA256':d['checkpointSHA256'],'gasUsed':d['gasUsed'],'elapsedMS':d['elapsedMS']})
(art/'original71-ordered-receipt-hashes.json').write_text(json.dumps(ordered,indent=2)+'\n')
cp=original/'official/checkpoints'/f"{head['checkpointSHA256']}.bin";assert hashlib.sha256(cp.read_bytes()).hexdigest()==head['checkpointSHA256']
import importlib.util
s=importlib.util.spec_from_file_location('frames',here/'checkpoint_frames.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
frames=m.inspect(cp.read_bytes());assert frames['javaSteps']==head['jvmSteps'] and frames['internalSteps']==81
(art/'last-success-frames.json').write_text(json.dumps({'checkpointBytes':cp.stat().st_size,**frames},indent=2)+'\n')
for name, world, drive in [('static-branch','java-diff-mc-post-cos-diagnostic-original71-parent-cd8122975','java-diff-mc-post-cos-symbol-diagnostic-parent-cd8122975'),('virtual-symbol','java-diff-mc-post-cos-virtual-diagnostic-original71-parent-cd8122975','java-diff-mc-post-cos-virtual-symbol-diagnostic-parent-cd8122975')]:
    w=root/'build'/world
    b=root/'build'/drive
    shutil.copyfile(w/'official/durable-head.json',art/f'{name}-diagnostic-head.json')
    shutil.copyfile(w/'reports/official/resume-refusal.json',art/f'{name}-diagnostic-refusal.json')
    shutil.copyfile(b/'pins.json',art/f'{name}-diagnostic-pins.json')
print(json.dumps({'generatedGateSeconds':json.loads((art/'generated-gate-summary.json').read_text())['wholeGateSeconds'],'originalVerifiedReportHashes':len(ordered),'lastCheckpointSHA256':head['checkpointSHA256'],'lastCheckpointBytes':cp.stat().st_size,'diagnosticWorlds':2}))
