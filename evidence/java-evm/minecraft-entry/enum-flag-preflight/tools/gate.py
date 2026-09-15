#!/usr/bin/env python3
"""Generated-only class-count29 EVM gate; no original JAR/class/world input."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
here=Path(__file__).resolve().parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and out.name.startswith('java-diff-mc-enum-flag-') and not out.exists()
out.mkdir(); logs=out/'logs';logs.mkdir();start=time.monotonic();commands=[]
def names(label):return ','.join(json.loads((fixtures/(label+'.json')).read_text())['entries'])
def run(label,args,bindings=None,expect=0):
 env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1');out.joinpath('tmp').mkdir(exist_ok=True)
 if bindings:env['MC_ENTRY_BINDINGS']=names(bindings)
 log=logs/(label+'.log'); t=time.monotonic()
 with log.open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'label':label,'command':list(map(str,args)),'exit':p.returncode,'elapsedSeconds':time.monotonic()-t};commands.append(row);(logs/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==expect,(label,p.returncode,log)
def report(w):return w.parent/'reports'/w.name
def failure(w,name):return json.loads((report(w)/name).read_text())
def words(x):return list(map(str,x['uint256Words']))
def inspect(world,n,q):
 h=json.loads((world/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['result']==0 and len(h['decoders'])==n and h['totalClassBytes']<=262144
 cp=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256']
 d.inspect(cp); active={x['classIndex'] for x in d.inspect(cp)['initialization'] if x['state']==2};assert set(range(n)).issubset(active),(n,q,active)
 return {'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'totalClassBytes':h['totalClassBytes'],'counters':h['counters']}
spec=importlib.util.spec_from_file_location('checkpoint_diagnostic',here/'checkpoint_diagnostic.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
driver=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json';rows={}
# Exact below-cap and new-cap packages use one uninterrupted q4096 direct run and
# independent q1/q7 checkpoint/reopen chains.  Canonical terminal machine and opaque
# blobs must be quantum invariant; reordered raw bindings are intentionally distinct.
for n in (28,29):
 baseline=None
 for tag,q in (('q1',1),('q7',7),('direct',4096)):
  w=out/('world-%d-%s'%(n,tag));a=[driver,'setup-chain',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)]
  run('%d-%s-start'%(n,tag),a,str(n));run('%d-%s-finish'%(n,tag),[driver,'finish',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)],str(n));run('%d-%s-reopen'%(n,tag),[driver,'verify',w,coord,engine,fixtures/(str(n)+'.zip'),str(q)],str(n))
  x=inspect(w,n,q);rows['%d/%s'%(n,tag)]=x
  if baseline is None:baseline=x
  else:
   for k in ('machineRoot','opaquePayloadSHA256'):assert x[k]==baseline[k],(n,tag,k)
w=out/'world-29-reordered';run('29-reordered-start',[driver,'setup-chain',w,coord,engine,fixtures/'29.zip','4096'],'29-reordered');run('29-reordered-finish',[driver,'finish',w,coord,engine,fixtures/'29.zip','4096'],'29-reordered');run('29-reordered-reopen',[driver,'verify',w,coord,engine,fixtures/'29.zip','4096'],'29-reordered');x=inspect(w,29,4096);h=json.loads((w/'durable-head.json').read_text());base=json.loads((out/'world-29-direct/durable-head.json').read_text());assert h['packageRoot']!=base['packageRoot'];x['packageRoot']=h['packageRoot'];rows['29/reordered']=x
# Product driver guard refuses 30 before newEnv/world installation.
w=out/'world-30-driver';run('30-driver-pre-mutation-refusal',[driver,'setup-chain',w,coord,engine,fixtures/'30.zip','4096'],'30',expect=2);assert not w.exists();rows['30/driver']={'layer':'driver','worldExists':False}
# Clone only the generated test transport guard to reach the unchanged product
# coordinator constructor; its code hash and all production pins remain exact.
def test_driver(label, coordinator_art, coordinator_keccak):
 src=(here/'Go.txt').read_text().replace('> 29','> 30').replace(json.loads((here.parent/'pins.json').read_text())['coordinator']['runtimeKeccak256'],coordinator_keccak)
 path=out/(label+'.go');path.write_text(src)
 exe=out/label
 subprocess.run(['gofmt','-w',str(path)],cwd=root,check=True)
 subprocess.run(['go','build','-trimpath','-o',str(exe),str(path)],cwd=root,check=True)
 return exe
coord_driver=test_driver('coordinator-30-driver',coord,json.loads((here.parent/'pins.json').read_text())['coordinator']['runtimeKeccak256'])
w=out/'world-30-coordinator';run('30-coordinator-atomic-refusal',[coord_driver,'boundary-create',w,coord,engine,fixtures/'30.zip','4096'],'30');b=failure(w,'boundary-refusal.json');assert b['selector']=='0xab23ed08' and words(b)==['2'] and b['rootUnchanged'];rows['30/coordinator']=b
# A mechanically widened, disposable coordinator is used solely to expose the
# immutable product engine's raw-class cap.  The product engine rejects 30 and the
# normal call reports an unchanged pre-call root; no modified runtime is a product pin.
probe=out/'engine-30-coordinator';shutil.copytree(here.parent/'coordinator',probe)
p=probe/'MCEntryCoordinator.sol';p.write_text(p.read_text().replace('[29]','[30]').replace('n > 29','n > 30'))
env=dict(os.environ,NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules',TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
with (logs/'30-engine-coordinator-build.log').open('w') as f:subprocess.run(['node',str(probe/'build.js')],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
probe_art=probe/'MCEntryCoordinator.json';probe_keccak=json.loads(probe_art.read_text())['codeHashes']['runtimeKeccak256'];engine_driver=test_driver('engine-30-driver',probe_art,probe_keccak)
w=out/'world-30-engine';run('30-engine-atomic-refusal',[engine_driver,'setup-chain',w,probe_art,engine,fixtures/'30.zip','4096'],'30');b=failure(w,'start-refusal.json');assert b['selector']=='0x427cfac5' and words(b)==['1','30'] and b['rootUnchanged'];rows['30/engine']=b
# Exact aggregate byte boundary reaches the honest parser; +1 is rejected by the
# independent coordinator aggregate guard before any engine execution.
w=out/'world-29-262144';run('262144-start',[driver,'setup-chain',w,coord,engine,fixtures/'29-262144.zip','4096'],'29-262144');b=failure(w,'start-refusal.json');assert b['selector']=='0x71540d20' and words(b)==['1','0'] and b['rootUnchanged'];rows['29/262144-infeasible']=b
w=out/'world-29-262145';run('262145-constructor-refusal',[driver,'boundary-create',w,coord,engine,fixtures/'29-262145.zip','4096'],'29-262145');b=failure(w,'boundary-refusal.json');assert b['selector']=='0xab23ed08' and words(b)==['12'] and b['rootUnchanged'];rows['29/262145']=b
summary={'profile':'MC-ENUM-FLAG-PARENT1','generatedOnly':True,'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
