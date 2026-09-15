#!/usr/bin/env python3
"""Retained generated field-arena quota/OOM control under Enum82 pins."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent; root=here.parents[4]; build=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
assert build.parent==root/'build' and out.parent==root/'build' and out.name.startswith('java-diff-mc-enum-bootstrap-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir(); src=out/'src'; classes=out/'classes'; src.mkdir(); classes.mkdir(); env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def call(label,args):
 with (out/(label+'.log')).open('w') as f: p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 assert p.returncode==0,(label,p.returncode)
(src/'OOMNewInstanceMain.java').write_text('public final class OOMNewInstanceMain { static int result; public static void main(String[] x) throws Exception { try { TooWideTarget.class.newInstance(); result=1; } catch (OutOfMemoryError expected) { result=7; } if (result!=7) throw new Error(); } }\n')
fields=''.join('  int f%d;\n'%i for i in range(1025)); (src/'TooWideTarget.java').write_text('public final class TooWideTarget {\n'+fields+'  public TooWideTarget() {}\n}\n')
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',classes,*sorted(src.glob('*.java'))])
archive=out/'oom.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
 for name in ('OOMNewInstanceMain.class','TooWideTarget.class'):
  i=zipfile.ZipInfo(name,(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_STORED; z.writestr(i,(classes/name).read_bytes())
env['MC_ENTRY_BINDINGS']='OOMNewInstanceMain.class,TooWideTarget.class'; rows={}; baseline=None
for tag,q in (('q1',1),('q7',7),('direct',4096)):
 w=out/('oom-'+tag); args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',archive,str(q)]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')): call('oom-'+tag+'-'+suffix,[build/'driver',mode,*args])
 h=json.loads((w/'durable-head.json').read_text()); assert h['lifecycle']==h['outcome']==2 and h['result']==0 and h['javaKind']==0
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes(); x={'machineRoot':h['machineRoot'],'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps']}; rows[tag]=x
 if baseline is None: baseline=x
 else:
  for k in ('machineRoot','opaquePayloadSHA256'): assert x[k]==baseline[k],(tag,k)
node_env=dict(os.environ,NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
subprocess.run(['node',here/'verify_receipts.js',build,out,'1','oom-q1','oom-q7','oom-direct'],cwd=root,env=node_env,check=True)
summary={'profile':'MC-ENUM-BOOTSTRAP-PREFLIGHT1','generatedOnly':True,'fieldCount':1025,'expectedGuestOutcome':'caught OutOfMemoryError; no arena quota change','results':rows}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
