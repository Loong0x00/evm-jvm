#!/usr/bin/env python3
"""Rebuild the exact Java8 Integer images and pinned Solidity artifacts."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent.parent; root=here.parents[3]
out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-integer-') and not out.exists()
out.mkdir(); (out/'classes').mkdir(); (out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules',PYTHONDONTWRITEBYTECODE='1')
def run(label,args,cwd=root):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode: raise SystemExit((label,p.returncode))
rt=out/'rt-without-replaced.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',rt)
run('strip-platform',['zip','-q','-d',rt,'java/lang/String.class','java/lang/System.class','java/lang/Class.class','java/lang/Number.class','java/lang/NumberFormatException.class','java/lang/Integer.class'])
sources=[here/'bootstrap/java/lang'/f'{x}.java' for x in ('String','System','Class','Number','NumberFormatException','Integer')]
run('java8-bootstrap',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',rt,'-d',out/'classes',*sources])
want={'String':'c412caea1d48baade8aa9d2653c6a23bb319a49deefe729ac99089f0c5248eba','System':'fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44','Class':'0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934','Number':'fe77f74edbcc2777f4edfa6227759fd8a3b856838113fb0fe9880affc4c9876f','NumberFormatException':'a627a1649de875297f522fd2fde19f32b3e79f1945e7343941c696692e039d15','Integer':'bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537'}
for n,h in want.items():
 b=(out/'classes/java/lang'/f'{n}.class').read_bytes(); assert hashlib.sha256(b).hexdigest()==h,(n,len(b))
for role in ('engine','coordinator'):
 dst=out/role; shutil.copytree(here/role,dst); run(role+'-build',['node',dst/'build.js'],dst)
e=json.loads((out/'engine/MCEntryInterpreter.json').read_text()); c=json.loads((out/'coordinator/MCEntryCoordinator.json').read_text())
assert len(e['deployedBytecode'])//2 <= 393216 and len(c['deployedBytecode'])//2 <= 24576
(out/'pins.json').write_text(json.dumps({'basis':'512864d47','domain':'MC-INTEGER-PREFLIGHT1','runtimeCap':393216,'accepted320Unchanged':True,'bootstrapCount':71,'globalNativeBindings':9,'stringLocalBinding':10,'exceptionKinds':14,'images':want,'engine':{'bytes':len(e['deployedBytecode'])//2,**e['codeHashes']},'coordinator':{'bytes':len(c['deployedBytecode'])//2,**c['codeHashes']}},indent=2)+'\n')
