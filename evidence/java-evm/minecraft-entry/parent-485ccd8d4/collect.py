#!/usr/bin/env python3
"""Archive independent P17 generated/original observations; never execution input."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
here=Path(__file__).resolve().parent;root=here.parents[3];art=here/'artifacts';art.mkdir(exist_ok=True)
build=root/'build/java-diff-mc-packed-float-single-scan-build-parent-485ccd8d4';gate=root/'build/java-diff-mc-packed-float-single-scan-gate-parent-485ccd8d4';original=root/'build/java-diff-mc-packed-float-single-scan-original71-parent-485ccd8d4';authorized=root/'build/java-diff-mc-packed-float-single-scan-original-authorized-parent-485ccd8d4'
for src,dest in [(build/'pins.json',art/'parent-build-pins.json'),(build/'root-audit.json',art/'root-audit.json'),(gate/'summary.json',art/'generated-gate-summary.json'),(original/'official/durable-head.json',art/'original71-durable-head.json'),(original/'reports/official/resume-refusal.json',art/'original71-q1-refusal.json'),(original/'reports/official/slice-00000000000000001983.json',art/'last-successful-original71-receipt.json'),(original/'setup-process.json',art/'original71-setup-process.json'),(authorized/'main.go',here/'authorized-driver.go.txt'),(authorized/'authorization.json',art/'original71-authorization.json'),(build/'main.go',here/'canonical-driver.go.txt')]:assert src.is_file(),src;shutil.copyfile(src,dest)
for i in range(1,11):shutil.copyfile(root/f'build/java-diff-mc-packed-float-single-scan-dynamic{i}-parent-485ccd8d4/summary.json',art/f'dynamic-{i}-summary.json')
for sub,files in [('engine',('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','MCEntryInterpreter.abi.json','build.js')),('coordinator',('MCEntryCoordinator.sol','MCEntryCoordinator.json','build.js'))]:
 dest=art/sub;dest.mkdir(exist_ok=True)
 for n in files:shutil.copyfile(build/sub/n,dest/n)
head=json.loads((original/'official/durable-head.json').read_text());assert head['jvmSteps']==1274103 and head['internalSteps']==83 and head['epoch']==1983 and head['lifecycle']==1
reports=sorted((original/'reports/official').glob('slice-*.json'));assert len(reports)==head['epoch'];index=[]
for n,p in enumerate(reports,1):
 b=p.read_bytes();r=json.loads(b);assert r['epoch']==n and r['checkpointSHA256'];index.append({'epoch':n,'reportSHA256':hashlib.sha256(b).hexdigest(),'checkpointSHA256':r['checkpointSHA256'],'gasUsed':r['gasUsed'],'elapsedMS':r['elapsedMS']})
(art/'original71-ordered-receipt-hashes.json').write_text(json.dumps(index,indent=2)+'\n')
cp=original/'official/checkpoints'/f"{head['checkpointSHA256']}.bin";blob=cp.read_bytes();assert hashlib.sha256(blob).hexdigest()==head['checkpointSHA256']
s=importlib.util.spec_from_file_location('frames',here/'checkpoint_frames.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);frames=m.inspect(blob);assert frames['javaSteps']==head['jvmSteps'] and frames['internalSteps']==head['internalSteps']
(art/'last-success-frames.json').write_text(json.dumps({'checkpointBytes':len(blob),**frames},indent=2)+'\n')
print(json.dumps({'generatedGateSeconds':json.loads((art/'generated-gate-summary.json').read_text())['wholeGateSeconds'],'originalReceiptHashes':len(index),'lastCheckpointSHA256':head['checkpointSHA256'],'lastCheckpointBytes':len(blob)}))
