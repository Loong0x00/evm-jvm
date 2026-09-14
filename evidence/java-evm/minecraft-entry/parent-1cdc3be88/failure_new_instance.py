#!/usr/bin/env python3
"""Parent generated constructor-throw and failing-class-init newInstance gates."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();src=out/'src';classes=out/'classes';src.mkdir();classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT)
 (out/(label+'-process.json')).write_text(json.dumps({'exit':p.returncode,'command':list(map(str,args))})+'\n');assert p.returncode==0,(label,p.returncode)
def source(name,text):(src/(name+'.java')).write_text(text+'\n')
source('ThrowingCtorMain','public final class ThrowingCtorMain { static int result; public static void main(String[] x) throws Exception { try { ThrowingCtorTarget.class.newInstance(); result=1; } catch (IllegalArgumentException expected) { result=7; } if (result!=7) throw new Error(); } }')
source('ThrowingCtorTarget','public final class ThrowingCtorTarget { public ThrowingCtorTarget() { throw new IllegalArgumentException(); } }')
source('FailingInitMain','public final class FailingInitMain { static int result; public static void main(String[] x) throws Exception { try { FailingInitTarget.class.newInstance(); result=1; } catch (ExceptionInInitializerError expected) { result=2; } try { FailingInitTarget.class.newInstance(); result+=10; } catch (NoClassDefFoundError expected) { result+=5; } if (result!=7) throw new Error(); } }')
source('FailingInitTarget','public final class FailingInitTarget { static { if (fail()) throw new IllegalArgumentException(); } private static boolean fail() { return true; } public FailingInitTarget() {} }')
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',classes,*sorted(src.glob('*.java'))]);rows={};labels=[]
for case,names in [('ctor',['ThrowingCtorMain.class','ThrowingCtorTarget.class']),('init',['FailingInitMain.class','FailingInitTarget.class'])]:
 z=out/(case+'.zip')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;a.writestr(i,(classes/n).read_bytes())
 e=dict(env,MC_ENTRY_BINDINGS=','.join(names));baseline=None
 for q in (1,7,4096):
  label=case+'-q'+str(q);labels.append(label);w=out/label;args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
  for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
  h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['javaKind']==0;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();current=(h['machineRoot'],hashlib.sha256(cp[280:]).hexdigest());baseline=current if baseline is None else baseline;assert current==baseline;rows[label]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaquePayloadSHA256':current[1]}
call('canonical',['node',here/'verify_receipts.js',build,out,1,*labels]);(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
