#!/usr/bin/env python3
"""Attempt the unchanged server's exact main via the EVM-only opaque archive path."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();jar=Path(sys.argv[2]).resolve();assert not out.exists()
raw=jar.read_bytes();assert len(raw)==30222121 and hashlib.sha256(raw).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e';del raw
subprocess.run([sys.executable,str(here/'build_driver.py'),str(out)],cwd=root,check=True)
env=dict(os.environ,TMPDIR=str(out/'tmp'));a=root/'evidence/java-evm/main-root/session-preflight/artifacts';world=out/'world'
with (out/'attempt.log').open('w') as f:
 p=subprocess.Popen([str(out/'driver'),'setup-chain',str(world),str(a/'coordinator/MR0MainCoordinator.json'),str(a/'engine/MR0MainInterpreter.json'),str(jar),'4096'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
(out/'process.json').write_text(json.dumps({'pid':p.pid,'exit':code,'artifact':str(jar),'bytes':30222121,'sha256':'fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e','budgetPerCall':100000000,'quantum':4096})+'\n');assert code==0
m=json.loads((world/'durable-head.json').read_text());report=out/'reports/world';failure=report/'start-refusal.json'
assert failure.exists(),'Original main did not refuse; inspect actual successful checkpoint before deciding next proof'
f=json.loads(failure.read_text());assert f['rootBefore']==f['rootAfter']==m['trieRoot'] and f['checkpointBytes']==0 and f['candidateHead']==f['candidateCheckpoint']==f['candidateRoot']=='' and 0<f['gas']<=100000000
assert m['totalClassBytes']==34977 and m['classSizes']==[33457,1093,300,127] and m['epoch']==m['jvmSteps']==m['internalSteps']==0
assert [base64.b64decode(n).decode() for n in m['rawNames']]==['net/minecraft/server/MinecraftServer.class','bn.class','tr.class','um.class']
fragments=f['resourceReadReceipts'];expected=[]
for addr,size in zip(m['decoders'],m['classSizes']):
 offset=0
 while offset<size:
  n=min(4096,size-offset);expected.append((addr.lower(),offset,n));offset+=n
assert len(fragments)==len(expected)
for r,want in zip(fragments,expected):assert (r['To'].lower(),r['Offset'],r['Requested'])==want and r['Returned']==r['Requested'] and r['Success']
hashes={k.lower():v for k,v in f['resourceHashes'].items()};assert hashes[m['decoders'][0].lower()]=='246e7916fde4261e776c4beb17c5b7e84a80948c5ce60abf1e8011ca88288b0f'
assert m['counters']['maxGas']<=100000000 and m['counters']['maxCallMs']<=30000
summary={'artifactSHA256':'fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e','classBytes':m['classSizes'],'classTotal':m['totalClassBytes'],'actualEVMReadFragments':len(fragments),'failure':f,'resourceHashes':hashes,'scope':'genuine original main-entry attempt, NOT successful Java execution or Minecraft startup; no official payload archived'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='failure'},indent=2));print(json.dumps({k:f[k] for k in ('error','selector','uint256Words','gas','rootUnchanged')},indent=2))
