#!/usr/bin/env python3
"""Archive independent P19 generated/original observations; never execution input."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
here=Path(__file__).resolve().parent;root=here.parents[3];art=here/'artifacts';art.mkdir(exist_ok=True)
build=root/'build/java-diff-mc-packed-float-grouped-scan-build-parent-668583cae';focused=root/'build/java-diff-mc-packed-float-grouped-scan-focused-parent-668583cae';full=root/'build/java-diff-mc-packed-float-grouped-scan-gate-parent-668583cae-full';probe=root/'build/java-diff-mc-packed-float-grouped-scan-probe-parent-668583cae';original=root/'build/java-diff-mc-packed-float-grouped-scan-original71-parent-668583cae';authorized=root/'build/java-diff-mc-packed-float-grouped-scan-original-authorized-parent-668583cae'
for src,dest in [(build/'pins.json',art/'parent-build-pins.json'),(build/'root-audit.json',art/'root-audit.json'),(focused/'summary.json',art/'focused-generated-gate-summary.json'),(full/'summary.json',art/'full-generated-gate-summary.json'),(probe/'summary.json',art/'direct-probe-summary.json'),(original/'official/durable-head.json',art/'original71-durable-head.json'),(original/'reports/official/resume-refusal.json',art/'original71-q1-refusal.json'),(original/'reports/official/slice-00000000000000001365.json',art/'last-successful-original71-receipt.json'),(original/'setup-process.json',art/'original71-setup-process.json'),(authorized/'main.go',here/'authorized-driver.go.txt'),(authorized/'authorization.json',art/'original71-authorization.json'),(build/'main.go',here/'canonical-driver.go.txt')]:assert src.is_file(),src;shutil.copyfile(src,dest)
for i in range(1,8):shutil.copyfile(root/f'build/java-diff-mc-packed-float-grouped-scan-dynamic{i}-parent-668583cae/summary.json',art/f'dynamic-{i}-summary.json')
for sub,files in [('engine',('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','MCEntryInterpreter.abi.json','build.js')),('coordinator',('MCEntryCoordinator.sol','MCEntryCoordinator.json','build.js'))]:
 dest=art/sub;dest.mkdir(exist_ok=True)
 for n in files:shutil.copyfile(build/sub/n,dest/n)
head=json.loads((original/'official/durable-head.json').read_text());assert head['jvmSteps']==1274589 and head['internalSteps']==83 and head['epoch']==1365 and head['lifecycle']==1
reports=sorted((original/'reports/official').glob('slice-*.json'));assert len(reports)==head['epoch'];index=[]
for n,p in enumerate(reports,1):
 b=p.read_bytes();r=json.loads(b);assert r['epoch']==n and r['checkpointSHA256'];index.append({'epoch':n,'reportSHA256':hashlib.sha256(b).hexdigest(),'checkpointSHA256':r['checkpointSHA256'],'gasUsed':r['gasUsed'],'elapsedMS':r['elapsedMS']})
(art/'original71-ordered-receipt-hashes.json').write_text(json.dumps(index,indent=2)+'\n')
cp=original/'official/checkpoints'/f"{head['checkpointSHA256']}.bin";blob=cp.read_bytes();assert hashlib.sha256(blob).hexdigest()==head['checkpointSHA256']
s=importlib.util.spec_from_file_location('frames',here/'checkpoint_frames.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);frames=m.inspect(blob);assert frames['javaSteps']==head['jvmSteps'] and frames['internalSteps']==head['internalSteps']
(art/'last-success-frames.json').write_text(json.dumps({'checkpointBytes':len(blob),**frames},indent=2)+'\n')
print(json.dumps({'focusedGateSeconds':json.loads((art/'focused-generated-gate-summary.json').read_text())['wholeGateSeconds'],'fullGateSeconds':json.loads((art/'full-generated-gate-summary.json').read_text())['wholeGateSeconds'],'originalReceiptHashes':len(index),'lastCheckpointSHA256':head['checkpointSHA256'],'lastCheckpointBytes':len(blob)}))
