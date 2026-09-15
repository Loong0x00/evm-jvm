#!/usr/bin/env python3
"""Exact count-28→29 reverse-source guard against parent-b985a6add."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent; stage=here.parent; parent=stage.parent/'parent-b985a6add'; pins=json.loads((stage/'pins.json').read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source={'artifacts/engine/MCEntryInterpreter.sol':'engine/MCEntryInterpreter.sol','artifacts/coordinator/MCEntryCoordinator.sol':'coordinator/MCEntryCoordinator.sol','executed-driver.go.txt':'tools/Go.txt','checkpoint_frames.py':'tools/checkpoint_diagnostic.py'}
inputs={p:digest(parent/p) for p in source}
assert json.loads((stage/'parent-input.json').read_text()) == {'basis':'b985a6add','parentEvidence':'parent-b985a6add','sha256':inputs}
old='MC-CLASSCOUNT28-PARENT1'; new='MC-CLASSCOUNT29-PREFLIGHT1'
oldAddress='4d432d434c41535332382d504152454e54000001'; address='4d43434c415353434f554e543239000000000001'
oldOwner='4d432d434c41535332382d4f574e455200000002'; owner='4d432d434c41535332392d4f574e455200000002'
oldEngineSHA='2617cd04a81faa4050075cdf9f3969993e13d047f7bb07f1fac7721bd642a705'; oldEngineKeccak='b9511a4e6592fca77e480ad77e355d66b91ab9af9fa2c69dca2b7e485ef97e89'; oldCoordinatorKeccak='991df8cd08ab61c01bbf36429d7f76e27e36ce14c156d36d6673d6de9f6b2035'
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text(); e=(stage/'engine/MCEntryInterpreter.sol').read_text(); want=e0.replace(old,new).replace('MAX_RAW_CLASSES = 28','MAX_RAW_CLASSES = 29').replace('uint32(28), uint32(262144)','uint32(29), uint32(262144)'); assert e==want
assert e.count(new)==9 and e.count('MAX_RAW_CLASSES = 29')==1 and e.count('uint32(29), uint32(262144)')==1
assert 'MAX_RAW_BYTES = 262144;' in e and 'new bytes32[](81)' in e and 'new uint256[](14)' in e and 'return 11;' in e
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text(); c=(stage/'coordinator/MCEntryCoordinator.sol').read_text(); want=c0.replace(old,new).replace('[28]','[29]').replace('n > 28','n > 29').replace(oldAddress,address).replace(oldEngineKeccak,pins['engine']['runtimeKeccak256']); assert c==want
assert c.count(new)==3 and c.count('[29]')==4 and c.count('n > 29')==1 and c.count(address)==1
d0=(parent/'executed-driver.go.txt').read_text(); d=(stage/'tools/Go.txt').read_text(); want=(d0.replace(old,new).replace(oldAddress,address).replace(oldOwner,owner).replace('> 28','> 29').replace(oldEngineSHA,pins['engine']['runtimeSHA256']).replace(oldEngineKeccak,pins['engine']['runtimeKeccak256']).replace(oldCoordinatorKeccak,pins['coordinator']['runtimeKeccak256'])); assert d==want
assert d.count(new)==5 and d.count('> 29')==2 and address in d and owner in d
for x in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert x in d
diag=(stage/'tools/checkpoint_diagnostic.py').read_text(); assert diag == (parent/'checkpoint_frames.py').read_text().replace('classes<=109','classes<=110')
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'; a=dict(re.findall(pat,e0)); b=dict(re.findall(pat,e)); assert len(a)==len(b)==81 and a==b
assert pins['rawLimits']==[29,262144] and pins['bootstrapCount']==81 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10 and pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['checkpointCap']==1048576 and pins['headCap']==32768
assert pins['runtimeCap']==393216 and pins['externalLocalGas']==1000000000 and pins['reserve']==25000000
print(json.dumps({'acceptedClasscount28Parent':'parent-b985a6add','parentInputsVerified':len(inputs),'bootstrapImages':81,'globalNativeBindings':11,'stringLocalBinding':10,'exceptionKinds':14,'rawClassCount':29,'rawByteCount':262144,'diagnosticClassBound':110,'address':'0x'+address,'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
