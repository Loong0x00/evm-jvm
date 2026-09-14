#!/usr/bin/env python3
"""Exact count-26→27 reverse-source guard against accepted queue parent source."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent; stage=here.parent; parent=stage.parent/'parent-854030297'
pins=json.loads((stage/'pins.json').read_text())
old='MC-CONCURRENT-LINKED-QUEUE-PARENT1'; new='MC-CLASSCOUNT27-PREFLIGHT1'
oldAddress='4d432d5145554555452d504152454e5400000001'; address='4d43434c415353434f554e543237000000000001'
oldOwner='4d432d5145554555452d4f574e45520000000002'; owner='4d432d434c415353434f554e5432374f574e4552'
oldEngineSHA='815193ba27cd60a152e55278c66ef5cf34f81f6d006f481fc50134776861710b'
oldEngineKeccak='34879656a9d14e6d938ab362b0ff12babfcad5a0438784329d7bc1abc884cb54'
oldCoordinatorKeccak='cdbde4143dcbe7fab37e00b1b79dba1cd9e5f04c966d0dd130c0b9bc74434285'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source={'artifacts/engine/MCEntryInterpreter.sol':'engine/MCEntryInterpreter.sol','artifacts/coordinator/MCEntryCoordinator.sol':'coordinator/MCEntryCoordinator.sol','executed-driver.go.txt':'tools/Go.txt','checkpoint_frames.py':'tools/checkpoint_diagnostic.py'}
inputs={p:digest(parent/p) for p in source}
assert json.loads((stage/'parent-input.json').read_text()) == {'basis':'ae7ce3fb8','parentEvidence':'parent-854030297','sha256':inputs}
# Engine changes only all nine domain labels, raw cap, and first DCFG word.
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text(); e=(stage/'engine/MCEntryInterpreter.sol').read_text()
want=e0.replace(old,new).replace('MAX_RAW_CLASSES = 26','MAX_RAW_CLASSES = 27').replace('uint32(26), uint32(262144)','uint32(27), uint32(262144)')
assert e==want
assert e.count(new)==9 and e.count('MAX_RAW_CLASSES = 27')==1 and e.count('uint32(27), uint32(262144)')==1
assert 'MAX_RAW_BYTES = 262144;' in e and 'new bytes32[](81)' in e and 'new uint256[](14)' in e and 'return 11;' in e
# Coordinator changes only all three domains, four fixed capacities, guard, engine anchor and fresh engine pin.
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text(); c=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
want=c0.replace(old,new).replace('[26]','[27]').replace('n > 26','n > 27').replace(oldAddress,address).replace(oldEngineKeccak,pins['engine']['runtimeKeccak256'])
assert c==want
assert c.count(new)==3 and c.count('[27]')==4 and c.count('n > 27')==1 and c.count(address)==1
# Durable driver retains logic, allowing only matching profile pins/domains/anchor and two cap guards.
d0=(parent/'executed-driver.go.txt').read_text(); d=(stage/'tools/Go.txt').read_text()
want=(d0.replace(old,new).replace(oldAddress,address).replace(oldOwner,owner).replace('> 26','> 27')
 .replace(oldEngineSHA,pins['engine']['runtimeSHA256'])
 .replace(oldEngineKeccak,pins['engine']['runtimeKeccak256'])
 .replace(oldCoordinatorKeccak,pins['coordinator']['runtimeKeccak256']))
assert d==want
assert d.count(new)==5 and d.count('> 27')==2 and address in d and owner in d
for x in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert x in d
# This consumer is diagnostic only. Bootstrap images and all remaining profile limits are exact.
diag=(stage/'tools/checkpoint_diagnostic.py').read_text(); assert diag == (parent/'checkpoint_frames.py').read_text().replace('classes<=107','classes<=108')
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,e0)); b=dict(re.findall(pat,e)); assert len(a)==len(b)==81 and a==b
assert pins['rawLimits']==[27,262144] and pins['bootstrapCount']==81 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10 and pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['checkpointCap']==1048576 and pins['headCap']==32768
assert pins['runtimeCap']==393216 and pins['externalLocalGas']==1000000000 and pins['reserve']==25000000
print(json.dumps({'acceptedQueueParent':'parent-854030297','parentInputsVerified':len(inputs),'bootstrapImages':81,'globalNativeBindings':11,'stringLocalBinding':10,'exceptionKinds':14,'rawClassCount':27,'rawByteCount':262144,'diagnosticClassBound':108,'address':'0x'+address,'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
