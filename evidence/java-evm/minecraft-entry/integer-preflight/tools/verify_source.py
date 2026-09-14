#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
p=Path(__file__).resolve().parent.parent; s=(p/'engine/MCEntryInterpreter.sol').read_text(); c=(p/'coordinator/MCEntryCoordinator.sol').read_text()
assert s.count('MC-INTEGER-PREFLIGHT1')==9
assert 'new bytes32[](71)' in s and 'new uint256[](14)' in s
assert 'return 10;' in s and 'global native bindings remain 1..9' in s
assert 'p.classes[classSlot + 29].data = _bootstrapNumber();' in s
assert 'p.classes[classSlot + 30].data = _bootstrapNumberFormatException();' in s
assert 'p.classes[classSlot + 31].data = _bootstrapInteger();' in s
assert '_isReservedIntegerClass(users[i])' in s
pins={'Class':'0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934','String':'c412caea1d48baade8aa9d2653c6a23bb319a49deefe729ac99089f0c5248eba','System':'fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44','Number':'fe77f74edbcc2777f4edfa6227759fd8a3b856838113fb0fe9880affc4c9876f','NumberFormatException':'a627a1649de875297f522fd2fde19f32b3e79f1945e7343941c696692e039d15','Integer':'bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537'}
for n,h in pins.items():
 m=re.search(r'function _bootstrap'+n+r'\(\).*?hex"([0-9a-f]+)";',s,re.S); assert m,n
 assert hashlib.sha256(bytes.fromhex(m.group(1))).hexdigest()==h,n
assert 'MC-INTEGER-PREFLIGHT1/package/v1' in c and 'MC-INTEGER-PREFLIGHT1/vm/v1' in c
print(json.dumps({'bootstrapCount':71,'exceptionKinds':14,'globalBindings':9,'stringLocalBinding':10,'sourceSHA256':hashlib.sha256(s.encode()).hexdigest(),'coordinatorSHA256':hashlib.sha256(c.encode()).hexdigest()},indent=2))
