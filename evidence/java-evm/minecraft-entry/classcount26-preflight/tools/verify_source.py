#!/usr/bin/env python3
"""Exact count-25→26 reverse-source guard against accepted reentrant-lock source."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent; stage=here.parent; parent=stage.parent/'parent-355547999'
pins=json.loads((stage/'pins.json').read_text())
old='MC-REENTRANT-LOCKS-PARENT1'; new='MC-CLASSCOUNT26-PREFLIGHT1'
oldAddress='4d432d524c4f434b532d504152454e5400000001'; address='4d43434c415353434f554e543236000000000001'
oldOwner='4d432d524c4f434b532d4f574e45520000000002'; owner='4d432d434c415353434f554e5432364f574e4552'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
paths=['artifacts/engine/MCEntryInterpreter.sol','artifacts/coordinator/MCEntryCoordinator.sol','executed-driver.go.txt','checkpoint_frames.py']
inputs={p:digest(parent/p) for p in paths}
assert json.loads((stage/'parent-input.json').read_text())['sha256']==inputs
# Engine changes only all nine domain labels, the raw class cap, and DCFG's first word.
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text(); e=(stage/'engine/MCEntryInterpreter.sol').read_text()
want=e0.replace(old,new).replace('MAX_RAW_CLASSES = 25','MAX_RAW_CLASSES = 26').replace('uint32(25), uint32(262144)','uint32(26), uint32(262144)')
assert e==want
assert e.count(new)==9 and e.count('MAX_RAW_CLASSES = 26')==1 and e.count('uint32(26), uint32(262144)')==1
assert 'MAX_RAW_BYTES = 262144;' in e and 'new bytes32[](79)' in e and 'new uint256[](14)' in e and 'return 11;' in e
# Coordinator changes only all three domains, four fixed capacities, its guard, anchor and engine pin.
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text(); c=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
want=c0.replace(old,new).replace('[25]','[26]').replace('n > 25','n > 26').replace(oldAddress,address).replace('0d9224c30cc236728ce70aa0b76cf6a7c0f612a5f21e78ae5747827899464f84',pins['engine']['runtimeKeccak256'])
assert c==want
assert c.count(new)==3 and c.count('[26]')==4 and c.count('n > 26')==1 and c.count(address)==1
# Durable driver retains its logic, accepting only the matching pins/domains/anchor and cap guards.
d0=(parent/'executed-driver.go.txt').read_text(); d=(stage/'tools/Go.txt').read_text()
want=(d0.replace(old,new).replace(oldAddress,address).replace(oldOwner,owner).replace('> 25','> 26')
 .replace('3123fe6d9512abf22b50814f7dd113eb9382171c0b1cfa37cefcb597cb1fda5d',pins['engine']['runtimeSHA256'])
 .replace('0d9224c30cc236728ce70aa0b76cf6a7c0f612a5f21e78ae5747827899464f84',pins['engine']['runtimeKeccak256'])
 .replace('e93a98671668757d39dd3b81c7eb2ad888806a3226f285d801ebe7472cc4ca31',pins['coordinator']['runtimeKeccak256']))
assert d==want
assert d.count(new)==5 and d.count('> 26')==2 and address in d and owner in d
for x in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert x in d
# This consumer is diagnostic only; bootstrap images and all remaining profile limits are unchanged.
diag=(stage/'tools/checkpoint_diagnostic.py').read_text(); assert diag== (parent/'checkpoint_frames.py').read_text().replace('classes<=104','classes<=105')
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,e0));b=dict(re.findall(pat,e));assert len(a)==len(b)==79 and a==b
assert pins['rawLimits']==[26,262144] and pins['bootstrapCount']==79 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10 and pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['checkpointCap']==1048576 and pins['headCap']==32768
print(json.dumps({'parentInputsVerified':len(inputs),'bootstrapImages':79,'globalNativeBindings':11,'stringLocalBinding':10,'exceptionKinds':14,'rawClassCount':26,'rawByteCount':262144,'diagnosticClassBound':105,'address':'0x'+address,'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
