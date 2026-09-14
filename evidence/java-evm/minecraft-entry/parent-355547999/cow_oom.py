#!/usr/bin/env python3
"""Parent generated COW backing-array count-quota OOM gate."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();src=out/'COWOOMMain.java';classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT)
 (out/(label+'-process.json')).write_text(json.dumps({'exit':p.returncode,'command':list(map(str,args))})+'\n');assert p.returncode==0,(label,p.returncode)
src.write_text('import java.util.concurrent.CopyOnWriteArrayList; public final class COWOOMMain { static int result; public static void main(String[] x) { Object[][] retained = new Object[1021][0]; CopyOnWriteArrayList<Object> list = new CopyOnWriteArrayList<Object>(); try { list.add(null); result=1; } catch (OutOfMemoryError expected) { result=7; } if (result!=7 || retained.length!=1021 || list.size()!=0) throw new Error(); } }\n')
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',classes,src]);z=out/'cow-oom.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:i=zipfile.ZipInfo('COWOOMMain.class',(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;a.writestr(i,(classes/'COWOOMMain.class').read_bytes())
e=dict(env,MC_ENTRY_BINDINGS='COWOOMMain.class');baseline=None;rows={}
for q in (1,7,4096):
 label='oom-q'+str(q);w=out/label;args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['javaKind']==0;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();current=(h['machineRoot'],hashlib.sha256(cp[280:]).hexdigest());baseline=current if baseline is None else baseline;assert current==baseline;rows[label]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'checkpointBytes':len(cp),'machineRoot':h['machineRoot'],'opaquePayloadSHA256':current[1]}
call('canonical',['node',here/'verify_receipts.js',build,out,1,'oom-q1','oom-q7','oom-q4096']);(out/'summary.json').write_text(json.dumps({'retainedZeroLengthInnerArrays':1021,'expectedArrayCountAtAdd':1024,'results':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
