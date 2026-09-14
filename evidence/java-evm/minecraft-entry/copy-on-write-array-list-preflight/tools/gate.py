#!/usr/bin/env python3
"""Generated-only q1/q7/direct/reopen COW bootstrap gate; no original inputs."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time,zipfile
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and not out.exists()
out.mkdir(); (out/'logs').mkdir(); start=time.monotonic(); rows={}; commands=[]
spec=importlib.util.spec_from_file_location('cow_checkpoint_diagnostic',here/'checkpoint_diagnostic.py'); diagnostic=importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver=build/'driver'; coord=build/'coordinator/MCEntryCoordinator.json'; engine=build/'engine/MCEntryInterpreter.json'; bundle=fixtures/'copy-on-write.zip'

def run(label,args,names='CopyOnWriteArrayListMain.class'):
    env=dict(os.environ,MC_ENTRY_BINDINGS=names,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
    (out/'tmp').mkdir(exist_ok=True); log=out/'logs'/(label+'.log'); then=time.monotonic()
    with log.open('w') as f: process=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
    row={'label':label,'command':list(map(str,args)),'exit':process.returncode,'seconds':time.monotonic()-then}; commands.append(row); assert process.returncode==0,row

def terminal(world):
    head=json.loads((world/'durable-head.json').read_text()); assert head['lifecycle']==head['outcome']==2 and head['result']==0
    checkpoint=(world/'checkpoints'/(head['checkpointSHA256']+'.bin')).read_bytes(); meta=diagnostic.inspect(checkpoint)
    assert 76<=meta['classCount']<=100
    return {'machineRoot':head['machineRoot'],'checkpointSHA256':hashlib.sha256(checkpoint).hexdigest(),'opaquePayloadSHA256':hashlib.sha256(checkpoint[280:]).hexdigest(),'epoch':head['epoch'],'jvmSteps':head['jvmSteps'],'internalSteps':head['internalSteps'],'classCount':meta['classCount'],'initialization':meta['initialization']}

# The fixture's guest Java assertions cover hierarchy checks, inherited isEmpty, duplicate
# and null additions, snapshot isolation/order and both exhaustion paths.
baseline=None
for quantum in (1,7,4096):
    world=out/('core-q'+str(quantum))
    run('core-q%d-start'%quantum,[driver,'setup-chain',world,coord,engine,bundle,str(quantum)])
    run('core-q%d-finish'%quantum,[driver,'finish',world,coord,engine,bundle,str(quantum)])
    run('core-q%d-reopen'%quantum,[driver,'verify',world,coord,engine,bundle,str(quantum)])
    got=terminal(world); rows['core/q'+str(quantum)]=got
    if baseline is None: baseline=got
    else:
        for key in ('machineRoot','opaquePayloadSHA256'): assert got[key]==baseline[key],(quantum,key)

# A raw class with each new platform binary name must be refused before a head mutation.
def raw_replacement(label,target):
    work=out/('raw-'+label); work.mkdir(); api=work/'rt.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
    subprocess.run(['zip','-q','-d',api,target],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    source=stage/'fixtures/replacements'/target.replace('.class','.java')
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',work,stage/'fixtures/RawCopyOnWriteReplacementMain.java',source],check=True)
    archive=work/'raw.zip'
    names=['RawCopyOnWriteReplacementMain.class',target]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as f:
        for name in names: f.writestr(name,(work/name).read_bytes())
    world=out/('raw-world-'+label)
    run('raw-'+label,[driver,'setup-chain',world,coord,engine,archive,'4096'],','.join(names))
    refusal=json.loads((out/'reports'/world.name/'start-refusal.json').read_text())
    assert refusal['rootBefore']==refusal['rootAfter'] and refusal['selector']=='0x6a23ad80' and refusal['uint256Words']==['1','1']
    rows['raw/'+label]=refusal

for label,target in (
    ('list','java/util/List.class'),('random-access','java/util/RandomAccess.class'),
    ('copy-on-write-array-list','java/util/concurrent/CopyOnWriteArrayList.class'),
    ('copy-on-write-array-list-iterator','java/util/concurrent/CopyOnWriteArrayListIterator.class'),
): raw_replacement(label,target)
summary={'profile':'MC-COPY-ON-WRITE-ARRAY-LIST-PREFLIGHT1','generatedOnly':True,'hostOracle':json.loads((fixtures/'summary.json').read_text())['hostJava8Oracle'],'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start,'caveat':'This focused worker gate does not claim the expensive COW array-quota exhaustion or retained Class.newInstance/prior-profile reruns; those remain parent reruns.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
