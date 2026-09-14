#!/usr/bin/env python3
"""Fresh Java8 image and Solidity artifact rebuild for this bounded preflight."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent.parent; root=here.parents[3]
out=Path(sys.argv[1]).resolve(); assert out.parent==root/'build' and out.name.startswith('java-diff-mc-java-version-split-') and not out.exists()
out.mkdir(); (out/'classes').mkdir(); (out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules',PYTHONDONTWRITEBYTECODE='1')
def run(label,args,cwd=root):
 with (out/(label+'.log')).open('w') as f: p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode: raise SystemExit((label,p.returncode))
rt=out/'rt-without-replaced.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',rt)
run('strip-platform',['zip','-q','-d',rt,'java/lang/String.class','java/lang/System.class','java/lang/Class.class'])
run('java8-bootstrap',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',rt,'-d',out/'classes',here/'bootstrap/java/lang/String.java',here/'bootstrap/java/lang/System.java',here/'bootstrap/java/lang/Class.java'])
want={'String':'c0ce987aec36ee7dcab427a59fab17858cece64cd0813ebe299ff77c09b6d61e','System':'fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44','Class':'0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934'}
for n,h in want.items():
 b=(out/'classes/java/lang'/f'{n}.class').read_bytes(); assert hashlib.sha256(b).hexdigest()==h,(n,len(b));
# The checked-in source is the reproducible engine source. Build it with pinned solc.
for role in ('engine','coordinator'):
 dst=out/role; shutil.copytree(here/role,dst); run(role+'-build',['node',dst/'build.js'],dst)
e=json.loads((out/'engine/MCEntryInterpreter.json').read_text()); c=json.loads((out/'coordinator/MCEntryCoordinator.json').read_text())
assert len(e['deployedBytecode'])//2 <= 393216
(out/'pins.json').write_text(json.dumps({'basis':'d183da5ab','domain':'MC-JAVA-VERSION-SPLIT1','address':'0x4d432d4a4156412d56455253494f4e2d53504c49','runtimeCap':393216,'accepted320Unchanged':True,'bootstrapCount':68,'globalNativeBindings':9,'stringLocalBinding':10,'exceptionKinds':14,'images':want,'engine':{'bytes':len(e['deployedBytecode'])//2,**e['codeHashes']},'coordinator':{'bytes':len(c['deployedBytecode'])//2,**c['codeHashes']}},indent=2)+'\n')
