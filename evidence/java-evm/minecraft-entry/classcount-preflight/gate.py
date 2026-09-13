#!/usr/bin/env python3
"""Fresh generated-only q1/q7/direct/reopen gate for the isolated count-24 COPY."""
from pathlib import Path
import hashlib,importlib.util,json,os,signal,subprocess,sys,time

here=Path(__file__).resolve().parent
root=here.parents[3]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent == root/'build' and fixtures.parent == root/'build' and out.parent == root/'build'
assert build.name.startswith('java-diff-mc-classcount-') and fixtures.name.startswith('java-diff-mc-classcount-') and out.name.startswith('java-diff-mc-classcount-') and not out.exists()
out.mkdir(); (out/'logs').mkdir(); deadline=time.monotonic()+1200; peak=0; commands=[]

def group_rss(pgid):
    total=0
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            if os.getpgid(int(entry.name)) != pgid: continue
            for line in (entry/'status').read_text().splitlines():
                if line.startswith('VmRSS:'): total+=int(line.split()[1])*1024; break
        except (FileNotFoundError,ProcessLookupError,PermissionError): pass
    return total

def run(label,args,env=None):
    global peak
    log=out/'logs'/(label+'.log'); started=time.monotonic()
    e=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
    if env: e.update(env)
    (out/'tmp').mkdir(exist_ok=True)
    with log.open('w') as f:
        p=subprocess.Popen([str(x) for x in args],cwd=root,env=e,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        while p.poll() is None:
            peak=max(peak,group_rss(p.pid))
            if time.monotonic()>deadline or peak>4*1024**3:
                os.killpg(p.pid,signal.SIGKILL); p.wait()
                raise RuntimeError('whole gate deadline/RSS exceeded')
            time.sleep(.05)
    receipt={'label':label,'command':[str(x) for x in args],'exit':p.returncode,'elapsedSeconds':time.monotonic()-started,'processGroup':p.pid}
    commands.append(receipt)
    (out/'logs'/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    if p.returncode: raise RuntimeError(label+' failed; inspect '+str(log))

def entries(n): return ','.join(json.loads((fixtures/(str(n)+'.json')).read_text())['entries'])

def report(world): return world.parent/'reports'/world.name

def verify(n,q,world):
    h=json.loads((world/'durable-head.json').read_text())
    assert h['lifecycle']==h['outcome']==2 and h['result']==0 and h['javaKind']==h['javaRef']==0 and not h['javaClass']
    assert len(h['decoders'])==n and h['totalClassBytes']<=262144 and h['counters']['timeoutCancels']==0
    rp=report(world); slices=sorted(rp.glob('slice-*.json')); assert len(slices)==h['epoch'] and h['epoch']>0
    j=i=0
    for at,p in enumerate(slices,1):
        x=json.loads(p.read_text()); s=x['slice']
        assert x['epoch']==s['epoch']==at and 0<x['gasUsed']<=100000000 and x['elapsedMS']<=30000 and len(x['nestedLogs'])==1
        assert s['executedJvmSteps']<=q and s['executedInternalSteps']<=4096 and s['totalJvmSteps']==j+s['executedJvmSteps'] and s['totalInternalSteps']==i+s['executedInternalSteps']
        j,i=s['totalJvmSteps'],s['totalInternalSteps']
    assert (j,i)==(h['jvmSteps'],h['internalSteps'])
    cp=world/'checkpoints'/(h['checkpointSHA256']+'.bin'); raw=cp.read_bytes(); assert hashlib.sha256(raw).hexdigest()==h['checkpointSHA256']
    diag.inspect(raw)
    # Raw user image indices are CountMain, all actively invoked TailXX, then supplied Runnable.
    active={x['classIndex'] for x in diag.inspect(raw)['initialization'] if x['state']==2}
    assert set(range(0,n-1)).issubset(active),('selected tail class not initialized',n,active)
    sentinel=next(x for x in diag.inspect(raw)['initialization'] if x['classIndex']==0)['staticValues'][0]['packedValue']
    tails=n-2; assert int(sentinel,16)&((1<<64)-1)==tails*(tails+1)//2+2
    return {'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'checkpointSHA256':h['checkpointSHA256'],'opaquePayloadSHA256':hashlib.sha256(raw[280:]).hexdigest(),'sentinelLow64':int(sentinel,16)&((1<<64)-1),'counters':h['counters']}

spec=importlib.util.spec_from_file_location('checkpoint_diagnostic',here/'checkpoint_diagnostic.py'); diag=importlib.util.module_from_spec(spec); spec.loader.exec_module(diag)
driver=build/'driver'; coord=build/'coordinator/MCEntryCoordinator.json'; engine=build/'engine/MCEntryInterpreter.json'
summary={'profile':'MC-CLASSCOUNT24-PREFLIGHT1','successful':{},'ordinaryReserveRefusals':[]}
for n in (17,18,24):
    baseline=None
    for q in (1,7,4096):
        world=out/('world-%d-q%d'%(n,q)); env={'MC_ENTRY_BINDINGS':entries(n)}
        args=[driver,'setup-chain',world,coord,engine,fixtures/(str(n)+'.zip'),str(q)]
        run('%d-q%d-start'%(n,q),args,env)
        assert not (report(world)/'start-refusal.json').exists()
        run('%d-q%d-finish'%(n,q),[driver,'finish',world,coord,engine,fixtures/(str(n)+'.zip'),str(q)],env)
        run('%d-q%d-verify-fresh-process'%(n,q),[driver,'verify',world,coord,engine,fixtures/(str(n)+'.zip'),str(q)],env)
        result=verify(n,q,world)
        if baseline is None: baseline=result
        else:
            for field in ('machineRoot','opaquePayloadSHA256','sentinelLow64'): assert result[field]==baseline[field],(n,q,field,result,baseline)
        summary['successful']['%d/q%d'%(n,q)]=result
# The twenty-fifth generated binding reaches ordinary EVM CREATE and is rejected by the coordinator constructor.
env={'MC_ENTRY_BINDINGS':entries(25),'MC_ENTRY_ALLOW_BOUNDARY_25':'1'}; world=out/'boundary-25'
run('boundary25-actual-evm',[driver,'boundary-25',world,coord,engine,fixtures/'25.zip','4096'],env)
b=json.loads((report(world)/'boundary25-refusal.json').read_text())
assert b['bindingCount']==25 and b['kind']=='actual EVM coordinator constructor count refusal' and b['selector']=='0xab23ed08' and b['rootUnchanged'] and b['ordinaryGas']==100000000
summary['boundary25']=b
summary['commands']=commands; summary['wholeGateSeconds']=1200-(deadline-time.monotonic()); summary['sampledProcessGroupPeakRSSBytes']=peak
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
