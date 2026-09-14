#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
p=Path(__file__).resolve().parent.parent; s=(p/'engine/MCEntryInterpreter.sol').read_text()
assert s.count('MC-JAVA-VERSION-SPLIT1') == 9
assert 'new bytes32[](68)' in s and 'new uint256[](14)' in s
assert 'return 10;' in s and 'global native bindings remain 1..9' in s
assert 'bytes("split")' in s and 'bytes("(Ljava/lang/String;)[Ljava/lang/String;")' in s
assert 'regex.length != 4' in s and 'StringProfileError(1, pc)' in s
assert 'units[i] == 0x2d || units[i] == 0x2e' in s
assert '_splitReceiverArray(arena, receiverHandle)' in s
assert 'ARRAY_CLASS_BASE + arena.stringClass' in s
assert 'count >= MAX_ARRAYS - arena.ordinaryArrayCount' in s
assert 'stringBinding == 7 || stringBinding == 10' in s
# Parent's corrected Java8 Class is intentionally retained exactly.
m=re.search(r'function _bootstrapClass\(\).*?hex"([0-9a-f]+)";',s,re.S); assert m
assert hashlib.sha256(bytes.fromhex(m.group(1))).hexdigest()=='0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934'
print(json.dumps({'bootstrapCount':68,'exceptionKinds':14,'globalBindings':9,'stringLocalBinding':10,'sourceSHA256':hashlib.sha256(s.encode()).hexdigest()},indent=2))
