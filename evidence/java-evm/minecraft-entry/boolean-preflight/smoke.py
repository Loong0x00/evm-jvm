#!/usr/bin/env python3
"""Generated Java-8/EVM Boolean and retained System/resource control gate."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys, zipfile

here = Path(__file__).resolve().parent
root = here.parents[3]
build = Path(sys.argv[1]).resolve(); out = Path(sys.argv[2]).resolve()
assert build.name.startswith('java-diff-mc-boolean-') and out.parent == root / 'build' and not out.exists()
out.mkdir(); (out / 'tmp').mkdir(); classes = out / 'classes'; classes.mkdir()
env = dict(os.environ, TMPDIR=str(out / 'tmp'), PYTHONDONTWRITEBYTECODE='1', NODE_PATH=os.environ['NODE_PATH'])
def call(label, args, e=None):
    with (out / (label + '.log')).open('w') as f:
        p = subprocess.Popen(list(map(str, args)), cwd=root, env=e or env, stdout=f, stderr=subprocess.STDOUT)
        rc = p.wait()
    (out / (label + '-process.json')).write_text(json.dumps({'pid':p.pid, 'exit':rc, 'command':list(map(str,args))})+'\n')
    assert rc == 0, (label, rc)
def jar(name, names, resource=False):
    p = out / name
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names:
            i = zipfile.ZipInfo(n, (1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(i, (classes/n).read_bytes())
        if resource:
            i = zipfile.ZipInfo('probe/resource.txt', (1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(i, b'boolean-preflight-resource\n')
    return p
sources = [here / x for x in ('BooleanProbe.java','BooleanHostOracle.java','ParentResourceEnumerationProbe.java','ParentResourceEnumerationHostOracle.java','SystemPropertyHostOracle.java','UnsupportedOpenStreamProbe.java','UnsupportedGetPropertiesProbe.java','UnsupportedSetPropertyProbe.java','UnsupportedClearPropertyProbe.java','UnsupportedBooleanParseProbe.java','UnsupportedBooleanGetBooleanProbe.java')]
call('java8-build', ['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sources])
(classes / 'probe').mkdir(); (classes / 'probe/resource.txt').write_bytes(b'boolean-preflight-resource\n')
call('java8-boolean-oracle', ['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'BooleanHostOracle'])
call('java8-resource-oracle', ['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'ParentResourceEnumerationHostOracle'])
call('java8-property-oracle', ['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'SystemPropertyHostOracle'])
spec = importlib.util.spec_from_file_location('d', here / 'tools/checkpoint_frames.py'); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
rows = {}; baseline = None
boolean_zip = jar('boolean-probe.zip', ['BooleanProbe.class'])
# Clinit, canonical values, public construction, strings, comparison and the
# javac-generated Comparable bridge are all in the single result=127 witness.
for q in (1,7,4096):
    label = 'boolean-q' + str(q); world = out / label
    e = dict(env, MC_ENTRY_BINDINGS='BooleanProbe.class')
    args = [world, build/'coordinator/MCEntryCoordinator.json', build/'engine/MCEntryInterpreter.json', boolean_zip, q]
    for suffix, mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):
        call(label+'-'+suffix, [build/'driver',mode,*args], e)
    h = json.loads((world/'durable-head.json').read_text()); assert h['lifecycle'] == h['outcome'] == 2
    cp = (world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); diag=d.inspect(cp)
    vals=next(x['staticValues'] for x in diag['initialization'] if x['classIndex']==0)
    assert int(vals[-1]['packedValue'],16) & ((1<<64)-1) == 127
    current=(h['machineRoot'], cp[280:])
    if baseline is None: baseline=current
    else: assert current == baseline
    rows[label]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}

# Retain the combined genuine empty System table, resource/URL, ordered-set,
# loader/thread/PA/security/Properties and arraycopy witness through q1/q7/direct.
resource_names=['ParentResourceEnumerationProbe.class','ParentResourceEnumerationProbe$Old.class','ParentResourceEnumerationProbe$New.class','ParentResourceEnumerationProbe$StringAction.class']
resource_zip=jar('retained-resource.zip', resource_names, True)
retained_baseline=None
for q in (1,7,4096):
    label='retained-q'+str(q); world=out/label; e=dict(env,MC_ENTRY_BINDINGS=','.join(resource_names)); args=[world,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',resource_zip,q]
    for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')): call(label+'-'+suffix,[build/'driver',mode,*args],e)
    h=json.loads((world/'durable-head.json').read_text()); cp=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); diag=d.inspect(cp); vals=next(x['staticValues'] for x in diag['initialization'] if x['classIndex']==0); assert int(vals[-1]['packedValue'],16)&((1<<64)-1)==953
    current=(h['machineRoot'],cp[280:]);
    if retained_baseline is None: retained_baseline=current
    else: assert current==retained_baseline
    rows[label]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}

# Omitted APIs and raw wrapper replacement are refusals, never substituted values.
for name,pc in [('UnsupportedGetPropertiesProbe','0'),('UnsupportedSetPropertyProbe','4'),('UnsupportedClearPropertyProbe','2'),('UnsupportedOpenStreamProbe','22'),('UnsupportedBooleanParseProbe','2'),('UnsupportedBooleanGetBooleanProbe','2')]:
    z=jar(name+'.zip',[name+'.class'], name=='UnsupportedOpenStreamProbe'); e=dict(env,MC_ENTRY_BINDINGS=name+'.class')
    call(name+'-start',[build/'driver','setup-chain',out/(name+'-world'),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,4096],e)
    r=json.loads((out/'reports'/(name+'-world')/'start-refusal.json').read_text()); assert r['selector']=='0xd631c3a4' and r['uint256Words']==['3',pc] and r['rootBefore']==r['rootAfter']; rows[name]=r
raw=out/'raw-boolean'; raw.mkdir()
call('raw-boolean-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',raw,here/'RawBooleanReplacementMain.java',here/'Boolean.java'])
with zipfile.ZipFile(out/'raw-boolean.zip','w',zipfile.ZIP_DEFLATED) as z:
    for n in ('RawBooleanReplacementMain.class','java/lang/Boolean.class'): z.writestr(n,(raw/n).read_bytes())
e=dict(env,MC_ENTRY_BINDINGS='RawBooleanReplacementMain.class,java/lang/Boolean.class')
call('raw-boolean-start',[build/'driver','setup-chain',out/'raw-boolean-world',build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',out/'raw-boolean.zip',4096],e)
r=json.loads((out/'reports/raw-boolean-world/start-refusal.json').read_text()); assert r['selector']=='0x6a23ad80' and r['uint256Words']==['1','1'] and r['rootBefore']==r['rootAfter']; rows['rawBooleanReplacement']=r
call('canonical',['node',here/'tools/verify_receipts.js',build,out,1,'boolean-q1','boolean-q7','boolean-q4096','retained-q1','retained-q7','retained-q4096'])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
