#!/usr/bin/env python3
import json,sys
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text())
assert p['baseCommit']=='73e17afbb5373b0cc2938b8b90ca950146fe8e9b'
assert p['pins']['di0CombinedSHA256']=='72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca'
assert p['pins']['vfs0aRuntimeSHA256']=='717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86'
s={x['label']:x for x in p['successes']}
assert s['alpha-direct']['result']==76 and s['alpha-q7']['result']==76 and s['beta-direct']['result']==203
assert s['alpha-direct']['slices']==1 and s['alpha-q7']['slices']>1 and s['beta-direct']['slices']==1
for key in ('machineRoot','vfsRoot','jvmSteps','internalSteps','inputBinding'):
    assert s['alpha-direct'][key]==s['alpha-q7'][key],key
assert s['alpha-direct']['resourceF']!=s['alpha-direct']['inputBinding']!=s['alpha-direct']['machineRoot']
assert s['alpha-direct']['inputBinding']!=s['beta-direct']['inputBinding']
assert s['alpha-direct']['result']!=s['beta-direct']['result']
f={x['label']:x for x in p['failures']}
assert f['unauthorized-caller']['error']=='BridgeError(10)'
assert f['wrong-resource-F']['error']=='BridgeError(7)'
assert f['wrong-archive-name-binding']['error']=='BridgeError(5)'
assert f['unverified-di0']['error']=='BridgeError(4)'
assert f['declared-name-mismatch']['error']=='LinkError'
assert f['malformed-class']['error']=='ClassError'
assert all(x['headAbsent'] for x in f.values())
assert max(x['tracker']['maxCallWallMs'] for x in p['resources'])<30000
assert p['totals']['maxTopLevelCallWallMs']<30000
print('verified: two guest results, q7 equivalence, distinct roots/bindings, six ownership/pre-execution/verifier refusals, ordinary-call wall bound')
