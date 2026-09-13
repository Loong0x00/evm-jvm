#!/usr/bin/env python3
"""Generated-only q1/q7/direct/reopen and exact unsupported-System probes."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent; build=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); assert not out.exists(); out.mkdir(); (out/'tmp').mkdir(); env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=e or env)
 assert p.returncode==0,(label,p.returncode)
 (out/(label+'-process.json')).write_text(json.dumps({'exit':p.returncode,'command':list(map(str,args))},indent=2)+'\n')
def archive(name, names, raw=False):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_STORED) as z:
  base=build/'raw-system-classes' if raw else build/'fixture-classes'
  for n in names:z.write(base/n,n)
 return p
engine=build/'engine/MCEntryInterpreter.json'; coordinator=build/'coordinator/MCEntryCoordinator.json'; driver=build/'driver'
names=['SystemPropertyProbe.class','java/lang/IllegalArgumentException.class']; z=archive('system-property.zip',names); rows={}; base=None
for q in (1,7,4096):
 w=out/('q'+str(q)); e=dict(env,MC_ENTRY_BINDINGS=','.join(names)); args=[driver,'setup-chain',w,coordinator,engine,z,q]
 for label,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call('q%d-%s'%(q,label),[driver,mode,*args[2:]],e)
 h=json.loads((w/'durable-head.json').read_text()); cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); assert h['lifecycle']==h['outcome']==2 and h['result']==0
 value=(h['machineRoot'],cp[280:]); base=base or value; assert value==base
 rows['q'+str(q)]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest(),'checkpointBytes':len(cp)}
for n in ('UnsupportedGetPropertiesProbe','UnsupportedSetPropertyProbe','UnsupportedClearPropertyProbe'):
 z=archive(n+'.zip',[n+'.class']); e=dict(env,MC_ENTRY_BINDINGS=n+'.class'); call(n,[driver,'setup-chain',out/(n+'-world'),coordinator,engine,z,4096],e)
 r=json.loads((out/'reports'/(n+'-world')/'start-refusal.json').read_text()); assert r['selector']=='0xd631c3a4' and r['uint256Words'][0]=='3' and r['rootUnchanged']; rows[n]=r
z=out/'raw-system-replacement.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_STORED) as f:
 f.write(build/'fixture-classes/RawSystemReplacementMain.class','RawSystemReplacementMain.class')
 f.write(build/'raw-system-classes/java/lang/System.class','java/lang/System.class')
e=dict(env,MC_ENTRY_BINDINGS='RawSystemReplacementMain.class,java/lang/System.class'); call('raw-system-replacement',[driver,'setup-chain',out/'raw-system-replacement-world',coordinator,engine,z,4096],e)
r=json.loads((out/'reports/raw-system-replacement-world/start-refusal.json').read_text()); assert r['selector']=='0x6a23ad80' and r['uint256Words']==['1','1'] and r['rootUnchanged']; rows['rawSystemReplacement']=r
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
