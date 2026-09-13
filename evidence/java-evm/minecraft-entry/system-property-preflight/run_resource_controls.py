#!/usr/bin/env python3
"""Generated-only retained EVM-ZI0 resource and prior-control replay."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent; build=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); assert not out.exists(); out.mkdir(); classes=out/'classes'; classes.mkdir(); (out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=e or env)
 assert p.returncode==0,(label,p.returncode)
 (out/(label+'-process.json')).write_text(json.dumps({'exit':p.returncode,'command':list(map(str,args))},indent=2)+'\n')
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sorted(map(str,(here/'fixtures').glob('*Resource*.java'))),here/'fixtures/UnsupportedOpenStreamProbe.java'])
(classes/'probe').mkdir(); (classes/'probe/resource.txt').write_bytes(b'system-property-evm-indexed-resource\n')
call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'ParentResourceEnumerationHostOracle'])
def archive(path,names,resource=True):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:z.write(classes/n,n)
  if resource:z.writestr('probe/resource.txt',b'system-property-evm-indexed-resource\n')
names=['ParentResourceEnumerationProbe.class','ParentResourceEnumerationProbe$Old.class','ParentResourceEnumerationProbe$New.class','ParentResourceEnumerationProbe$StringAction.class']; z=out/'resource-control.zip'; archive(z,names)
rows={}; base=None
for q in (1,7,4096):
 w=out/('q'+str(q)); e=dict(env,MC_ENTRY_BINDINGS=','.join(names)); args=[build/'driver','setup-chain',w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
 for label,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call('q%d-%s'%(q,label),[build/'driver',mode,*args[2:]],e)
 h=json.loads((w/'durable-head.json').read_text()); cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); assert h['lifecycle']==h['outcome']==2
 current=(h['machineRoot'],cp[280:]); base=base or current; assert current==base
 rows['q'+str(q)]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest(),'checkpointBytes':len(cp)}
# Missing-loader and openStream remain honest refusals; no fake empty result.
archive(out/'missing-loader.zip',['ResourceEnumerationProbe.class']); e=dict(env,MC_ENTRY_BINDINGS='ResourceEnumerationProbe.class'); call('missing-loader',[build/'driver','setup-chain',out/'missing-loader-world',build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',out/'missing-loader.zip',4096],e)
r=json.loads((out/'reports/missing-loader-world/start-refusal.json').read_text()); assert r['selector']=='0x71540d20' and r['rootUnchanged']; rows['missingLoader']=r
archive(out/'open-stream.zip',['UnsupportedOpenStreamProbe.class']); e=dict(env,MC_ENTRY_BINDINGS='UnsupportedOpenStreamProbe.class'); call('open-stream',[build/'driver','setup-chain',out/'open-stream-world',build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',out/'open-stream.zip',4096],e)
r=json.loads((out/'reports/open-stream-world/start-refusal.json').read_text()); assert r['selector']=='0xd631c3a4' and r['rootUnchanged']; rows['unsupportedOpenStream']=r
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
