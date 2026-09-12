#!/usr/bin/env python3
"""Strict receipt-only verifier for MR0 transport preflight evidence."""
import json,pathlib
p=pathlib.Path(__file__).parent/'results'
def load(n): return json.loads((p/n).read_text())
def same(a,b):
    assert a['rootBefore']==a['rootAfter'] and a['rootUnchanged']
over=load('positive-overload-start-refusal.json')
assert over['selector']=='0x166ac6c3' and over['uint256Words']==['2'] and over['actualDI0ReadSizes']==[566,286]; same(over,None)
reb=load('rebind-q1-resume-refusal.json')
assert reb['selector']=='0x71540d20' and reb['uint256Words']==['7','0'] and reb['epoch']==3; same(reb,None)
for q,epoch in ((1,19),(7,3)):
    w=load(f'exception-q{q}-world-report.json')
    m=w['manifest']; assert m['lifecycle']==3 and m['epoch']==epoch and m['javaKind']==0
    assert w['engineHeadEpoch']==epoch and w['engineHeadLifecycle']==3
    assert m['engineCodeHash']=='0x463dd2419b296aa39f766bdae06d11b49b9cffa935d052a38fe82921757e29de'
    assert len(m['processPids'])>=3 and m['counters']['actualDI0ReadSizes']==[231]*epoch
print('strict receipt checks passed')
