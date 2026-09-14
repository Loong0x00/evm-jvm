#!/usr/bin/env python3
"""Independent parent source-build of bounded Class.forName binding9."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3]
cand=here.parent/'class-for-name-preflight';dcand=here.parent/'class-not-found-preflight'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-class-for-name-parent-') and not out.exists()
out.mkdir();(out/'tmp').mkdir();(out/'bootstrap-classes').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,check=True):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if check:assert p.returncode==0,(label,p.returncode)
 return p.returncode
# Rebuild the Java8 Class image rather than trusting worker bytes.
api=out/'rt-without-class.jar';shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api);run('strip-platform',['zip','-q','-d',api,'java/lang/Class.class'])
run('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out/'bootstrap-classes',here/'Class.java'])
img=(out/'bootstrap-classes/java/lang/Class.class').read_bytes();expected='0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934';assert len(img)==670 and hashlib.sha256(img).hexdigest()==expected
run('javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-bootclasspath',str(out/'bootstrap-classes')+':'+str(api),'-c','-p','-s','java.lang.Class'])
# Source-level semantic pins and exact image embedding.
s=(cand/'engine/MCEntryInterpreter.sol').read_text();assert s.count('MC-CLASS-FOR-NAME-PREFLIGHT1')==9 and 'new bytes32[](68)' in s and 'new uint256[](14)' in s and 'classesByKind[13] = at + 62' in s and 'exceptionKind > 13' in s and 'kind <= 13' in s and 'pk > 13' in s and 'p.javaKind > 13' in s
assert 'bytes("forName0")' in s and 'return 9;' in s and 'binding == 7 || binding == 8 || binding == 9' in s and 'ClassForNameInitializationError(target, opPC)' in s and 'nativeBinding == 9, opPC' in s
m=re.search(r'(function _bootstrapClass\(\).*?hex")([0-9a-f]+)(";)',s,re.S);assert m and hashlib.sha256(bytes.fromhex(m.group(2))).hexdigest()=='d63783800a1906528d2064fc40f740aaaceb616af8212c4d1a8db1da21791061'
s=s[:m.start(2)]+img.hex()+s[m.end(2):]
s=s.replace('MC-CLASS-FOR-NAME-PREFLIGHT1','MC-CLASS-FOR-NAME-PARENT1');engine=out/'engine';shutil.copytree(cand/'engine',engine);(engine/'MCEntryInterpreter.sol').write_text(s);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=393216
co=out/'coordinator';shutil.copytree(cand/'coordinator',co);p=co/'MCEntryCoordinator.sol';x=p.read_text();assert x.count('MC-CLASS-FOR-NAME-PREFLIGHT1')==3;x=x.replace('MC-CLASS-FOR-NAME-PREFLIGHT1','MC-CLASS-FOR-NAME-PARENT1');x,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d464f524e414d452d504152454e54000001"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text())
# Retain the already parent-exercised generic/original driver; pin it to this new engine.
wp=json.loads((dcand/'pins.json').read_text());d=(dcand/'tools/driver.go.txt').read_text()
for a,b in [('MC-CLASS-NOT-FOUND-PREFLIGHT1','MC-CLASS-FOR-NAME-PARENT1'),(wp['engine']['runtimeSHA256'],ea['codeHashes']['runtimeSHA256']),(wp['engine']['runtimeKeccak256'],ea['codeHashes']['runtimeKeccak256']),(wp['coordinator']['runtimeKeccak256'],ca['codeHashes']['runtimeKeccak256']),(str(wp['engine']['bytes']),str(size)),('0x4d432d434e46452d505245464c49474854310001','0x4d432d464f524e414d452d504152454e54000001'),('0x4d432d434e46452d4f574e455200000000000002','0x4d432d464f524e414d452d4f574e455200000002')]:assert a in d,a;d=d.replace(a,b)
(out/'main.go').write_text(d)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
result={'basis':'e90909eae','worker':'69ea5129d','domain':'MC-CLASS-FOR-NAME-PARENT1','address':'0x4d432d464f524e414d452d504152454e54000001','owner':'0x4d432d464f524e414d452d4f574e455200000002','runtimeCap':393216,'accepted320Unchanged':True,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'bootstrapSHA256':{'Class':expected},'bootstrapCount':68,'nativeBindings':9,'exceptionKinds':14,'externalLocalGas':1000000000,'resourceLookupGas':1000000,'reserve':25000000,'maxFrames':128,'rawLimits':[24,262144]};(out/'pins.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
