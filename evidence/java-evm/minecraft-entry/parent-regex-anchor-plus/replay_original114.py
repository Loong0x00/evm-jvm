#!/usr/bin/env python3
"""Fresh untouched-original replay or same-domain RUNNING continuation, max-gas q65536.

Read only successful opaque checkpoints. A terminal Java exception is a genuine
committed outcome even when its final slice has0 JVM/positive internal steps.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];MAX=(1<<64)-1
discovery="--discovery" in sys.argv
if discovery:sys.argv.remove("--discovery")
sys.path.insert(0,str(HERE.parent/"perf-replay-discovery"))
from replay_controller import classify_missing_refusal
discovery_name=None
mode,bs,ws,rs,js=sys.argv[1:6];build,world,out,jar=map(lambda s:Path(s).resolve(),(bs,ws,rs,js));assert mode in ('start','continue')
assert build.parent==world.parent.parent==out.parent==ROOT/'build' and not out.exists()
assert hashlib.sha256(jar.read_bytes()).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e'
assert json.load(open(build/'authorization.json'))['gas']==str(MAX)
profile=json.load(open(build/'pins.json'));assert profile['engine']['bytes']<=profile['runtimeCap']
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',GOPROXY='off',GOSUMDB='off')
names=json.load(open(HERE.parent/'parent-original114-objects-super/original114-bindings.json'));assert len(names)==114 and len(set(names))==114
env.update(MC_ENTRY_BINDINGS=','.join(names),MC_ENTRY_SELECTED_RESOURCE='META-INF/log4j-provider.properties')
args=[str(world),str(build/'coordinator/MCEntryCoordinator.json'),str(build/'engine/MCEntryInterpreter.json'),str(jar)]
reports=world.parent/'reports'/world.name;rows=[];q=int(sys.argv[7]) if len(sys.argv)>7 else 65536;assert 1<=q<=65536
limit=int(sys.argv[6]) if len(sys.argv)>6 else 600;began=time.monotonic()
def execute(label,command,timeout=75):
 t=time.monotonic()
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 row={'label':label,'command':list(map(str,command)),'exit':p.returncode,'wallSeconds':time.monotonic()-t};(out/(label+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==0,row;return row
if mode=='start':
 assert not world.exists();execute('setup',[build/'driver','setup-chain',*args,str(q)],timeout=900)
 h=json.load(open(world/'durable-head.json'))
 if (reports/'start-refusal.json').exists():
  r=json.load(open(reports/'start-refusal.json'));assert h['epoch']==0 and r['rootUnchanged'];(out/'summary.json').write_text(json.dumps({'status':'atomic-start-refusal','head':h,'refusal':r},indent=2)+'\n');raise SystemExit('initial start refused; no failed state continuation')
 assert h['epoch']==1 and h['lifecycle'] in (1,2,3)
else:
 assert world.is_dir() and json.load(open(world/'durable-head.json'))['lifecycle']==1,'terminal checkpoint cannot resume'
first=json.load(open(world/'durable-head.json'))
for n in range(1,limit+1):
 before_bytes=(world/'durable-head.json').read_bytes();before=json.loads(before_bytes)
 if before['lifecycle']!=1:break
 refusal=reports/'resume-refusal.json'
 if refusal.exists():
  target=out/f'preexisting-refusal-{n:04d}.json';assert not target.exists();target.write_bytes(refusal.read_bytes());refusal.unlink()
 proc=execute(f'resume-{n:04d}-q{q}',[build/'driver','resume-one-qn',*args,str(q)])
 after=json.load(open(world/'durable-head.json'))
 if refusal.exists():
  r=json.load(open(refusal));assert before_bytes==(world/'durable-head.json').read_bytes();assert r['rootBefore']==r['rootAfter']==before['trieRoot'] and r['rootUnchanged'] and r['durableHeadUnchanged'];(out/f'atomic-{n:04d}-q{q}.json').write_bytes(refusal.read_bytes());row={'call':n,'q':q,'ok':False,'java':before['jvmSteps'],'internal':before['internalSteps'],'selector':r['selector'],'words':r['uint256Words'],'gas':r['gas'],'error':r['error'],'wallSeconds':proc['wallSeconds']};rows.append(row);print(json.dumps(row),flush=True)
  if discovery:
   name=classify_missing_refusal(r,before_bytes,before,MAX)
   if name is not None:
    discovery_name=name
    (out/'discovery-successful-head-before-refusal.json').write_bytes(before_bytes)
    break
  if q==1:break
  q=max(1,q//2);continue
 assert after['epoch']==before['epoch']+1
 dj=after['jvmSteps']-before['jvmSteps'];di=after['internalSteps']-before['internalSteps'];assert 0<=dj<=q and 0<=di<=4096 and dj+di>0
 r=json.load(open(reports/f"slice-{after['epoch']:020d}.json"));assert r['suppliedGas']==MAX and r['executionBudget']=='LOCAL-U64MAX-USER-AUTHORIZED' and r['elapsedMS']<=60000
 cp=world/'checkpoints'/(after['checkpointSHA256']+'.bin');assert hashlib.sha256(cp.read_bytes()).hexdigest()==after['checkpointSHA256']
 row={'call':n,'q':q,'ok':True,'epoch':after['epoch'],'java':after['jvmSteps'],'internal':after['internalSteps'],'deltaJvm':dj,'deltaInternal':di,'lifecycle':after['lifecycle'],'gas':r['gasUsed'],'elapsedMS':r['elapsedMS'],'checkpointBytes':r['checkpointBytes']};rows.append(row)
 if n%20==0 or after['lifecycle']!=1:print(json.dumps(row),flush=True)
 if after['lifecycle']!=1:break
 # Do not re-grow during an atomic-refusal localization; that repeats expensive calls.
 if not (mode=='continue' and int(sys.argv[7])<65536 if len(sys.argv)>7 else False) and not any(not x['ok'] for x in rows): q=min(65536,q*2)
if discovery_name is None:execute('reopen',[build/'driver','verify',*args,str(q)])
last=json.load(open(world/'durable-head.json'));summary={'schema':1,'gas':str(MAX),'maxQuantum':65536,'wallSeconds':time.monotonic()-began,'firstHead':first,'lastHead':last,'rows':rows,'discoveryMode':discovery,'discoveryMissingName':discovery_name,'finalAcceptanceEligible':not discovery,'q1FrontierAcceptance':not discovery and bool(rows) and not rows[-1]['ok'] and rows[-1]['q']==1,'nextPreciseQuantum':max(1,q//2) if discovery_name else q,'status':'discovery-missing-class' if discovery_name else ('terminal' if last['lifecycle']!=1 else ('atomic-q1-refusal' if rows and not rows[-1]['ok'] and rows[-1]['q']==1 else 'bounded-running-window'))};(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k] for k in ('status','wallSeconds')}|{'java':last['jvmSteps'],'internal':last['internalSteps'],'epoch':last['epoch'],'lifecycle':last['lifecycle']}),flush=True)
