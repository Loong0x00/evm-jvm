#!/usr/bin/env python3
"""Generated-fixture EVM smoke under one 20-minute/4-GiB process-group watchdog.
No original archive path is accepted; the host JVM is a TEST-only oracle."""
import json, os, pathlib, signal, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parents[4]
here=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]).resolve()

def members(pgid):
    rss=0; pids=[]
    for d in pathlib.Path('/proc').glob('[0-9]*'):
        try:
            stat=(d/'stat').read_text().split(); status=(d/'status').read_text()
            if int(stat[4]) != pgid: continue
            kb=next(int(x.split()[1]) for x in status.splitlines() if x.startswith('VmRSS:'))
            rss += kb*1024; pids.append(int(d.name))
        except (OSError,ValueError,StopIteration): pass
    return rss,pids

def supervise():
    if out.exists(): raise SystemExit('refuse existing output')
    env=dict(os.environ, MC_ARRAYCOPY_WORKER='1', PYTHONDONTWRITEBYTECODE='1')
    # One child session owns every compiler, fixture, Go and EVM process.  Its
    # stdout is not a pipe; command logs are file-backed in the worker instead.
    start=time.monotonic()
    p=subprocess.Popen([sys.executable, __file__, str(out)],cwd=root,env=env,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    pgid=os.getpgid(p.pid); peak=0; samples=[]; failure=None
    while p.poll() is None:
        elapsed=time.monotonic()-start; rss,pids=members(pgid)
        peak=max(peak,rss); samples.append({'seconds':round(elapsed,3),'rssBytes':rss,'pids':pids})
        if elapsed > 1200: failure='20min group limit'
        if rss > 4*1024**3: failure='4GiB group limit'
        if failure:
            os.killpg(pgid,signal.SIGKILL); p.wait(); break
        time.sleep(.1)
    code=p.wait()
    if out.exists():
        (out/'whole-watchdog.json').write_text(json.dumps({
            'command':[sys.executable,__file__,str(out)],'pgid':pgid,'exit':code,
            'elapsedSeconds':round(time.monotonic()-start,6),'peakRSSBytes':peak,
            'samples':samples,'failure':failure},indent=2)+'\n')
    if failure or code: raise SystemExit(f'whole smoke failed: {failure or code}')

def worker():
    if out.exists(): raise SystemExit('refuse existing output')
    out.mkdir(parents=True); (out/'tmp').mkdir()
    env=dict(os.environ, TMPDIR=str(out/'tmp'), PYTHONDONTWRITEBYTECODE='1')
    def run(label, argv):
        start=time.monotonic()
        with (out/(label+'.log')).open('wb') as log:
            p=subprocess.run([str(x) for x in argv],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        report={'label':label,'command':[str(x) for x in argv],'exit':p.returncode,
                'elapsedSeconds':round(time.monotonic()-start,6)}
        (out/(label+'-receipt.json')).write_text(json.dumps(report,indent=2)+'\n')
        if p.returncode: raise SystemExit(label+' failed')
    D=here; driver=out/'driver'; fixtures=out/'fixtures'; worlds=out/'worlds'; worlds.mkdir()
    if not env.get('NODE_PATH'): raise SystemExit('set NODE_PATH to pinned solc module')
    run('engine-build',['node',D/'engine/build.js'])
    run('coordinator-build',['node',D/'coordinator/build.js'])
    run('go-build',['go','build','-o',driver,D/'driver.go'])
    run('fixtures',[sys.executable,D/'fixtures/generate-arraycopy.py',fixtures])
    coord=D/'coordinator/MCEntryCoordinator.json'; engine=D/'engine/MCEntryInterpreter.json'
    def world(label,q,finish=True):
        run(label+'-setup',[driver,'setup-chain',worlds/label,coord,engine,fixtures/'arraycopy.zip',str(q)])
        if finish:
            run(label+'-finish',[driver,'finish',worlds/label,coord,engine,'x','1'])
            run(label+'-verify',[driver,'verify',worlds/label,coord,engine,'x','1'])
    world('arraycopy-q4096',4096,False) # retain an actual refusal if direct reaches one
    for q in (1,7): world('arraycopy-q'+str(q),q)
    summary={}
    for d in sorted(worlds.iterdir()):
        m=json.loads((d/'durable-head.json').read_text()); f=d/'start-refusal.json'
        summary[d.name]={'manifest':m,'startRefusal':json.loads(f.read_text()) if f.exists() else None}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')

if os.environ.get('MC_ARRAYCOPY_WORKER') == '1': worker()
else: supervise()
