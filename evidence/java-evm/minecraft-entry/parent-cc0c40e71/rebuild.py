#!/usr/bin/env python3
"""Independent source-only exact single-Thread profile and LOCAL1B driver."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'thread-context-preflight';basis=here.parent/'parent-d19622e52';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-thread-context-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
classes=out/'bootstrap-classes';classes.mkdir();source=src/'bootstrap/java/lang/Thread.java';run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,source]);image=(classes/'java/lang/Thread.class').read_bytes();assert len(image)==450 and hashlib.sha256(image).hexdigest()=='4c76217e07b547c39ef42523e3cef55af582541265882b6998332124b3f72cb5'
candidate=(src/'artifacts/engine/MCEntryInterpreter.sol').read_text();r=candidate;assert r.count('MC-THREAD-CONTEXT-PREFLIGHT1')==9;r=r.replace('MC-THREAD-CONTEXT-PREFLIGHT1','MC-CLASSLOADER-TYPE-PREFLIGHT1')
pairs=[('bytes32[] memory h = new bytes32[](51);','bytes32[] memory h = new bytes32[](50);'),('        h[50] = keccak256(_bootstrapThread());\n',''),(' || _isReservedThreadClass(users[i])',''),('uint256 count = inputCount + 45 + (suppliedObject ? 0 : 1)','uint256 count = inputCount + 44 + (suppliedObject ? 0 : 1)'),('        p.classes[classSlot + 11].data = _bootstrapThread();\n',''),('''    function _isReservedThreadClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Thread"));
    }

''',''),('''    /// @dev One guest Thread: private Object constructor, static singleton and nullable context field only.
    function _bootstrapThread() private pure returns (bytes memory) { return hex"'''+image.hex()+'''"; }

''','')]
for a,b in pairs:assert r.count(a)==1,a;r=r.replace(a,b)
assert r==(basis/'engine/MCEntryInterpreter.sol').read_text()
engine=out/'engine';shutil.copytree(src/'artifacts/engine',engine);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());assert ea==json.loads((src/'artifacts/engine/MCEntryInterpreter.json').read_text()) and len(ea['deployedBytecode'])//2==326052
co=out/'coordinator';shutil.copytree(src/'artifacts/coordinator',co);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text());assert ca==json.loads((src/'artifacts/coordinator/MCEntryCoordinator.json').read_text())
driver=(basis/'executed_driver.go.txt').read_text()
for a,b in [('MC-CLASSLOADER-TYPE-PREFLIGHT1','MC-THREAD-CONTEXT-PREFLIGHT1'),('c0e9d627b5709f9635731f6d85159b9d33079c33fd1876cbe7b6a258c5912a7b',ea['codeHashes']['runtimeSHA256']),('35f8925e4f8631a9ff23cb5faec1ed6c4db2c0e3d318c9fa21c70693e69a0258',ea['codeHashes']['runtimeKeccak256']),('af03ab895945c9308894496c6f34feb649e18bf28b6471e3d063c604cc5b3e3e',ca['codeHashes']['runtimeKeccak256']),('323026','326052'),('0x4d432d434c4153534c4f414445522d5459504501','0x4d432d5448524541442d434f4e544558542d3031'),('0x4d43434c4153534c4f414445522d4f574e455202','0x4d432d5448524541442d4354582d4f574e455202'),('0x4d43434c4153534c4f414445522d4f5448455203','0x4d432d5448524541442d4354582d4f5448455203')]:assert a in driver,a;driver=driver.replace(a,b)
(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d432d5448524541442d434f4e544558542d3031','owner':'0x4d432d5448524541442d4354582d4f574e455202','domain':'MC-THREAD-CONTEXT-PREFLIGHT1','ThreadSHA256':hashlib.sha256(image).hexdigest(),'prior50BootstrapImagesIdentical':True,'engine':{'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
