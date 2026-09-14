#!/usr/bin/env python3
"""Exact count-24→25 source delta guard against parent-fdb8b3155."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent; stage=here.parent; parent=stage.parent/'parent-fdb8b3155'
pins=json.loads((stage/'pins.json').read_text())
old='MC-CLASS-AS-SUBCLASS-PARENT1'; new='MC-CLASSCOUNT25-PREFLIGHT1'
address='4d43434c415353434f554e543235000000000001'; owner='4d432d434c415353434f554e5432354f574e4552'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
inputs={str(p.relative_to(parent)):digest(p) for p in (parent/'engine/MCEntryInterpreter.sol',parent/'coordinator/MCEntryCoordinator.sol',parent/'executed_driver.go.txt',parent/'checkpoint_frames.py')}
assert json.loads((stage/'parent-input.json').read_text())['sha256']==inputs
# Engine changes only its all-nine-domain identity and raw-count/config commitment.
e0=(parent/'engine/MCEntryInterpreter.sol').read_text(); e= (stage/'engine/MCEntryInterpreter.sol').read_text()
want=e0.replace(old,new).replace('MAX_RAW_CLASSES = 24','MAX_RAW_CLASSES = 25').replace('uint32(24), uint32(262144)','uint32(25), uint32(262144)')
assert e==want
assert e.count(new)==9 and e.count('MAX_RAW_CLASSES = 25')==1 and e.count('uint32(25), uint32(262144)')==1 and 'MAX_RAW_BYTES = 262144;' in e
# Coordinator changes only domains, fixed capacity, fresh engine address/pin.
c0=(parent/'coordinator/MCEntryCoordinator.sol').read_text(); c=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
# Parent source has the exact engine Keccak, deliberately written explicitly here.
want=c0.replace(old,new).replace('[24]','[25]').replace('n > 24','n > 25').replace('4d432d41535355422d504152454e540000000001',address).replace('adb3eee77f938193982453c060a44ada01d10eb7c29f7874e4813d2a5046c600',pins['engine']['runtimeKeccak256'])
assert c==want
assert c.count('[25]')==4 and c.count('n > 25')==1 and c.count(new)==3
# Driver has the two fixed input/manifest guards at25; its only extra code is the
# explicit pre-mutation input ordering and constructor-boundary observer.
d=(stage/'tools/Go.txt').read_text()
assert d.count('> 25')==2 and d.count(new)==5 and address in d and owner in d
for value in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert value in d
assert 'names := fixtureNames(zipPath)\n\te, x := newEnv(dir)' in d and 'func boundaryCreate(' in d and 'case "boundary-create"' in d
assert 'classes<=96' in (stage/'tools/checkpoint_diagnostic.py').read_text()
# Bootstrap byte images/order and all native families are untouched.
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,e0));b=dict(re.findall(pat,e)); assert len(a)==len(b)==71 and a==b
assert 'new bytes32[](71)' in e and 'new uint256[](14)' in e and 'return 10;' in e
print(json.dumps({'parentInputsVerified':len(inputs),'bootstrapImages':71,'globalNativeBindings':10,'stringLocalBinding':10,'exceptionKinds':14,'rawClassCount':25,'rawByteCount':262144,'diagnosticClassBound':96,'address':'0x'+address},indent=2))
