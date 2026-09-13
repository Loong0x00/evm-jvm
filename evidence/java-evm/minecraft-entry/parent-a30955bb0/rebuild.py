#!/usr/bin/env python3
"""Independent source-only PrivilegedAction build with repaired full domain isolation."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'privileged-action-preflight';basis=here.parent/'parent-2293e298e'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-privileged-action-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
# Independent Java8 interface build.
classes=out/'bootstrap-classes';classes.mkdir();source=src/'bootstrap/java/security/PrivilegedAction.java'
run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,source]);action=(classes/'java/security/PrivilegedAction.class').read_bytes();assert len(action)==198 and hashlib.sha256(action).hexdigest()=='8188676e90fe79c605761b4592483b511966e7396f8a14e0d9b7962f00d948da'
# Reverse the worker's exact semantic delta and prove no hidden inherited changes.
candidate=(src/'artifacts/engine/MCEntryInterpreter.sol').read_text();r=candidate
pairs=[
('keccak256("JVMEVM:MC-PRIVILEGED-ACTION-PREFLIGHT1:BOOTSTRAP:1")','keccak256("JVMEVM:MC-SECURITY-GETTER-PREFLIGHT1:BOOTSTRAP:1")'),
('bytes32[] memory h = new bytes32[](49);','bytes32[] memory h = new bytes32[](48);'),
('        h[48] = keccak256(_bootstrapPrivilegedAction());\n',''),
(' || _isReservedPrivilegedActionClass(users[i])',''),
('uint256 count = inputCount + 43 + (suppliedObject ? 0 : 1)','uint256 count = inputCount + 42 + (suppliedObject ? 0 : 1)'),
('        // Appended after the existing 48 pinned images; caller replacement is rejected.\n        p.classes[classSlot + 9].data = _bootstrapPrivilegedAction();\n',''),
('''    function _isReservedPrivilegedActionClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/security/PrivilegedAction"));
    }

''',''),
('''    /// @dev Exact Java 8 java.security.PrivilegedAction<T>; this interface grants no privilege.
    function _bootstrapPrivilegedAction() private pure returns (bytes memory) { return hex"'''+action.hex()+'''"; }

''','')]
for a,b in pairs:assert r.count(a)==1,a;r=r.replace(a,b)
assert r==(basis/'engine/MCEntryInterpreter.sol').read_text()
# Worker changed only DBOOT; parent repairs all nine engine identity domains.
domain='MC-PRIVILEGED-ACTION-PARENT1';engine=out/'engine';shutil.copytree(src/'artifacts/engine',engine);s=candidate.replace('MC-SECURITY-GETTER-PREFLIGHT1',domain).replace('MC-PRIVILEGED-ACTION-PREFLIGHT1',domain);assert s.count(domain)==9 and 'MC-SECURITY-GETTER' not in s and 'MC-PRIVILEGED-ACTION-PREFLIGHT1' not in s;(engine/'MCEntryInterpreter.sol').write_text(s)
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";';old=dict(re.findall(pat,(basis/'engine/MCEntryInterpreter.sol').read_text()));new=dict(re.findall(pat,s));assert len(old)==48 and len(new)==49 and all(new[k]==v for k,v in old.items()) and new['_bootstrapPrivilegedAction']==action.hex()
run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());assert len(ea['deployedBytecode'])//2<=327680
# Coordinator gets the same full parent domain and new code identity.
co=out/'coordinator';shutil.copytree(src/'artifacts/coordinator',co);s=(co/'MCEntryCoordinator.sol').read_text().replace('MC-PRIVILEGED-ACTION-PREFLIGHT1',domain).replace('05259639552222f01f3ba651c88175ea9a03926d877bc7825c6cf0f1fd8038d5',ea['codeHashes']['runtimeKeccak256']);s,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d505249564143542d504152454e54310001"));',s);assert n==1;(co/'MCEntryCoordinator.sol').write_text(s)
run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text())
# Derive execution harness from last parent-verified LOCAL1B source.
driver=(basis/'executed_driver.go.txt').read_text()
for a,b in [('MC-SECURITY-GETTER-PREFLIGHT1',domain),('4a8aafbfafef9fed3c3fd3106d99b9819a40ecc2eccfe40e234efa448dc038f9',ea['codeHashes']['runtimeSHA256']),('74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae',ea['codeHashes']['runtimeKeccak256']),('113bcbc2b3512af2cbddc90379dbc8cacfb64f7df50ef7ec8f89e1bdfe8ed59a',ca['codeHashes']['runtimeKeccak256']),('322301',str(len(ea['deployedBytecode'])//2)),('0x4d43534543555249545947455454455200000001','0x4d432d505249564143542d504152454e54310001'),('0x4d52304d41494e454e47494e4500000000000002','0x4d432d505249564143542d4f574e455200000002'),('0x4d52304d41494e454e47494e4500000000000003','0x4d432d505249564143542d4f5448455200000003')]:assert a in driver,a;driver=driver.replace(a,b)
(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d432d505249564143542d504152454e54310001','owner':'0x4d432d505249564143542d4f574e455200000002','domain':domain,'PrivilegedActionSHA256':hashlib.sha256(action).hexdigest(),'prior48BootstrapImagesIdentical':True,'engine':{'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
