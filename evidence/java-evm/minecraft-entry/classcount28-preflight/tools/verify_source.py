#!/usr/bin/env python3
"""Exact count-27→28 reverse-source guard against accepted classcount27 parent source."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent; stage=here.parent; parent=stage.parent/'parent-a1e9e0f64'
pins=json.loads((stage/'pins.json').read_text())
old='MC-CLASSCOUNT27-PARENT1'; new='MC-CLASSCOUNT28-PREFLIGHT1'
oldAddress='4d432d434c41535332372d504152454e54000001'; address='4d43434c415353434f554e543238000000000001'
oldOwner='4d432d434c41535332372d4f574e455200000002'; owner='4d432d434c415353434f554e5432384f574e4552'
oldEngineSHA='97a1b4a4792105caf755bdb6c15a060ea068b0280f7f494bf36e831d69dc675e'
oldEngineKeccak='6f406521290192e018ce5a50cfba0d572f0f83cd8924f613344f47b907e2f2ed'
oldCoordinatorKeccak='2e5dcf64745b389ff312e02b56d19e8339742d4b1bcc0dff6c8c83687fed397b'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source={'artifacts/engine/MCEntryInterpreter.sol':'engine/MCEntryInterpreter.sol','artifacts/coordinator/MCEntryCoordinator.sol':'coordinator/MCEntryCoordinator.sol','executed-driver.go.txt':'tools/Go.txt','checkpoint_frames.py':'tools/checkpoint_diagnostic.py'}
inputs={p:digest(parent/p) for p in source}
assert json.loads((stage/'parent-input.json').read_text()) == {'basis':'a1e9e0f64','parentEvidence':'parent-a1e9e0f64','sha256':inputs}
# Engine changes only all nine domain labels, raw cap, and the first DCFG word.
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text(); e=(stage/'engine/MCEntryInterpreter.sol').read_text()
want=e0.replace(old,new).replace('MAX_RAW_CLASSES = 27','MAX_RAW_CLASSES = 28').replace('uint32(27), uint32(262144)','uint32(28), uint32(262144)')
assert e==want
assert e.count(new)==9 and e.count('MAX_RAW_CLASSES = 28')==1 and e.count('uint32(28), uint32(262144)')==1
assert 'MAX_RAW_BYTES = 262144;' in e and 'new bytes32[](81)' in e and 'new uint256[](14)' in e and 'return 11;' in e
# Coordinator changes only all three domains, four fixed capacities, guard, engine anchor and fresh engine pin.
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text(); c=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
want=c0.replace(old,new).replace('[27]','[28]').replace('n > 27','n > 28').replace(oldAddress,address).replace(oldEngineKeccak,pins['engine']['runtimeKeccak256'])
assert c==want
assert c.count(new)==3 and c.count('[28]')==4 and c.count('n > 28')==1 and c.count(address)==1
# Durable driver retains logic, allowing only matching profile pins/domains/anchor and two cap guards.
d0=(parent/'executed-driver.go.txt').read_text(); d=(stage/'tools/Go.txt').read_text()
want=(d0.replace(old,new).replace(oldAddress,address).replace(oldOwner,owner).replace('> 27','> 28')
 .replace(oldEngineSHA,pins['engine']['runtimeSHA256'])
 .replace(oldEngineKeccak,pins['engine']['runtimeKeccak256'])
 .replace(oldCoordinatorKeccak,pins['coordinator']['runtimeKeccak256']))
assert d==want
assert d.count(new)==5 and d.count('> 28')==2 and address in d and owner in d
for x in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert x in d
# This consumer is diagnostic only. Bootstrap images and all remaining profile limits are exact.
diag=(stage/'tools/checkpoint_diagnostic.py').read_text(); assert diag == (parent/'checkpoint_frames.py').read_text().replace('classes<=108','classes<=109')
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,e0)); b=dict(re.findall(pat,e)); assert len(a)==len(b)==81 and a==b
assert pins['rawLimits']==[28,262144] and pins['bootstrapCount']==81 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10 and pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['checkpointCap']==1048576 and pins['headCap']==32768
assert pins['runtimeCap']==393216 and pins['externalLocalGas']==1000000000 and pins['reserve']==25000000
print(json.dumps({'acceptedClasscount27Parent':'parent-a1e9e0f64','parentInputsVerified':len(inputs),'bootstrapImages':81,'globalNativeBindings':11,'stringLocalBinding':10,'exceptionKinds':14,'rawClassCount':28,'rawByteCount':262144,'diagnosticClassBound':109,'address':'0x'+address,'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
