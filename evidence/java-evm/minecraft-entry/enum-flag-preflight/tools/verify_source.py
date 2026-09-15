#!/usr/bin/env python3
"""Strict reverse verifier for the ACC_ENUM-only MC staged-engine delta."""
from pathlib import Path
import hashlib,json,re,subprocess
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
parent=stage.parent/'parent-17e21d664'; pins=json.loads((stage/'pins.json').read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def expect_one(s, old, new):
    assert s.count(old)==1,(old,s.count(old)); return s.replace(old,new)
assert pins['basis']=='17e21d664' and pins['parentEvidence']=='parent-17e21d664'
assert pins['domain']=='MC-ENUM-FLAG-PARENT1' and pins['address']=='0x4d432d454e554d2d464c41472d504152454e5431'
# The address is an independently allocated 20-byte LOCAL384 engine address.
old_domain='MC-CLASSCOUNT29-PARENT1'; domain=pins['domain']
old_addr='4d432d434c41535332392d504152454e54000001'; addr=pins['address'][2:]
old_owner='4d432d434c41535332392d4f574e455200000002'; owner=pins['owner'][2:]
old_engine_sha='e7838ac0e3c670348caeb8b12c71fc25a97f2d2beb9fbdd91437bce0403bb829'
old_engine_keccak='3a483cbb9f382ff41f122cdbad670e9681b03327c98b617e782f875d376c8e08'
old_coord_keccak='eb85f0ea2bc8d621b5da2acaea4ad3422ec8ed4c62099c2a4ca50b4a5edbe29e'
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text()
e=e0.replace(old_domain,domain); e=expect_one(e,'(c.accessFlags & 0xe000) != 0','(c.accessFlags & 0xa000) != 0')
assert (stage/'engine/MCEntryInterpreter.sol').read_text()==e
assert e.count('0xa000')==1 and e.count('0xe000')==0
# Interface validation stays byte-for-byte inherited and rejects I|E/I|A/I|M.
assert '(c.accessFlags & 0xe010) != 0' in e
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text()
c=c0.replace(old_domain,domain).replace(old_addr,addr).replace(old_engine_keccak,pins['engine']['runtimeKeccak256'])
assert (stage/'coordinator/MCEntryCoordinator.sol').read_text()==c
d0=(parent/'executed-driver.go.txt').read_text()
d=(d0.replace(old_domain,domain).replace(old_addr,addr).replace(old_owner,owner)
    .replace(old_engine_sha,pins['engine']['runtimeSHA256'])
    .replace(old_engine_keccak,pins['engine']['runtimeKeccak256'])
    .replace(old_coord_keccak,pins['coordinator']['runtimeKeccak256']))
assert (stage/'tools/Go.txt').read_text()==d
# The generic profile is explicitly out of scope and remains on its 0xe000 policy.
generic=(root/'jvmevm/runtime/JVMSubsetInterpreter.sol').read_text()
assert generic.count('(c.accessFlags & 0xe000) != 0')==1
assert subprocess.run(['git','diff','--quiet','17e21d664','--','jvmevm/runtime/JVMSubsetInterpreter.sol'],cwd=root).returncode==0
for k in ('bootstrapCount','globalNativeBindings','stringLocalBinding','exceptionKinds','maxFrames','checkpointCap','headCap'):
    assert pins[k]=={'bootstrapCount':81,'globalNativeBindings':11,'stringLocalBinding':10,'exceptionKinds':14,'maxFrames':128,'checkpointCap':1048576,'headCap':32768}[k]
assert pins['rawLimits']==[29,262144] and pins['runtimeCap']==393216 and pins['externalLocalGas']==1000000000 and pins['reserve']==25000000
assert pins['engine']['bytes']==388963 and pins['coordinator']['bytes']==4146
# All embedded bootstrap images are exactly inherited; no Enum bootstrap was added.
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,e0)); b=dict(re.findall(pat,e)); assert len(a)==len(b)==81 and a==b
assert 'function _bootstrapEnum()' not in e and e.count('java/lang/Enum') == e0.count('java/lang/Enum')
print(json.dumps({'basis':'parent-17e21d664','semanticDelta':'noninterface unsupported mask 0xe000 -> 0xa000','genericRuntimeUnchanged':True,'bootstrapImages':81,'rawLimits':pins['rawLimits'],'domain':domain,'address':pins['address'],'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
