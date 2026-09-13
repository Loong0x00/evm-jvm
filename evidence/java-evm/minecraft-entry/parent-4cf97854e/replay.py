#!/usr/bin/env python3
"""Run narrow class literal checks and retry unchanged Minecraft with rebuilt pins."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();jar=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
a=json.loads((build/'engine/MCEntryInterpreter.json').read_text());assert hashlib.sha256(bytes.fromhex(a['deployedBytecode'])).hexdigest()=='a35a22d28314bcfcad05df73046d9ef7af08cfb6a5b24e3925f4ce1b9fee09fe'
assert hashlib.sha256(jar.read_bytes()).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e'
def call(label,args,names=None):
 e=dict(env)
 if names:e['MC_ENTRY_BINDINGS']=','.join(names)
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=e,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'command':list(map(str,args))})+'\n');assert code==0,(label,code)
call('fixtures',[sys.executable,root/'evidence/java-evm/minecraft-entry/class-literal-preflight/fixtures/generate-class-literal.py',out/'fixtures'])
# Test oracles run with actual Java8, separately from every EVM execution input.
for cl in ('LiteralMain','WideLiteralMain','UntakenMissingLiteral'):call('java8-oracle-'+cl,['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',out/'fixtures/classes',cl])
exe=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json';summary={};payloads={}
cases=[('literal','class-literal.zip',['LiteralMain.class','LiteralMain$Target.class','LiteralMain$Tracker.class','LiteralMain$Face$Inner.class'],(1,7,4096),40),('wide','wide-class-literal.zip',['WideLiteralMain.class','WideLiteralMain$Target.class'],(7,4096),9),('untaken','untaken-missing-literal.zip',['UntakenMissingLiteral.class'],(4096,),5),('missing','missing-literal.zip',['MissingLiteral.class'],(4096,),0)]
for kind,z,names,qs,steps in cases:
 for q in qs:
  label=kind+'-q'+str(q);w=out/label;args=[w,coord,engine,out/'fixtures'/z,q];call(label+'-setup',[exe,'setup-chain']+args,names)
  rp=out/'reports'/label
  if kind=='missing':
   f=json.loads((rp/'start-refusal.json').read_text());assert f['rootBefore']==f['rootAfter'] and f['diagnostic']=={'site':'4108','context':'0','name':'MissingTarget2'};summary[label]={'failure':f};continue
  call(label+'-finish',[exe,'finish']+args,names);call(label+'-verify',[exe,'verify']+args,names)
  m=json.loads((w/'durable-head.json').read_text());assert m['lifecycle']==m['outcome']==2 and m['jvmSteps']==steps and m['result']==0
  cp=(w/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==m['checkpointSHA256'] and len(cp)<=1048576
  if kind in payloads:assert cp[280:]==payloads[kind]
  payloads[kind]=cp[280:];jvm=internal=0
  for n,p in enumerate(sorted(rp.glob('slice-*.json')),1):
   r=json.loads(p.read_text());s=r['slice'];assert s['epoch']==n and 0<r['gasUsed']<=100000000 and s['executedJvmSteps']<=q and s['totalJvmSteps']==jvm+s['executedJvmSteps'] and s['totalInternalSteps']==internal+s['executedInternalSteps'] and len(r['nestedLogs'])==1
   jvm,internal=s['totalJvmSteps'],s['totalInternalSteps']
  summary[label]={'epoch':m['epoch'],'java':jvm,'internal':internal,'terminalPayloadSHA256':hashlib.sha256(cp[280:]).hexdigest()}
names=['net/minecraft/server/MinecraftServer.class','bn.class','tr.class','um.class','org/apache/logging/log4j/LogManager.class','org/apache/logging/log4j/status/StatusLogger.class','org/apache/logging/log4j/spi/AbstractLogger.class','org/apache/logging/log4j/spi/ExtendedLogger.class','org/apache/logging/log4j/Logger.class']
w=out/'official9';args=[w,coord,engine,jar,1];call('official9-setup',[exe,'setup-chain']+args,names)
m=json.loads((w/'durable-head.json').read_text());summary['official9']={'head':m}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='missing-q4096'},indent=2))
