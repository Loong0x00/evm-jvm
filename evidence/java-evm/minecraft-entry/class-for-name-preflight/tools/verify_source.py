#!/usr/bin/env python3
"""Source-only invariant check for the bounded Class.forName preflight."""
import hashlib, re
from pathlib import Path
here=Path(__file__).resolve().parents[1]
source=(here/'engine/MCEntryInterpreter.sol').read_text()
prior=(Path('/home/user/evm-jvm/mc-class-for-name')/'evidence/java-evm/minecraft-entry/parent-10c10d224/engine/MCEntryInterpreter.sol').read_text()
def bootstrap(s):
    return {m.group(1):m.group(2) for m in re.finditer(r'function (_bootstrap\w+)\([^)]*\)[^{]*\{\s*return hex"([0-9a-f]+)";',s)}
a,b=bootstrap(source),bootstrap(prior)
changed={k for k in a if a[k]!=b.get(k)}
assert changed=={'_bootstrapClass'}, changed
assert len(bytes.fromhex(a['_bootstrapClass']))==770
assert hashlib.sha256(bytes.fromhex(a['_bootstrapClass'])).hexdigest()=='d63783800a1906528d2064fc40f740aaaceb616af8212c4d1a8db1da21791061'
assert 'bytes("forName0")' in source and 'return 9;' in source
assert 'binding == 7 || binding == 8 || binding == 9' in source
assert 'ClassForNameInitializationError(target, opPC)' in source
assert 'nativeBinding == 9, opPC' in source
assert source.count('MC-CLASS-FOR-NAME-PREFLIGHT1')==9
assert 'forName(String,boolean,ClassLoader)' not in source
print('only bootstrap39 changed; Class=770B; binding9/private-static; nine domains repinned')
