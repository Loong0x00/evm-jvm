#!/usr/bin/env python3
"""Independent narrow smoke then original archive frontier; not a generic Session gate."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();jar=Path(sys.argv[2]).resolve();assert not out.exists();assert hashlib.sha256(jar.read_bytes()).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e'
subprocess.run([sys.executable,str(here/'rebuild.py'),str(out)],cwd=root,check=True)
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def command(label,argv,extra=None):
 e=dict(env);e.update(extra or {})
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,argv)),cwd=root,env=e,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'command':list(map(str,argv))})+'\n');assert code==0,(label,code)
 return p.pid
command('fixtures',[sys.executable,root/'evidence/java-evm/minecraft-entry/runtime-preflight/fixtures/generate-positive-exception.py',out/'fixtures'])
engine=out/'engine/MCEntryInterpreter.json';coord=out/'coordinator/MCEntryCoordinator.json';exe=out/'driver';summaries={}
def world(label,z,names,q,finish):
 w=out/label;args=[w,coord,engine,z,q];extras={'MC_ENTRY_BINDINGS':','.join(names)}
 command(label+'-setup',[exe,'setup-chain']+args,extras)
 rp=out/'reports'/label;failure=rp/'start-refusal.json';m=json.loads((w/'durable-head.json').read_text())
 if failure.exists():
  f=json.loads(failure.read_text());assert f['rootBefore']==f['rootAfter']==m['trieRoot'] and m['epoch']==0 and f['checkpointBytes']==0 and 0<f['gas']<=100000000
  summaries[label]={'classBytes':m['classSizes'],'totalBytes':m['totalClassBytes'],'failure':f,'scope':'real EVM refusal, no checkpoint accepted'};return
 if finish:
  command(label+'-finish',[exe,'finish']+args,extras);command(label+'-verify',[exe,'verify']+args,extras)
  m=json.loads((w/'durable-head.json').read_text())
 r=json.loads((rp/'slice-00000000000000000001.json').read_text());cp=(w/'checkpoints'/(r['checkpointSHA256']+'.bin')).read_bytes()
 assert hashlib.sha256(cp).hexdigest()==r['checkpointSHA256'] and r['slice']['schema']==1 and len(r['nestedLogs'])==1 and 0<r['gasUsed']<=100000000
 summaries[label]={'classBytes':m['classSizes'],'totalBytes':m['totalClassBytes'],'start':r,'head':m,'firstCheckpointSHA256':hashlib.sha256(cp).hexdigest(),'scope':'actual successful EVM-issued checkpoint; execution attribution must be inspected'}
for kind,names,steps,internal in [('positive',['MainPositive.class','MainHelper.class'],319,3),('runnable',['MainRunnable.class','RunImpl.class'],14,4),('exception',['MainException.class'],18,5)]:
 for q in (1,7):
  label=kind+'-q'+str(q);world(label,out/'fixtures'/(kind+'.zip'),names,q,True)
  s=summaries[label];assert 'failure' not in s,(label,s)
  m=s['head'];assert m['jvmSteps']==steps and m['result']==0
  if kind=='exception':assert m['lifecycle']==m['outcome']==3 and m['javaRef']>0 and base64.b64decode(m['javaClass'])==b'java/lang/RuntimeException'
  else:assert m['lifecycle']==m['outcome']==2
# Bindings are selected assertions, never a host class catalogue. All bytes remain
# in the same untouched JAR and are selected/decoded by EVM ZI0/DI0.
entry=['net/minecraft/server/MinecraftServer.class','bn.class','tr.class','um.class']
world('official4',jar,entry,1,False)
logging=entry+['org/apache/logging/log4j/LogManager.class','org/apache/logging/log4j/status/StatusLogger.class','org/apache/logging/log4j/spi/AbstractLogger.class','org/apache/logging/log4j/spi/ExtendedLogger.class','org/apache/logging/log4j/Logger.class']
world('official9',jar,logging,1,False)
(out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
for k,v in summaries.items():
 if 'failure' in v:print(k,json.dumps({x:v['failure'].get(x) for x in ('diagnostic','selector','uint256Words','gas')}))
 else:print(k,json.dumps({'epoch':v['head']['epoch'],'lifecycle':v['head']['lifecycle'],'jvm':v['head']['jvmSteps'],'firstGas':v['start']['gasUsed']}))
