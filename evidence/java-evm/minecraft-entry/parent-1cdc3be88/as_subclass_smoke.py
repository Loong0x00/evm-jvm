#!/usr/bin/env python3
"""Independent parent focused Class.asSubclass q1/q7/direct gate."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
sources=[here/x for x in ('ClassAsSubclassProbe.java','RawMessageFactory.java','RawReusableMessageFactory.java','NoInitClassAsSubclassProbe.java','UncaughtClassCastProbe.java','OmittedClassAssignableProbe.java','OmittedClassCastProbe.java','OmittedClassNewInstanceProbe.java')];call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sources])
def jar(name,names):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(classes/n).read_bytes())
 return p
def converge(prefix,main,names,lifecycle,kind=None):
 z=jar(prefix+'.zip',names);baseline=None;rows={}
 for q in (1,7,4096):
  label=prefix+'-q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS=','.join(names));args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
  for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
  h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==lifecycle and (kind is None or h['javaKind']==kind);cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();current=(h['machineRoot'],cp[280:]);baseline=current if baseline is None else baseline;assert current==baseline;rows[label]={'epoch':h['epoch'],'java':h['jvmSteps'],'internal':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest(),'lifecycle':h['lifecycle'],'javaKind':h['javaKind']}
 return rows
rows={};rows.update(converge('focused','ClassAsSubclassProbe',['ClassAsSubclassProbe.class','RawMessageFactory.class','RawReusableMessageFactory.class'],2));rows.update(converge('noinit','NoInitClassAsSubclassProbe',['NoInitClassAsSubclassProbe.class','NoInitClassAsSubclassProbe$Target.class'],2));rows.update(converge('uncaught','UncaughtClassCastProbe',['UncaughtClassCastProbe.class','RawMessageFactory.class'],3,8))
# Still-omitted Class APIs retain ordinary CallError refusal.
for name in ('OmittedClassAssignableProbe','OmittedClassCastProbe'):
 z=jar(name+'.zip',[name+'.class']);e=dict(env,MC_ENTRY_BINDINGS=name+'.class');call(name+'-start',[build/'driver','setup-chain',out/(name+'-world'),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,4096],e);r=json.loads((out/'reports'/(name+'-world')/'start-refusal.json').read_text());assert r['selector']=='0xd631c3a4' and r['rootBefore']==r['rootAfter'];rows[name]=r
# newInstance now resolves, while a bootstrap mirror is outside its bounded raw target profile.
name='OmittedClassNewInstanceProbe';z=jar(name+'.zip',[name+'.class']);e=dict(env,MC_ENTRY_BINDINGS=name+'.class');call(name+'-start',[build/'driver','setup-chain',out/(name+'-world'),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,4096],e);r=json.loads((out/'reports'/(name+'-world')/'start-refusal.json').read_text());assert r['selector']=='0xc6254057' and r['uint256Words']==['1','2'] and r['rootBefore']==r['rootAfter'];rows[name]=r
call('canonical',['node',here/'verify_receipts.js',build,out,1,'focused-q1','focused-q7','focused-q4096','noinit-q1','noinit-q7','noinit-q4096','uncaught-q1','uncaught-q7','uncaught-q4096']);(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
