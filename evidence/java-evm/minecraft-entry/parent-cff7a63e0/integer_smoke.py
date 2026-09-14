#!/usr/bin/env python3
"""Independent parent focused Integer q1/q7/direct/terminal/replacement gate."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
sources=[here/x for x in ('IntegerProbe.java','UncaughtNumberFormatProbe.java','RawIntegerReplacementMain.java','OmittedIntegerRadixProbe.java','OmittedIntegerValueOfProbe.java')];call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sources])
def jar(name,base,names):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(base/n).read_bytes())
 return p
z=jar('integer.zip',classes,['IntegerProbe.class']);baseline=None;rows={}
for q in (1,7,4096):
 label='integer-q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS='IntegerProbe.class');args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['result']==0;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();current=(h['machineRoot'],cp[280:]);baseline=current if baseline is None else baseline;assert current==baseline;rows[label]={'epoch':h['epoch'],'java':h['jvmSteps'],'internal':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}
uz=jar('uncaught-nfe.zip',classes,['UncaughtNumberFormatProbe.class']);terminal=None
for q in (1,7,4096):
 label='nfe-q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS='UncaughtNumberFormatProbe.class');args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',uz,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==3 and h['javaKind']==0 and base64.b64decode(h['javaClass'])==b'java/lang/NumberFormatException' and h['javaRef']!=0;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();current=(h['machineRoot'],cp[280:]);terminal=current if terminal is None else terminal;assert current==terminal;rows[label]={'epoch':h['epoch'],'java':h['jvmSteps'],'internal':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest(),'javaClass':'java/lang/NumberFormatException'}
# Reserved raw tail classes.
for name in ('Number','NumberFormatException','Integer'):
 cd=out/('raw-'+name);cd.mkdir();source=here/'integer-replacements/java/lang'/(name+'.java');call('raw-build-'+name,['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',cd,here/'RawIntegerReplacementMain.java',source]);rz=jar('raw-'+name+'.zip',cd,['RawIntegerReplacementMain.class','java/lang/'+name+'.class']);e=dict(env,MC_ENTRY_BINDINGS='RawIntegerReplacementMain.class,java/lang/'+name+'.class');call('raw-start-'+name,[build/'driver','setup-chain',out/('raw-world-'+name),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e);r=json.loads((out/'reports'/('raw-world-'+name)/'start-refusal.json').read_text());assert r['selector']=='0x6a23ad80' and r['rootBefore']==r['rootAfter'];rows['raw-'+name]=r
# Deliberately omitted APIs fail without mutation.
for name in ('OmittedIntegerRadixProbe','OmittedIntegerValueOfProbe'):
 rz=jar(name+'.zip',classes,[name+'.class']);e=dict(env,MC_ENTRY_BINDINGS=name+'.class');call(name+'-start',[build/'driver','setup-chain',out/(name+'-world'),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e);r=json.loads((out/'reports'/(name+'-world')/'start-refusal.json').read_text());assert r['selector']=='0xd631c3a4' and r['rootBefore']==r['rootAfter'];rows[name]=r
call('canonical',['node',here/'verify_receipts.js',build,out,1,'integer-q1','integer-q7','integer-q4096','nfe-q1','nfe-q7','nfe-q4096']);(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
