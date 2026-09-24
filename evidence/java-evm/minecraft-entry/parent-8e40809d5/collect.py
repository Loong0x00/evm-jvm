#!/usr/bin/env python3
"""Archive independent generated/original/diagnostic observations, never execution inputs."""
from pathlib import Path
import hashlib, importlib.util, json, shutil
here=Path(__file__).resolve().parent;root=here.parents[3];art=here/'artifacts';art.mkdir(exist_ok=True)
build=root/'build/java-diff-mc-object-hash-code-build-parent-8e40809d5'
original=root/'build/java-diff-mc-object-hash-code-original71-parent-8e40809d5'
authorized=root/'build/java-diff-mc-object-hash-code-original-authorized-parent-8e40809d5'
gate=root/'build/java-diff-mc-object-hash-code-gate-parent-8e40809d5'
diag=root/'build/java-diff-mc-post-object-hash-diagnostic-original71-parent-8e40809d5'
dbuild=root/'build/java-diff-mc-post-object-hash-virtual-symbol-diagnostic-parent-8e40809d5'
for src,dest in [(build/'pins.json',art/'parent-build-pins.json'),(build/'root-audit.json',art/'root-audit.json'),(gate/'summary.json',art/'generated-gate-summary.json'),(original/'official/durable-head.json',art/'original71-durable-head.json'),(original/'reports/official/resume-refusal.json',art/'original71-q1-refusal.json'),(original/'reports/official/slice-00000000000000002086.json',art/'last-successful-original71-receipt.json'),(original/'setup-process.json',art/'original71-setup-process.json'),(authorized/'main.go',here/'authorized-driver.go.txt'),(authorized/'authorization.json',art/'original71-authorization.json'),(diag/'official/durable-head.json',art/'virtual-symbol-diagnostic-head.json'),(diag/'reports/official/resume-refusal.json',art/'virtual-symbol-diagnostic-refusal.json'),(dbuild/'pins.json',art/'virtual-symbol-diagnostic-pins.json'),(build/'main.go',here/'canonical-driver.go.txt')]:
 assert src.is_file(),src;shutil.copyfile(src,dest)
for i in range(1,12):shutil.copyfile(root/f'build/java-diff-mc-object-hash-code-dynamic{i}-parent-8e40809d5/summary.json',art/f'dynamic-{i}-summary.json')
for sub,files in [('engine',('MCEntryInterpreter.sol','MCEntryInterpreter.json','MCEntryInterpreter.runtime.hex','MCEntryInterpreter.init.hex','MCEntryInterpreter.abi.json','build.js')),('coordinator',('MCEntryCoordinator.sol','MCEntryCoordinator.json','build.js'))]:
 dest=art/sub;dest.mkdir(exist_ok=True)
 for n in files:shutil.copyfile(build/sub/n,dest/n)
head=json.loads((original/'official/durable-head.json').read_text());assert head['jvmSteps']==1273147 and head['internalSteps']==81 and head['epoch']==2086 and head['lifecycle']==1
files=sorted((original/'reports/official').glob('slice-*.json'));assert len(files)==head['epoch'];index=[]
for n,p in enumerate(files,1):
 b=p.read_bytes();r=json.loads(b);assert r['epoch']==n and r['checkpointSHA256'];index.append({'epoch':n,'reportSHA256':hashlib.sha256(b).hexdigest(),'checkpointSHA256':r['checkpointSHA256'],'gasUsed':r['gasUsed'],'elapsedMS':r['elapsedMS']})
(art/'original71-ordered-receipt-hashes.json').write_text(json.dumps(index,indent=2)+'\n')
cp=original/'official/checkpoints'/f"{head['checkpointSHA256']}.bin";blob=cp.read_bytes();assert hashlib.sha256(blob).hexdigest()==head['checkpointSHA256']
s=importlib.util.spec_from_file_location('frames',here/'checkpoint_frames.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);frames=m.inspect(blob);assert frames['javaSteps']==head['jvmSteps'] and frames['internalSteps']==head['internalSteps']
(art/'last-success-frames.json').write_text(json.dumps({'checkpointBytes':len(blob),**frames},indent=2)+'\n')
print(json.dumps({'generatedGateSeconds':json.loads((art/'generated-gate-summary.json').read_text())['wholeGateSeconds'],'originalReceiptHashes':len(index),'lastCheckpointSHA256':head['checkpointSHA256'],'lastCheckpointBytes':len(blob)}))
