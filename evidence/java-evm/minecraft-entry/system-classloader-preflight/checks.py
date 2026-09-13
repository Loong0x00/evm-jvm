#!/usr/bin/env python3
"""Offline checks for the system ClassLoader getter evidence (no StateDB access)."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'pins.json').read_text())
assert sha256((HERE/'artifacts/engine/MCEntryInterpreter.runtime.hex').read_text().strip().encode()).hexdigest() != '0' * 64
runtime=bytes.fromhex((HERE/'artifacts/engine/MCEntryInterpreter.runtime.hex').read_text().strip())
assert len(runtime)==PINS['engine']['bytes']==328695
assert sha256(runtime).hexdigest()==PINS['engine']['runtimeSHA256']
assert sha256((HERE/'artifacts/bootstrap/java/lang/ClassLoader.class').read_bytes()).hexdigest()==PINS['classLoader']['sha256']
assert len((HERE/'artifacts/bootstrap/java/lang/ClassLoader.class').read_bytes())==PINS['classLoader']['bytes']==195
source=(HERE/'source/engine/MCEntryInterpreter.sol').read_text()
assert source.count('MC-SYSTEM-CLASSLOADER-PREFLIGHT1')==9
assert 'bytes("getSystemClassLoader")' in source
assert 'bytes("()Ljava/lang/ClassLoader;")' in source
assert 'binding == 6 && (uint16(meta) != 0x0109' in source
assert 'f.sp = _push(f.stack, base, _packRef(uint32(loader)), opPC);' in source
assert 'if (malformed || loader == 0) revert LC0StateError(7, 0);' in source
assert 'return 5;' in source and 'return 6;' in source
rows=[]; opaque=None; machine=None
for q in ('q1','q7','q4096'):
    head=json.loads((HERE/'receipts'/q/'durable-head.json').read_text())
    cp=(HERE/'receipts'/q/'checkpoints'/(head['checkpointSHA256']+'.bin')).read_bytes()
    assert head['lifecycle']==head['outcome']==2
    assert head['jvmSteps']==332 and head['internalSteps']==8
    assert sha256(cp).hexdigest()==head['checkpointSHA256']
    # `done=631` is a packed guest int in the generated root's static state.
    assert bytes.fromhex('0000000000000000010000000000000277') in cp
    row=(head['jvmSteps'],head['internalSteps'],head['machineRoot'],sha256(cp[280:]).hexdigest())
    if opaque is None: opaque=row
    else: assert row==opaque
    rows.append({'quantum':q,'epoch':head['epoch'],'machineRoot':head['machineRoot'],'opaqueSHA256':row[3]})
for n,selector,words in [('resources-unsupported','0xd631c3a4',['3','21']),('vm-replacement','0x6a23ad80',['1','1'])]:
    r=json.loads((HERE/'receipts/negatives'/f'{n}-start-refusal.json').read_text())
    assert r['selector']==selector and r['uint256Words']==words and r['rootUnchanged']
(HERE/'verified.json').write_text(json.dumps({'generated':rows,'negativeRefusals':2},indent=2)+'\n')
print((HERE/'verified.json').read_text(),end='')
