#!/usr/bin/env python3
"""Exact-delta source guard for the class-count-only derivative."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent
parent=here.parent/'parent-f780f1a13'
inputs=json.loads((here/'parent-input.json').read_text())['inputs']
for name,want in inputs.items(): assert hashlib.sha256((parent/name).read_bytes()).hexdigest()==want,name
engine=(here/'engine/MCEntryInterpreter.sol').read_text(); oldengine=(parent/'engine/MCEntryInterpreter.sol').read_text()
coord=(here/'coordinator/MCEntryCoordinator.sol').read_text(); driver=(here/'executed_bounded_driver.go.txt').read_text()
domain='MC-CLASSCOUNT24-PREFLIGHT1'; address='4d43434c415353434f554e543234000000000001'
assert 'MC-ARRAYCOPY-PARENT1' not in engine+coord+driver
assert engine.count(domain)==9 and 'MAX_RAW_CLASSES = 24;' in engine and 'MAX_RAW_BYTES = 262144;' in engine
assert engine.count('uint32(24), uint32(262144)')==1 and engine.count('s.argumentCount = s.argumentKinds.length;')==oldengine.count('s.argumentCount = s.argumentKinds.length;')==6
native=re.search(r'function _loadNativeCallee.*?\n    }',engine,re.S).group(0)
assert 's.argumentCount = s.argumentKinds.length;' in native
assert coord.count(domain)==3 and address in coord and coord.count('[24]')==4 and coord.count('n > 24')==1
assert driver.count(domain)==5 and address in driver and driver.count('> 24')==1 and 'MC_ENTRY_ALLOW_BOUNDARY_25' in driver
# Only the raw class count slots and domain commitments differ in the engine; all bootstrap class bytes/order are exact.
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,oldengine)); b=dict(re.findall(pat,engine)); assert len(a)==len(b)==45 and a==b
root=re.search(r'function _bootstrapRoot\(\).*?return keccak256\(abi.encode\(DBOOT, h\)\);',engine,re.S).group(0)
assert 'h[44] = keccak256(_bootstrapSystem());' in root
pins=json.loads((here/'pins.json').read_text())
for value in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']): assert value in coord+driver,value
print(json.dumps({'parentInputsVerified':len(inputs),'bootstrapImages':45,'systemBootstrapIndex':44,'rawClassCount':24,'rawByteCount':262144,'address':'0x'+address},indent=2))
