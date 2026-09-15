#!/usr/bin/env python3
"""Strict reverse verifier for the append-only java/lang/Enum bootstrap 82 stage."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
parent=stage.parent/'parent-9453ebd08'; pins=json.loads((stage/'pins.json').read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
inputs={k:digest(parent/k) for k in ('artifacts/engine/MCEntryInterpreter.sol','artifacts/coordinator/MCEntryCoordinator.sol','executed-driver.go.txt')}
assert json.loads((stage/'parent-input.json').read_text())=={'basis':'9453ebd08','parentEvidence':'parent-9453ebd08','sha256':inputs}
assert pins['basis']=='9453ebd08' and pins['parentEvidence']=='parent-9453ebd08' and pins['phase']=='built'
assert pins['domain']=='MC-ENUM-BOOTSTRAP-PARENT1' and pins['address']=='0x4d432d454e554d2d424f4f545354524150310000' and pins['owner']=='0x4d432d454e554d2d424f4f542d4f574e45523100'
assert pins['bootstrapCount']==82 and pins['bootstrapSHA256']['Enum']=='0e041ff7141ae18c33269980951bc62b190a62c13091c74c7dabf5cd82db01cf'
assert pins['runtimeCap']==393216 and pins['rawLimits']==[29,262144] and pins['externalLocalGas']==1000000000 and pins['reserve']==25000000 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10 and pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['checkpointCap']==1048576 and pins['headCap']==32768
# Recompile the one Java8 source input against an rt.jar with only Enum removed.
with tempfile.TemporaryDirectory(dir=root/'build') as td:
 td=Path(td); api=td/'rt-without-enum.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
 subprocess.run(['zip','-q','-d',api,'java/lang/Enum.class'],check=True)
 out=td/'classes'; out.mkdir()
 subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out,stage/'bootstrap/java/lang/Enum.java'],check=True)
 enum=(out/'java/lang/Enum.class').read_bytes()
assert hashlib.sha256(enum).hexdigest()==pins['bootstrapSHA256']['Enum']
assert bytes.fromhex((stage/'bootstrap/java/lang/Enum.class.hex').read_text().strip())==enum and b'<clinit>' not in enum
source=(stage/'bootstrap/java/lang/Enum.java').read_text()
for text in ('public abstract class Enum<E extends Enum<E>>','implements Comparable<E>, java.io.Serializable','private final String name;','private final int ordinal;','protected Enum(String name, int ordinal)','public final String name()','public final int ordinal()','public String toString()','public final int compareTo(E other)'):
 assert text in source,text
for forbidden in ('hashCode(', 'clone(', 'finalize(', 'valueOf(', 'getDeclaringClass(', '<clinit>'):
 assert forbidden not in source,forbidden
# Reconstruct the exact source delta from the accepted parent. No historical image moves.
e0=(parent/'artifacts/engine/MCEntryInterpreter.sol').read_text(); e=e0.replace('MC-ENUM-FLAG-PARENT2',pins['domain'])
def one(a,b):
 global e
 assert e.count(a)==1,(a,e.count(a)); e=e.replace(a,b)
one('bytes32[] memory h = new bytes32[](81);','bytes32[] memory h = new bytes32[](82);')
one('        h[80] = keccak256(_bootstrapConcurrentLinkedQueue());\n        return keccak256(abi.encode(DBOOT, h));','        h[80] = keccak256(_bootstrapConcurrentLinkedQueue());\n        // Enum appends only after the complete 81-image queue tail.\n        h[81] = keccak256(_bootstrapEnum());\n        return keccak256(abi.encode(DBOOT, h));')
one('                || _isReservedLockClass(users[i])\n                || _isReservedQueueClass(users[i])) {','                || _isReservedLockClass(users[i])\n                || _isReservedQueueClass(users[i])\n                || _isReservedEnumClass(users[i])) {')
one('uint256 count = inputCount + 75 + (suppliedObject ? 0 : 1)','uint256 count = inputCount + 76 + (suppliedObject ? 0 : 1)')
one('        p.classes[classSlot + 41].data = _bootstrapConcurrentLinkedQueue();\n        p.classClass = classSlot;','        p.classes[classSlot + 41].data = _bootstrapConcurrentLinkedQueue();\n        // Enum is an immutable append-only image and never changes prior slots.\n        p.classes[classSlot + 42].data = _bootstrapEnum();\n        p.classClass = classSlot;')
one('    function _isReservedVFSClass(ClassInfo memory c) private pure returns (bool) {','    // java/lang/Enum is interpreter-owned: raw bindings may not replace it.\n    function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) {\n        return _isNamedClass(c, bytes("java/lang/Enum"));\n    }\n\n    function _isReservedVFSClass(ClassInfo memory c) private pure returns (bool) {')
assert e.endswith('}\n'); e=e[:-2]+'    function _bootstrapEnum() private pure returns (bytes memory) { return hex"'+enum.hex()+'"; }\n\n}\n'
actual=(stage/'engine/MCEntryInterpreter.sol').read_text(); assert actual==e
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=re.findall(pat,e0); b=re.findall(pat,actual); assert len(a)==81 and len(b)==82 and a==b[:81] and b[81]==('_bootstrapEnum',enum.hex())
assert actual.count('new bytes32[](82)')==1 and actual.count('inputCount + 76 +')==1 and actual.count('_isReservedEnumClass(users[i])')==1 and actual.count('function _bootstrapEnum()')==1
# Coordinator/driver contain only independent domain/address/owner changes and freshly
# measured immutable runtime pins; no raw limits or transport semantics change.
assert pins['engine']['bytes']==390633 and pins['coordinator']['bytes']==4146
c0=(parent/'artifacts/coordinator/MCEntryCoordinator.sol').read_text(); c=c0.replace('MC-ENUM-FLAG-PARENT2',pins['domain']).replace('4d432d454e554d2d504152454e54320000000001',pins['address'][2:]).replace('db5607160a3e035397de19a287fef688e7c34c92d0f5e2d2ee834201815f0f1a',pins['engine']['runtimeKeccak256']); assert (stage/'coordinator/MCEntryCoordinator.sol').read_text()==c
d0=(parent/'executed-driver.go.txt').read_text(); d=d0.replace('MC-ENUM-FLAG-PARENT2',pins['domain']).replace('4d432d454e554d2d504152454e54320000000001',pins['address'][2:]).replace('4d432d454e554d2d4f574e455232000000000002',pins['owner'][2:]).replace('50c5cd6ffefd559658b7c879bf4763b70b6336d1eaf7f6702fc13b609f5698da',pins['engine']['runtimeSHA256']).replace('db5607160a3e035397de19a287fef688e7c34c92d0f5e2d2ee834201815f0f1a',pins['engine']['runtimeKeccak256']).replace('534671b5bbb412a8d452efcae0ab28335e1a7a3e0fca786485c0d2916b4224d0',pins['coordinator']['runtimeKeccak256']).replace('388963',str(pins['engine']['bytes'])); assert (stage/'tools/Go.txt').read_text()==d
# Generic runtime and all fixed product dimensions remain outside this profile.
generic=root/'jvmevm/runtime/JVMSubsetInterpreter.sol'; assert subprocess.run(['git','diff','--quiet','9453ebd08','--',generic.relative_to(root)],cwd=root).returncode==0 and '(c.accessFlags & 0xe000) != 0' in generic.read_text()
assert 'assert classes<=111' in (stage/'tools/checkpoint_diagnostic.py').read_text()
print(json.dumps({'basis':'9453ebd08','semanticDelta':'append immutable Java8 Enum image82, reserve raw Enum replacement','bootstrapImages':82,'enumSHA256':pins['bootstrapSHA256']['Enum'],'rawLimits':pins['rawLimits'],'diagnosticClassBound':111,'domain':pins['domain']},indent=2))
