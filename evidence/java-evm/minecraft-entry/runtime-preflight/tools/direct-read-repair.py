#!/usr/bin/env python3
"""COPY-only remove measured implicit allocation from a pure struct-return getter.
Parent dff19493 debug IR: fun_selectedAt begins
pop(allocate_and_zero_memory_struct_struct_Selected()).
Actual counts: padded15/big20/dense35, not merely2/3/5 loaded slots.
Direct typed memory reads preserve exactly the same indexes and bounds checks.
No assembly, fallback, shared Selected sentinel, ABI/cap/gas/codec change.
"""
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=p.read_text()
start=s.index('    function _selectedAt(');end=s.index('    function _putSelection(',start)
block=s[start:end]
assert block.count('function ')==1 and 'return selected[ci][mi][0];' in block
s=s[:start]+s[end:]
s,n=re.subn(r'_selectedAt\((p\.selected|selected), ([\w.]+), ([\w.]+)\)',lambda m:m[1]+'['+m[2]+']['+m[3]+'][0]',s)
assert n==11 and '_selectedAt(' not in s,(n,block)
p.write_text(s)
