#!/usr/bin/env python3
"""Reproducible generated-fixture EVM smoke with a whole process-group watchdog.
No original archive path is accepted by this script."""
import json, os, pathlib, resource, signal, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parents[4]
here=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]).resolve()
if out.exists(): raise SystemExit('refuse existing output')
out.mkdir(parents=True); (out/'tmp').mkdir()
env=dict(os.environ, TMPDIR=str(out/'tmp'), PYTHONDONTWRITEBYTECODE='1')
def run(label, argv):
    start=time.monotonic(); peak=0; samples=[]
    with (out/(label+'.log')).open('wb') as log:
        p=subprocess.Popen([str(x) for x in argv],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        pgid=os.getpgid(p.pid)
        try:
            while p.poll() is None:
                if time.monotonic()-start > 1200: raise TimeoutError('20min group limit')
                rss=0; members=[]
                for d in pathlib.Path('/proc').glob('[0-9]*'):
                    try:
                        stat=(d/'stat').read_text().split(); status=(d/'status').read_text()
                        if int(stat[4]) != pgid: continue
                        kb=next(int(x.split()[1]) for x in status.splitlines() if x.startswith('VmRSS:'))
                        rss += kb*1024; members.append(int(d.name))
                    except (OSError,ValueError,StopIteration): pass
                peak=max(peak,rss); samples.append({'seconds':round(time.monotonic()-start,3),'rssBytes':rss,'pids':members})
                if rss > 4*1024**3: raise MemoryError('4GiB group limit')
                time.sleep(.1)
        except BaseException:
            os.killpg(pgid,signal.SIGKILL); p.wait(); raise
        code=p.wait()
    report={'label':label,'command':[str(x) for x in argv],'pgid':pgid,'exit':code,'elapsedSeconds':round(time.monotonic()-start,6),'peakRSSBytes':peak,'samples':samples}
    (out/(label+'-watchdog.json')).write_text(json.dumps(report,indent=2)+'\n')
    if code: raise SystemExit(label+' failed')
D=here; driver=out/'driver'; fixtures=out/'fixtures'; worlds=out/'worlds'; worlds.mkdir()
# The caller supplies the pinned local solc module through NODE_PATH; fail rather
# than downloading a compiler or using a host substitute.
if not env.get('NODE_PATH'): raise SystemExit('set NODE_PATH to pinned solc module')
run('engine-build',['node',D/'engine/build.js'])
run('coordinator-build',['node',D/'coordinator/build.js'])
run('go-build',['go','build','-o',driver,D/'driver.go'])
run('fixtures',[sys.executable,D/'fixtures/generate-platform-map.py',fixtures])
coord=D/'coordinator/MCEntryCoordinator.json'; engine=D/'engine/MCEntryInterpreter.json'
def world(label,zipname,q,finish=True):
    args=[driver,'setup-chain',worlds/label,coord,engine,fixtures/zipname,str(q)]
    run(label+'-setup',args)
    if finish:
        run(label+'-finish',[driver,'finish',worlds/label,coord,engine,'x','1'])
        run(label+'-verify',[driver,'verify',worlds/label,coord,engine,'x','1'])
world('platform-map-q4096','platform-map.zip',4096,False) # measured ordinary-cap direct refusal
for q in (1,7): world('platform-map-q'+str(q),'platform-map.zip',q)
summary={}
for d in sorted(worlds.iterdir()):
    m=json.loads((d/'durable-head.json').read_text()); f=d/'start-refusal.json'
    summary[d.name]={'manifest':m,'startRefusal':json.loads(f.read_text()) if f.exists() else None}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
