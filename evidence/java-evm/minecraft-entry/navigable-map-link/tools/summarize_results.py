#!/usr/bin/env python3
"""Collect selected durable receipts only; session DBs remain untracked intermediates."""
from pathlib import Path
import json, hashlib
root=Path(__file__).resolve().parents[1]; results=root/'results'; reports=results/'reports'
def load(p): return json.loads(Path(p).read_text())
small={}
for q in (1,7,4096):
 d=results/f'world-small-q{q}'; m=load(d/'durable-head.json'); rr=reports/f'world-small-q{q}'
 rows=[]
 for p in [rr/'start.json',*sorted(rr.glob('slice-*.json'))]:
  if p.exists():
   x=load(p); s=x.get('slice')
   if s: rows.append(s)
 last=rows[-1]
 small[str(q)]={'quantum':q,'epoch':m['epoch'],'lifecycle':m['lifecycle'],'outcome':m['outcome'],'result':m['result'],'totalJvmSteps':m['jvmSteps'],'totalInternalSteps':m['internalSteps'],'machineStateRoot':last['machineStateRoot'],'vfsStateRoot':last['vfsStateRoot'],'checkpointRoot':m['checkpointRoot'],'checkpointBytes':(d/'checkpoints'/f"{m['checkpointSHA256']}.bin").stat().st_size,'reopenedInSeparateProcess':load(reports/f'world-small-q{q}'/'world-report.json')['manifest']['stage']=='final-reopened','finalReopenPID':load(reports/f'world-small-q{q}'/'world-report.json')['finalReopenPID'],'physicalCounters':m['counters']}
assert len({x['machineStateRoot'] for x in small.values()})==1
assert len({x['vfsStateRoot'] for x in small.values()})==1
assert len({(x['totalJvmSteps'],x['totalInternalSteps']) for x in small.values()})==1
# Exact raw150 / derived257 / slot256 positive.
d=results/'world-q4096'; m=load(d/'durable-head.json'); rr=reports/'world-q4096'; cp=load(d/'checkpoint-diagnostic.json'); start=load(rr/'start.json'); reopen=load(rr/'world-report.json')
assert len(m['rawNames'])==150 and cp['classCount']==257 and cp['lifecycle']==2
assert m['lifecycle']==2 and m['outcome']==2 and m['result']==0
# Refusal receipts: exact same bytes raw collision; absent API invokeinterface.
def refusal(name):
 p=reports/name/'start-refusal.json'; x=load(p); return {'selector':x['selector'],'error':x['error'],'uint256Words':x['uint256Words'],'gas':x['gas'],'rootUnchanged':x['rootUnchanged'],'durableHeadUnchanged':x['durableHeadUnchanged'],'revertHex':x['revertHex']}
raw=refusal('world-raw-reserved-exact'); absent=refusal('world-omitted-api-v2')
assert raw['selector']=='0x6a23ad80' and raw['uint256Words']==['1','1'] and raw['rootUnchanged'] and raw['durableHeadUnchanged']
assert absent['selector']=='0xd631c3a4' and absent['uint256Words']==['3','7'] and absent['rootUnchanged'] and absent['durableHeadUnchanged']
obj={'scope':'generated fixtures only; actual fresh geth EVM; no original Minecraft input','bootstrapImages':{'oldPrefixCount':106,'newImageCount':107,'oldPrefixByteIdentical':True,'navigableMapBootstrapIndex':106,'combinedRaw150ClassCount':cp['classCount'],'rawClassBindings':len(m['rawNames']),'derivedNavigableMapIndex':256,'checkpointClassCount':cp['classCount'],'terminalLifecycle':m['lifecycle'],'outcome':m['outcome'],'result':m['result'],'machineRoot':m['machineRoot'],'vfsRoot':m['vfsRoot'],'checkpointRoot':m['checkpointRoot'],'checkpointBytes':(d/'checkpoints'/f"{m['checkpointSHA256']}.bin").stat().st_size,'classCountDiagnosticSHA256':cp['checkpointSHA256'],'separateProcessReopen':reopen['manifest']['stage']=='final-reopened','finalReopenPID':reopen['finalReopenPID'],'startPID':start['pid']},'smallQuantumEquivalence':small,'negativeGates':{'rawNavigableMapNameEvenIdenticalImage':raw,'omittedNavigableMapMethodCall':absent},'interpretation':'Internal guest-step totals and machine/VFS commitments are equal across q1/q7/q4096. Checkpoint roots, epoch and host/EVM transport operation counters intentionally vary by quantum; they are not semantic state.'}
(results/'selected-results.json').write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({'classCount':cp['classCount'],'smallQuantumRoots':[x['machineStateRoot'] for x in small.values()],'guestSteps':{q:(x['totalJvmSteps'],x['totalInternalSteps']) for q,x in small.items()},'rawRefusal':raw['selector'],'omittedMethodRefusal':absent['selector'],'separateReopen':obj['bootstrapImages']['separateProcessReopen']},indent=2))
