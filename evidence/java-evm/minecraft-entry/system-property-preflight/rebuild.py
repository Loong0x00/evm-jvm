#!/usr/bin/env python3
"""Rebuild the fixed-64 System-property engine in a fresh ignored tree."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-system-property-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir(); (out/'bootstrap-classes').mkdir()
node_path=os.environ.get('NODE_PATH','')
assert node_path and os.path.isabs(node_path), 'set an absolute NODE_PATH to pinned solc 0.8.30'
env=dict(os.environ, TMPDIR=str(out/'tmp'), NODE_PATH=node_path, PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,(label,p.returncode)
# javac otherwise resolves the pre-existing java.lang.System from rt.jar before
# the supplied source. A private copy with System removed makes this a source build.
api=out/'rt-without-system.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
run('strip-system',['zip','-q','-d',api,'java/lang/System.class','java/lang/System$*.class'])
run('system-java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out/'bootstrap-classes',here/'bootstrap/java/lang/System.java'])
run('system-javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-bootclasspath',str(out/'bootstrap-classes')+':'+str(api),'-c','-p','java.lang.System'])
system=(out/'bootstrap-classes/java/lang/System.class').read_bytes()
jp=(out/'system-javap.log').read_text(); assert 'java.util.Properties properties' in jp and 'getProperty(java.lang.String)' in jp and 'java/lang/IllegalArgumentException' in jp and 'java/lang/String.length' in jp
base=(here/'engine/MCEntryInterpreter.sol').read_text(); old=re.search(r'function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',base); assert old
# Only the pinned System image changes as an image; the nine domain commitments
# necessarily receive their unique engine-domain tag below.
text,n=re.subn(r'function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}', 'function _bootstrapSystem() private pure returns (bytes memory) { return hex"'+system.hex()+'"; }',base); assert n==1
assert text.count('MC-RESOURCE-ENUMERATION-PARENT1')==9
text=text.replace('MC-RESOURCE-ENUMERATION-PARENT1','MC-SYSTEM-PROPERTY-PREFLIGHT1')
assert 'MC-RESOURCE-ENUMERATION-PARENT1' not in text
# A reverse substitution must recover the source byte-for-byte after restoring
# the one pinned System image; this prevents accidental edits to the other 63.
reverse=text.replace('MC-SYSTEM-PROPERTY-PREFLIGHT1','MC-RESOURCE-ENUMERATION-PARENT1')
reverse,n=re.subn(r'function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}', old.group(0), reverse); assert n==1 and reverse==base
eng=out/'engine'; shutil.copytree(here/'engine',eng); (eng/'MCEntryInterpreter.sol').write_text(text); run('engine-build',['node',eng/'build.js'])
ea=json.loads((eng/'MCEntryInterpreter.json').read_text()); size=len(ea['deployedBytecode'])//2; assert size<=384*1024
co=out/'coordinator'; shutil.copytree(here/'coordinator',co); cp=co/'MCEntryCoordinator.sol'; c=cp.read_text(); assert c.count('MC-RESOURCE-ENUMERATION-PARENT1')==3
c=c.replace('MC-RESOURCE-ENUMERATION-PARENT1','MC-SYSTEM-PROPERTY-PREFLIGHT1')
engine_address='0x4d432d53595354454d2d50524f50454e47310000'
assert len(bytes.fromhex(engine_address[2:]))==20
c,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"'+engine_address[2:]+'"));',c); assert n==1
c,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',c); assert n==1
cp.write_text(c); run('coordinator-build',['node',co/'build.js']); ca=json.loads((co/'MCEntryCoordinator.json').read_text())
# Driver is evidence-only public EVM transport. New fixed addresses/domains/pins
# prohibit accidental reuse of the prior engine or coordinator.
d=(here/'tools/evidence.go.txt').read_text(); replacements={
 'MC-RESOURCE-ENUMERATION-PARENT1':'MC-SYSTEM-PROPERTY-PREFLIGHT1',
 'a119cdb383a57e8478d5ec0780e84e70a9d5a5d7e0b9f11832dacd12c59faeba':ea['codeHashes']['runtimeSHA256'],
 '0x5183113f3979d284a00faf6cd2f3d70b5b613f716758e791fe87d485410250d6':'0x'+ea['codeHashes']['runtimeKeccak256'],
 '0x4b516bdd37573efe8eecd65eaafe7401abdeb963c300645e39c57545e7f6caa4':'0x'+ca['codeHashes']['runtimeKeccak256'],
 '348319':str(size),
 '4146':str(len(ca['deployedBytecode'])//2),
 '0x4d432d524553454e554d2d504152454e54000001':engine_address,
 '0x4d432d524553454e554d2d4f574e455200000002':'0x4d432d53595354454d2d50524f504f574e310000',
 '0x4d432d524553454e554d2d4f5448455200000003':'0x4d432d53595354454d2d50524f504f5448310000',
}
for a,b in replacements.items():
 assert a in d,a; d=d.replace(a,b)
assert 'MC-RESOURCE-ENUMERATION-PARENT1' not in d and 'a119cdb383' not in d
(out/'main.go').write_text(d); run('gofmt',['gofmt','-w',out/'main.go']); run('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']); run('go-vet',['go','vet',out/'main.go'])
pins={'basis':'c49360bc3','domain':'MC-SYSTEM-PROPERTY-PREFLIGHT1','address':engine_address,'owner':'0x4d432d53595354454d2d50524f504f574e310000','runtimeCap':393216,'accepted320Unchanged':True,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'system':{'bytes':len(system),'sha256':hashlib.sha256(system).hexdigest(),'priorSHA256':hashlib.sha256(bytes.fromhex(old.group(1))).hexdigest()},'bootstrapCount':64,'externalLocalGas':1000000000,'resourceLookupGas':1000000,'reserve':25000000,'maxFrames':128,'rawLimits':[24,262144]}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n'); print(json.dumps(pins,indent=2))
