#!/usr/bin/env python3
"""Parent generated Java8/EVM smoke for full-domain repaired interface profile."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'privileged-action-preflight';build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
sources=[src/'fixtures/PrivilegedActionProbe.java',src/'fixtures/CallerPrivilegedActionRefusal.java',src/'fixtures/AccessControllerRefusal.java',src/'fixtures/java/security/PrivilegedAction.java']
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sources]);call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'PrivilegedActionProbe'])
def archive(name,names):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(classes/n).read_bytes())
 return p
probe=archive('probe.zip',['PrivilegedActionProbe.class','PrivilegedActionProbe$StringAction.class']);normal={};ref=None
for q in (1,7,4096):
 label='q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS='PrivilegedActionProbe.class,PrivilegedActionProbe$StringAction.class');args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',probe,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['jvmSteps']==226 and h['internalSteps']==4
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256']
 if ref is None:ref=cp[280:]
 else:assert ref==cp[280:]
 normal[label]={'epoch':h['epoch'],'java':h['jvmSteps'],'internal':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}
call('canonical',['node',here.parent/'parent-2293e298e/verify_receipts.js',build,out,1,'q1','q7','q4096'])
# Honest replacement and unsupported API failures.
caller=archive('caller.zip',['CallerPrivilegedActionRefusal.class','java/security/PrivilegedAction.class']);access=archive('access.zip',['AccessControllerRefusal.class']);fails={}
for label,jar,names,want in [('caller',caller,'CallerPrivilegedActionRefusal.class,java/security/PrivilegedAction.class','0x6a23ad80'),('access',access,'AccessControllerRefusal.class','0x555db429')]:
 e=dict(env,MC_ENTRY_BINDINGS=names);w=out/label;args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',jar,4096];call(label+'-start',[build/'driver','setup-chain',*args],e);r=json.loads((out/'reports'/label/'start-refusal.json').read_text());assert r['selector']==want and r['rootBefore']==r['rootAfter']
 if label=='access':assert r['diagnostic']['name']=='java/security/AccessController' and r['diagnostic']['site']=='4107'
 else:assert r['uint256Words']==['1','1']
 fails[label]=r
(out/'summary.json').write_text(json.dumps({'normal':normal,'failures':fails},indent=2)+'\n');print(json.dumps(normal,indent=2))
