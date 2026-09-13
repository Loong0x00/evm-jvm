#!/usr/bin/env python3
"""Parent repair/rebuild: Java HashSet uses incoming-key equals per Java8 HashMap."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];cand=here.parent/'linked-hash-set-preflight';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-linked-hash-set-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,check=True):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if check:assert p.returncode==0,(label,p.returncode)
 return p.returncode
classes=out/'bootstrap-classes';classes.mkdir();sources=sorted((here/'bootstrap').rglob('*.java'));run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sources]);names=['Iterator','Collection','Set','AbstractCollection','AbstractSet','HashSet','LinkedHashSet','HashSetIterator','NoSuchElementException'];images={n:(classes/'java/util'/(n+'.class')).read_bytes() for n in names};pins=json.loads((cand/'pins.json').read_text());
for n in names:
 h=hashlib.sha256(images[n]).hexdigest()
 if n=='HashSet':assert h!=pins['bootstrapSHA256'][n]
 else:assert h==pins['bootstrapSHA256'][n],(n,h)
run('javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-classpath',classes,'-p','-s',*[('java.util.'+n) for n in names]])
# Replace only repaired HashSet bytes, and isolate parent domains.
s=(cand/'source/engine/MCEntryInterpreter.sol').read_text();pat=r'function _bootstrapHashSet\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}';rep='function _bootstrapHashSet() private pure returns (bytes memory) { return hex"'+images['HashSet'].hex()+'"; }';s,n=re.subn(pat,rep,s);assert n==1;assert s.count('MC-LINKED-HASH-SET-PREFLIGHT1')==9;s=s.replace('MC-LINKED-HASH-SET-PREFLIGHT1','MC-LINKED-HASH-SET-PARENT1')
engine=out/'engine';shutil.copytree(cand/'source/engine',engine);(engine/'MCEntryInterpreter.sol').write_text(s);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert 327680<size<=393216
co=out/'coordinator';shutil.copytree(cand/'source/coordinator',co);p=co/'MCEntryCoordinator.sol';x=p.read_text();assert x.count('MC-LINKED-HASH-SET-PREFLIGHT1')==3;x=x.replace('MC-LINKED-HASH-SET-PREFLIGHT1','MC-LINKED-HASH-SET-PARENT1');x,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d4c48532d504152454e5400000000000001"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text())
d=(cand/'tools-driver.go.txt').read_text()
for a,b in [('MC-LINKED-HASH-SET-PREFLIGHT1','MC-LINKED-HASH-SET-PARENT1'),(pins['engine']['runtimeSHA256'],ea['codeHashes']['runtimeSHA256']),(pins['engine']['runtimeKeccak256'],ea['codeHashes']['runtimeKeccak256']),(pins['coordinator']['runtimeKeccak256'],ca['codeHashes']['runtimeKeccak256']),(str(pins['engine']['bytes']),str(size)),('0x4d432d4c48532d505245464c4947485431000001','0x4d432d4c48532d504152454e5400000000000001'),('0x4d432d4c48532d505245464c4f574e4552000002','0x4d432d4c48532d4f574e45520000000000000002'),('0x4d432d4c48532d505245464c4f54484552000003','0x4d432d4c48532d4f544845520000000000000003')]:assert a in d,a;d=d.replace(a,b)
(out/'main.go').write_text(d)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
result={'basis':'696994208','repair':'incoming item.equals(existing), matching Java8 HashMap.putVal key.equals(k)','domain':'MC-LINKED-HASH-SET-PARENT1','address':'0x4d432d4c48532d504152454e5400000000000001','owner':'0x4d432d4c48532d4f574e45520000000000000002','runtimeCap':393216,'accepted320Unchanged':True,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'bootstrapSHA256':{n:hashlib.sha256(images[n]).hexdigest() for n in names},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128,'bootstrapCount':61,'rawLimits':[24,262144]};(out/'pins.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
