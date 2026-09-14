#!/usr/bin/env python3
"""Source-only invariants for the isolated Class.asSubclass candidate."""
from pathlib import Path
import hashlib,re
here=Path(__file__).resolve().parent.parent
s=(here/'engine/MCEntryInterpreter.sol').read_text()
c=(here/'coordinator/MCEntryCoordinator.sol').read_text()
cls=(here/'bootstrap/java/lang/Class.java').read_text()
assert s.count('MC-CLASS-AS-SUBCLASS-PREFLIGHT1') == 9
assert 'new bytes32[](71)' in s and 'new uint256[](14)' in s
assert 'bytes("asSubclass0")' in s
assert 'bytes("(Ljava/lang/Class;Ljava/lang/Class;)Ljava/lang/Class;")' in s
assert 'return 10;' in s
assert 'binding == 7 || binding == 8 || binding == 9 || binding == 10' in s
assert 'binding == 10 && (s.argumentKinds.length != 2' in s
assert '_canonicalClassMirrorTarget(' in s
assert '_typeAssignable(classes, valueTarget, parentTarget, parentLinks)' in s
assert '_raiseJava(\n                                8,' in s
assert '_raiseJava(\n                                6,' in s
assert 'f.stack[base] = f.stack[base];' in s
assert 'MC-INTEGER-PARENT1' not in s and 'MC-INTEGER-PARENT1' not in c
assert '4d432d434c4153532d41532d535542434c000001' in c
assert 'public <U> Class<? extends U> asSubclass(Class<U> parent)' in cls
assert 'private static native <U> Class<? extends U> asSubclass0' in cls
# Only Class changes relative to the accepted parent Java8 bootstrap sources.
parent=here.parent/'parent-661331e3d/bootstrap/java/lang'
for name in ('String','System','Number','NumberFormatException','Integer'):
    assert (here/'bootstrap/java/lang'/f'{name}.java').read_bytes()==(parent/f'{name}.java').read_bytes(),name
print('ok',hashlib.sha256(s.encode()).hexdigest())
