#!/usr/bin/env python3
"""Strict source-only guard for the bounded Class.newInstance profile."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,tempfile,zipfile

here=Path(__file__).resolve().parent
stage=here.parent
root=here.parents[4]
pins=json.loads((stage/'pins.json').read_text())
engine=(stage/'engine/MCEntryInterpreter.sol').read_text()
coord=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
driver=(stage/'tools/Go.txt').read_text()
assert pins['profile']=='MC-CLASS-NEW-INSTANCE-PREFLIGHT1'
assert pins['rawLimits']==[25,262144] and pins['bootstrapCount']==71
assert pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10
assert pins['exceptionKinds']==14 and pins['maxFrames']==128
assert 'MAX_RAW_CLASSES = 25' in engine and 'MAX_RAW_BYTES = 262144;' in engine
assert 'new bytes32[](71)' in engine and 'new uint256[](14)' in engine
assert 'error ClassNewInstanceProfileError(uint256 code, uint256 pc);' in engine
assert 'bytes("newInstance")' in engine and 'bytes("()Ljava/lang/Object;")' in engine
assert 'if (binding == 11)' in engine and 'access != 0x0101' in engine
assert 'function _newInstanceConstructor(' in engine
assert 'target >= rawClassCount' in engine and 'ClassNewInstanceProfileError' in engine
assert '_canonicalClassMirrorTarget(' in engine and 'f.pc = opPC;' in engine
assert 'KIND_UNINIT << KIND_SHIFT' in engine and 'instanceChild.isConstructor = true;' in engine
assert 'new bytes32[](71)' in engine # bootstrap and exception families remain fixed
assert engine.count('MC-CLASS-NEW-INSTANCE-PREFLIGHT1')==9
assert coord.count('MC-CLASS-NEW-INSTANCE-PREFLIGHT1')==3
assert pins['address'][2:] in coord and pins['engine']['runtimeKeccak256'] in coord
for value in (pins['engine']['runtimeSHA256'],pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']):
    assert value in driver
assert str(pins['engine']['bytes']) in driver and str(pins['coordinator']['bytes']) in driver
assert 'len(m.Decoders) > 25' in driver and 'ordinaryGas = uint64(1_000_000_000)' in driver
# Rebuild the six replaced Java 8 inputs and require the embedded Class image exactly.
with tempfile.TemporaryDirectory(dir=root/'build') as td:
    td=Path(td); api=td/'rt.jar'; out=td/'classes'; out.mkdir()
    api.write_bytes(Path('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar').read_bytes())
    subprocess.run(['zip','-q','-d',api,*['java/lang/'+x+'.class' for x in ('String','System','Class','Number','NumberFormatException','Integer')]],check=True)
    src=[stage/'bootstrap/java/lang'/(x+'.java') for x in ('String','System','Class','Number','NumberFormatException','Integer')]
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out,*src],check=True)
    rebuilt=(out/'java/lang/Class.class').read_bytes()
    assert hashlib.sha256(rebuilt).hexdigest()==pins['bootstrapSHA256']['Class']
    m=re.search(r'function _bootstrapClass\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";',engine,re.S)
    assert m and bytes.fromhex(m.group(1))==rebuilt
print(json.dumps({'profile':pins['profile'],'bootstrapImages':71,'globalNativeBindings':11,'classSHA256':pins['bootstrapSHA256']['Class'],'engineBytes':pins['engine']['bytes'],'coordinatorBytes':pins['coordinator']['bytes']},indent=2))
