#!/usr/bin/env python3
"""Parent Java8 TEST oracle + actual EVM package name/identity/non-init control."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();(out/'classes').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),MC_ENTRY_BINDINGS='dotted/Main.class,dotted/Target.class')
jdk='/usr/lib/jvm/java-8-openjdk/bin/';subprocess.run([jdk+'javac','-source','8','-target','8','-g:none','-d',str(out/'classes')]+list(map(str,(here/'dotted').glob('*.java'))),env=env,check=True)
subprocess.run([jdk+'java','-cp',str(out/'classes'),'dotted.Main'],env=env,check=True)
zp=out/'dotted.zip'
with zipfile.ZipFile(zp,'w') as z:
 for n in ('dotted/Main.class','dotted/Target.class'):z.writestr(zipfile.ZipInfo(n,(1980,1,1,0,0,0)),(out/'classes'/n).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
ref=None;summary={}
for q in (1,7,4096):
 w=out/('q'+str(q));args=[str(w),str(build/'coordinator/MCEntryCoordinator.json'),str(build/'engine/MCEntryInterpreter.json'),str(zp),str(q)]
 for mode in ('setup-chain','finish','verify'):
  with (out/('q%d-%s.log'%(q,mode))).open('w') as f:subprocess.run([str(build/'driver'),mode]+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 m=json.loads((w/'durable-head.json').read_text());assert m['outcome']==m['lifecycle']==2
 cp=(w/'checkpoints'/(m['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==m['checkpointSHA256']
 if ref is None:ref=cp[280:]
 else:assert ref==cp[280:]
 summary[str(q)]={'epoch':m['epoch'],'jvm':m['jvmSteps'],'internal':m['internalSteps'],'machineRoot':m['machineRoot'],'payloadSHA256':hashlib.sha256(cp[280:]).hexdigest()}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
