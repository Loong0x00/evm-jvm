#!/usr/bin/env python3
"""Rebuild the pinned Class.asSubclass evidence candidate into an ignored build dir."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent.parent; root=here.parents[3]
out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-class-as-subclass-') and not out.exists()
out.mkdir();(out/'classes').mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str((out/'tmp').resolve()),NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules',PYTHONDONTWRITEBYTECODE='1')
def run(label,args,cwd=root):
    with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
    assert p.returncode==0,(label,p.returncode)
run('source-invariants',[sys.executable,here/'tools/verify_source.py'])
rt=out/'rt-without-replaced.jar';shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',rt)
names=('String','System','Class','Number','NumberFormatException','Integer')
run('strip-platform',['zip','-q','-d',rt,*['java/lang/'+n+'.class' for n in names]])
run('java8-bootstrap',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',rt,'-d',out/'classes',*[here/'bootstrap/java/lang'/(n+'.java') for n in names]])
images={n:hashlib.sha256((out/'classes/java/lang'/(n+'.class')).read_bytes()).hexdigest() for n in names}
expected={'String':'c412caea1d48baade8aa9d2653c6a23bb319a49deefe729ac99089f0c5248eba','System':'fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44','Class':'8986691ab80193f6958d7560a09f44b9dbacb22a30b317b905c811a2bf440ff7','Number':'fe77f74edbcc2777f4edfa6227759fd8a3b856838113fb0fe9880affc4c9876f','NumberFormatException':'a627a1649de875297f522fd2fde19f32b3e79f1945e7343941c696692e039d15','Integer':'bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537'}
assert images==expected,images
run('javap-class',['/usr/lib/jvm/java-8-openjdk/bin/javap','-bootclasspath',str(out/'classes')+':'+str(rt),'-c','-p','-s','java.lang.Class'])
for role in ('engine','coordinator'):
    shutil.copytree(here/role,out/role);run(role+'-build',['node',out/role/'build.js'],out/role)
e=json.loads((out/'engine/MCEntryInterpreter.json').read_text());c=json.loads((out/'coordinator/MCEntryCoordinator.json').read_text())
assert len(e['deployedBytecode'])//2 <= 393216 and len(c['deployedBytecode'])//2 <=24576
pins={'basis':'661331e3d parent accepted source archive','domain':'MC-CLASS-AS-SUBCLASS-PREFLIGHT1','address':'0x4d432d434c4153532d41532d535542434c000001','owner':'0x4d432d434c4153532d41532d4f574e4552000002','runtimeCap':393216,'accepted320Unchanged':True,'bootstrapCount':71,'globalNativeBindings':10,'stringLocalBindings':list(range(1,11)),'exceptionKinds':14,'images':images,'engine':{'bytes':len(e['deployedBytecode'])//2,**e['codeHashes']},'coordinator':{'bytes':len(c['deployedBytecode'])//2,**c['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128,'rawLimits':[24,262144]}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
