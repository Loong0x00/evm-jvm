#!/usr/bin/env python3
"""Parent LOCAL384 system-loader native q1/q7/direct generated proof."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'system-classloader-preflight';build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
fix=src/'fixtures';call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,fix/'SystemClassLoaderProbe.java',fix/'LoaderResourcesUnsupported.java',fix/'VMClassLoaderReplacementMain.java',here/'SystemClassLoaderHostOracle.java']);call('replacement-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,fix/'java/lang/VMClassLoader.java']);call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'SystemClassLoaderHostOracle'])
def jar(name,names):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(classes/n).read_bytes())
 return p
spec=importlib.util.spec_from_file_location('d',here/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
probe=jar('probe.zip',['SystemClassLoaderProbe.class','SystemClassLoaderProbe$Second.class','SystemClassLoaderProbe$StringAction.class']);ref=None;baseline=None;normal={}
for q in (1,7,4096):
 label='q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS='SystemClassLoaderProbe.class,SystemClassLoaderProbe$Second.class,SystemClassLoaderProbe$StringAction.class');args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',probe,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['jvmSteps']==332 and h['internalSteps']==8;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();diag=d.inspect(cp);v=next(x['staticValues'] for x in diag['initialization'] if x['classIndex']==0);assert (int(v[-1]['packedValue'],16)&((1<<64)-1))==631
 current=(h['machineRoot'],cp[280:]);
 if baseline is None:baseline=current
 else:assert current==baseline
 normal[label]={'epoch':h['epoch'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}
call('canonical',['node',here.parent/'parent-102911980/verify_receipts.js',build,out,1,'q1','q7','q4096'])
for label,z,names,want,words in [('vm-replacement',jar('replace.zip',['VMClassLoaderReplacementMain.class','java/lang/VMClassLoader.class']),'VMClassLoaderReplacementMain.class,java/lang/VMClassLoader.class','0x6a23ad80',['1','1']),('resources',jar('resources.zip',['LoaderResourcesUnsupported.class']),'LoaderResourcesUnsupported.class','0xd631c3a4',['3','21'])]:
 w=out/label;e=dict(env,MC_ENTRY_BINDINGS=names);args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,4096];call(label+'-start',[build/'driver','setup-chain',*args],e);r=json.loads((out/'reports'/label/'start-refusal.json').read_text());assert r['selector']==want and r['uint256Words']==words and r['rootBefore']==r['rootAfter']
(out/'summary.json').write_text(json.dumps(normal,indent=2)+'\n');print(json.dumps(normal,indent=2))
