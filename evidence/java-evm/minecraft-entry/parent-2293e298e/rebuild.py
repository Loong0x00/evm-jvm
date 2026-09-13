#!/usr/bin/env python3
"""Independent source-only rebuild of exact getter candidate and LOCAL1B driver."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'security-getter-preflight';basis=here.parent/'parent-c24d374bc';budget=here.parent/'local-budget-1b'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-security-getter-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as log:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
# Compile the guest source independently and require exact pinned image.
shutil.copytree(src/'bootstrap',out/'bootstrap');classes=out/'bootstrap-classes';classes.mkdir()
run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,out/'bootstrap/java/lang/System.java'])
system=(classes/'java/lang/System.class').read_bytes();assert hashlib.sha256(system).hexdigest()=='2dbd8eb88dfc0ed82e0bf84e6a1c06e7530b666674c461e857416782e77bf49a' and len(system)==338
for kind in ('engine','coordinator'):
 shutil.copytree(basis/kind,out/kind)
engine=out/'engine/MCEntryInterpreter.sol';s=engine.read_text();pattern=r'(function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex")([0-9a-f]+)("; \})';m=re.search(pattern,s);assert m
parentSystem=m.group(2);s,n=re.subn(pattern,lambda m:m.group(1)+system.hex()+m.group(3),s);assert n==1;s=s.replace('MC-PROPERTIES-PARENT1','MC-SECURITY-GETTER-PREFLIGHT1');engine.write_text(s)
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";';a=dict(re.findall(pat,(basis/'engine/MCEntryInterpreter.sol').read_text()));b=dict(re.findall(pat,s));assert len(a)==len(b)==48 and all(b[k]==v for k,v in a.items() if k!='_bootstrapSystem') and a['_bootstrapSystem']==parentSystem
run('engine-build',['node',out/'engine/build.js']);ea=json.loads((out/'engine/MCEntryInterpreter.json').read_text());assert ea==json.loads((src/'candidate/engine/MCEntryInterpreter.json').read_text())
co=out/'coordinator/MCEntryCoordinator.sol';s=co.read_text().replace('MC-PROPERTIES-PARENT1','MC-SECURITY-GETTER-PREFLIGHT1').replace('eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7',ea['codeHashes']['runtimeKeccak256']);s,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d43534543555249545947455454455200000001"));',s);assert n==1;co.write_text(s)
run('coordinator-build',['node',out/'coordinator/build.js']);ca=json.loads((out/'coordinator/MCEntryCoordinator.json').read_text());assert ca==json.loads((src/'candidate/coordinator/MCEntryCoordinator.json').read_text())
# Start from the actually executed, explicitly authorized LOCAL1B source.
driver=(budget/'executed_driver.go.txt').read_text()
for a,b in [('877f35a4ac4092a7c65ab5071104413e4579ced0b69a172852db77d772aee1bb',ea['codeHashes']['runtimeSHA256']),('eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7',ea['codeHashes']['runtimeKeccak256']),('4ac62a3ecc1612110cbc97779ebf760d101a33f1c85ddfb03c75d1b5478f2bae',ca['codeHashes']['runtimeKeccak256']),('0x4d4350524f50455254494553504152454e540001','0x4d43534543555249545947455454455200000001'),('MC-PROPERTIES-PARENT1','MC-SECURITY-GETTER-PREFLIGHT1'),('321590','322301')]:assert a in driver;driver=driver.replace(a,b)
# Worker omitted cosmetic 0x prefixes on two common.HexToHash string constants.
# Keep the parent's canonical prefixed form and prove this is the only source difference.
workerDriver=(src/'candidate/executed_generated_driver.go.txt').read_text()
assert workerDriver==driver.replace('0x'+ea['codeHashes']['runtimeKeccak256'],ea['codeHashes']['runtimeKeccak256']).replace('0x'+ca['codeHashes']['runtimeKeccak256'],ca['codeHashes']['runtimeKeccak256'])
(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d43534543555249545947455454455200000001','domain':'MC-SECURITY-GETTER-PREFLIGHT1','systemSHA256':hashlib.sha256(system).hexdigest(),'other47BootstrapImagesIdentical':True,'engine':{'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
