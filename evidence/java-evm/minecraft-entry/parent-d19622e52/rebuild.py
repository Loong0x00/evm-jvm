#!/usr/bin/env python3
"""Independent source-only exact ClassLoader type build and authorized1B driver."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'classloader-type-preflight';basis=here.parent/'parent-a30955bb0';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-classloader-type-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
classes=out/'bootstrap-classes';classes.mkdir();source=src/'bootstrap/java/lang/ClassLoader.java';run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,source]);image=(classes/'java/lang/ClassLoader.class').read_bytes();assert len(image)==136 and hashlib.sha256(image).hexdigest()=='df3b18c48b514343c2dcf9d025afd714027e319db03174c8f831215645f39e8b'
candidate=(src/'artifacts/engine/MCEntryInterpreter.sol').read_text();r=candidate
pairs=[('MC-CLASSLOADER-TYPE-PREFLIGHT1','MC-PRIVILEGED-ACTION-PARENT1'),('bytes32[] memory h = new bytes32[](50);','bytes32[] memory h = new bytes32[](49);'),('        h[49] = keccak256(_bootstrapClassLoader());\n',''),('\n                || _isReservedClassLoaderClass(users[i])) {',') {'),('uint256 count = inputCount + 44 + (suppliedObject ? 0 : 1)','uint256 count = inputCount + 43 + (suppliedObject ? 0 : 1)'),('        p.classes[classSlot + 10].data = _bootstrapClassLoader();\n',''),('''    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/ClassLoader"));
    }

''',''),('''    /// @dev Exact minimal Java 8 java.lang.ClassLoader type with protected Object constructor only.
    function _bootstrapClassLoader() private pure returns (bytes memory) { return hex"'''+image.hex()+'''"; }

''','')]
for a,b in pairs:assert r.count(a)==1,a;r=r.replace(a,b)
assert r==(basis/'engine/MCEntryInterpreter.sol').read_text()
engine=out/'engine';shutil.copytree(src/'artifacts/engine',engine);(engine/'MCEntryInterpreter.sol').write_text(candidate);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());assert ea==json.loads((src/'artifacts/engine/MCEntryInterpreter.json').read_text()) and len(ea['deployedBytecode'])//2==323026
co=out/'coordinator';shutil.copytree(src/'artifacts/coordinator',co);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text());assert ca==json.loads((src/'artifacts/coordinator/MCEntryCoordinator.json').read_text())
# Known-good parent driver, mechanically pinned; no worker report-only instrumentation.
driver=(basis/'executed_driver.go.txt').read_text()
for a,b in [('MC-PRIVILEGED-ACTION-PARENT1','MC-CLASSLOADER-TYPE-PREFLIGHT1'),('64f46d45d924e272ca74c0d73f652c68d00cc4709e36ff231483bdf62615c3c9',ea['codeHashes']['runtimeSHA256']),('327a60e7a0a32a621291ed39875df8e9ef18be6dc37374fb6b5a9dbcf6435729',ea['codeHashes']['runtimeKeccak256']),('cf6c798d521a1280e2a42f2f34ee8dfd7e9659d93651bf13435d3e083881d224',ca['codeHashes']['runtimeKeccak256']),('323700','323026'),('0x4d432d505249564143542d504152454e54310001','0x4d432d434c4153534c4f414445522d5459504501'),('0x4d432d505249564143542d4f574e455200000002','0x4d43434c4153534c4f414445522d4f574e455202'),('0x4d432d505249564143542d4f5448455200000003','0x4d43434c4153534c4f414445522d4f5448455203')]:assert a in driver,a;driver=driver.replace(a,b)
(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d432d434c4153534c4f414445522d5459504501','owner':'0x4d43434c4153534c4f414445522d4f574e455202','domain':'MC-CLASSLOADER-TYPE-PREFLIGHT1','ClassLoaderSHA256':hashlib.sha256(image).hexdigest(),'prior49BootstrapImagesIdentical':True,'engine':{'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
