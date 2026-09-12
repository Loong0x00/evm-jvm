#!/usr/bin/env python3
"""Verify the opaque density gate without asserting cross-engine root equality."""
from pathlib import Path
import hashlib,json,sys
out=Path(sys.argv[1]).resolve()
d=out/'density'
r=json.loads((d/'report.json').read_text())
assert r['aggregate']==181969 and r['oracle']==23
ordinary=r['ordinary'];assert 'error' not in ordinary and ordinary['budget']==100000000
assert ordinary['slice']['Lifecycle']==2 and ordinary['slice']['Result']==23
assert ordinary['gas']==63660316
rows={}
for q in (1,7):
    a=r['ordinarySliced'][str(q)]
    assert a and 'error' not in a[-1] and a[-1]['slice']['Lifecycle']==2
    last=a[-1]
    for k in ('MachineStateRoot','VFSStateRoot','Result','TotalJvmSteps','TotalInternalSteps'):
        assert last['slice'][k]==ordinary['slice'][k],(q,k)
    # Trace is from the ordinary public EVM calls, not an injected class source.
    for x in a:
        tr=x['trace'];assert tr['enabled'] and tr['rootCalls']==1
        assert len(tr['reads'])==47
        assert all(v['requested']<=4096 and v['requested']==v['returned'] and v['success'] for v in tr['reads'])
    rows[str(q)]={'calls':len(a),'firstGas':a[0]['gas'],'lastGas':last['gas'],
                  'lastEpoch':last['head']['Java']['Epoch'],'readsPerCall':len(last['trace']['reads'])}
# Exact checkpoint payload bytes intentionally differ with distinct epoch/envelope
# binding. Same-engine terminal machine/VFS roots are the permitted comparison.
summary={'aggregate':r['aggregate'],'result':ordinary['slice']['Result'],
 'directGas':ordinary['gas'],'directReads':len(ordinary['trace']['reads']),
 'q':rows,'engine':json.loads((out/'selected-pins.json').read_text()),
 'comparisonCaveat':'engine/config/package/instance roots intentionally differ from old capacity reference; no cross-engine root or checkpoint-byte equality asserted'}
(out/'density-verify.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
