#!/usr/bin/env python3
"""Strict verifier: every reported gas, grouping, root, and refusal claim is asserted."""
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]).resolve(); r=out/'results'; f=json.loads((out/'fixture'/'fixture.json').read_text())
assert f['javac']=='javac 1.8.0_504' and f['oracle']=='10724\n41\n10731\n41\n',f
for name,digest in f['files'].items():
 p=out/'fixture'/('classes' if name.endswith('.class') else '')/name
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
# Generated-only javap is evidence that all three demand opcodes share the omitted class;
# the omitted declaration has a CP class entry but mode 0 never executes it.
javap=(out/'fixture'/'javap-DemandEntry.txt').read_text()
for text in ('Class              #18            // MissingTarget','invokestatic','new           #3','checkcast     #3'): assert text in javap,text

def j(name): return json.loads((r/name).read_text())
def ordinary(x): assert 0 < x['gasUsed'] <= 100000000,x
closed0=j('closed-direct0.json'); assert (closed0['lifecycle'],closed0['result'],closed0['totalJvmSteps'],closed0['totalInternalSteps'])==(2,10724,44,6),closed0
closed=j('closed-direct7.json'); assert (closed['lifecycle'],closed['result'],closed['totalJvmSteps'],closed['totalInternalSteps'])==(2,10731,44,6),closed
assert closed['nestedEngineLogs']==1 and not closed['reopenedEngineInstalled']
q1=[j('closed-q1-%d.json'%i) for i in range(1,45)]
assert [x['epoch'] for x in q1]==list(range(1,45)) and len({x['pid'] for x in q1})==44
last=q1[-1]
for key in ('machineRoot','vfsRoot','packageRoot','as0ContentRoot','indexRoot','decoderRoots'):
 assert last[key]==closed[key],(key,last[key],closed[key])
assert (last['lifecycle'],last['result'],last['totalJvmSteps'],last['totalInternalSteps'])==(2,10731,44,6)
for x in [closed0,closed]+q1: ordinary(x)
# Demand mode 0 proves the loaded class can leave MissingTarget's CP reference unused.
d0=j('demand-0.json'); assert (d0['lifecycle'],d0['result'])==(2,41); ordinary(d0)
# Exact EVM LinkError(4, PC) is binding only when each symbolic reference executes.
for mode,pc in ((1,'12'),(2,'21'),(3,'38')):
 x=j('demand-%d-refusal.json'%mode)
 assert (x['selector'],x['code'],x['detail'])==('0x427cfac5','4',pc),x
 assert x['stateUnchanged'] and x['beforeEpoch']==0 and x['afterEpoch']==0,x; ordinary(x)
# Omitted superclass binds during hierarchy validation; omitted interface maps to current
# LinkError(4,0), not a forged Java exception.
sup=j('super-refusal.json'); assert (sup['selector'],sup['code'],sup['detail'])==('0xa52e829f','1','0') and sup['stateUnchanged']; ordinary(sup)
inter=j('interface-refusal.json'); assert (inter['selector'],inter['code'],inter['detail'])==('0x427cfac5','4','0') and inter['stateUnchanged']; ordinary(inter)
# Five successful q1 EVM-issued checkpoints remain routable after resume refusal.
prior=[j('demand-q1-%d.json'%i) for i in range(1,6)]
assert [x['epoch'] for x in prior]==[1,2,3,4,5] and len({x['pid'] for x in prior})==5
for x in prior: assert x['lifecycle']==1 and x['nestedEngineLogs']==1; ordinary(x)
fail=j('demand-q1-6.json'); after=j('demand-q1-after.json')
assert (fail['selector'],fail['code'],fail['detail'])==('0x427cfac5','4','12') and fail['stateUnchanged']; ordinary(fail)
assert after['epoch']==5 and after['lifecycle']==1 and after['checkpointRoot']==prior[-1]['checkpointRoot']==fail['afterCheckpointRoot'],(after,fail)
cap=j('fifth-capacity.json')
assert cap['command']=='fifth-class-refusal' and cap['decoderCount']==4 and cap['stateUnchanged'] and cap['gasUsed']==0 and 'decoder slot is not next bounded slot' in cap['error'],cap
print(json.dumps({'fixture':f,'closedGraph':{'result':closed['result'],'directSlices':1,'q1Slices':44,'unicodeUTF16':['U+03BB','U+2603']},'demandRefusals':{str(m):j('demand-%d-refusal.json'%m) for m in (1,2,3)},'hierarchyRefusals':{'super':sup,'interface':inter},'survivingCheckpoint':after,'fifthClassFrontier':cap,'gas':'Every EVM Start/Resume/refusal call asserted ordinary <=100000000; capacity gate is an API pre-EVM guard with measured gas 0; no 1B calls.'},indent=2,sort_keys=True))
