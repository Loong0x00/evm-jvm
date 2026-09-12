#!/usr/bin/env python3
"""Fresh independent reconstruction of incomplete worker COPY recipe, no accepted edits."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];src=root/'evidence/java-evm/capacity-baseline/preflight';out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-capacity-') and not out.exists(),out
out.mkdir(parents=True);(out/'tmp').mkdir();os.environ['TMPDIR']=str(out/'tmp')
os.environ['NODE_PATH']=str(root/'jvmevm/runtime/node_modules')
records=[]
def cp(rel,dst):
 p=root/rel;b=p.read_bytes();expected=subprocess.check_output(['git','show','7b46769c5:'+rel],cwd=root);assert b==expected,rel
 dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);records.append({'source':rel,'sha256':hashlib.sha256(b).hexdigest()})
def patch(dst,name):
 text=gzip.decompress((src/'patches'/name).read_bytes())
 subprocess.run(['patch','--batch','--forward',str(dst)],input=text,check=True)
# Bootstrap source/hex files and compiler are accepted and unchanged. Artifacts are NOT copied.
a=out/'capacityvfsassets'
for rel in ['VFS0aInterpreter.sol','build.js','assets.go','package.json','package-lock.json']:
 cp('jvmevm/runtime/local/vfs0a/'+rel,a/rel)
for p in (root/'jvmevm/runtime/local/vfs0a/bootstrap').rglob('*'):
 if p.is_file():cp(str(p.relative_to(root)),a/'bootstrap'/p.relative_to(root/'jvmevm/runtime/local/vfs0a/bootstrap'))
patch(a/'VFS0aInterpreter.sol','vfs0a-capacity.patch.gz')
p=a/'assets.go';p.write_text(p.read_text().replace('package vfs0aassets','package capacityvfsassets'))
# The worker omitted these two adapter/asset recipe steps; reconstruct them explicitly.
v=out/'capacityvfs/vfs0a.go';cp('jvmevm/localcontinuation/vfs0a/vfs0a.go',v)
module='github.com/ethereum/go-ethereum/'+str(out.relative_to(root))
v.write_text(v.read_text().replace('package vfs0a','package capacityvfs',1).replace('github.com/ethereum/go-ethereum/jvmevm/runtime/local/vfs0a',module+'/capacityvfsassets'))
c=out/'capacitycb0';r=c/'runtime'
for rel in ['CB0ClassCoordinator.sol','build.js','assets.go','package.json','package-lock.json']:
 cp('jvmevm/localcontinuation/cb0/runtime/'+rel,r/rel)
patch(r/'CB0ClassCoordinator.sol','cb0-coordinator-capacity.patch.gz');patch(r/'build.js','cb0-build-capacity.patch.gz')
for rel,pt in [('artifact.go','cb0-artifact.go.capacity.patch.gz'),('cb0.go','cb0-profile-capacity.patch.gz'),('head.go','cb0-head.go.capacity.patch.gz'),('session.go','cb0-session.go.capacity.patch.gz')]:
 cp('jvmevm/localcontinuation/cb0/'+rel,c/rel);patch(c/rel,pt)
 p=c/rel;p.write_text(p.read_text().replace('github.com/ethereum/go-ethereum/build/java-diff-mc-capacity-proto-smoke',module))
(out/'base-sources.json').write_text(json.dumps(records,indent=2)+'\n')
for name,path in [('vfs',a),('coordinator',r)]:
 with (out/(name+'-build.log')).open('w') as f:subprocess.run(['node',str(path/'build.js')],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
# Pins below are the worker's exact experimental artifacts, not synthesized Go constants.
va=json.loads((a/'artifacts/VFS0aInterpreter.json').read_text());ca=json.loads((r/'combinedartifacts/CB0ClassCoordinator.json').read_text())
vb=bytes.fromhex(va['deployedBytecode'].removeprefix('0x'));assert len(vb)==292968 and hashlib.sha256(vb).hexdigest()=='4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f'
assert hashlib.sha256((r/'combinedartifacts/CB0ClassCoordinator.json').read_bytes()).hexdigest()=='c0d3dfead16a7658b7deb3712f06c7c16e7cce75070d3d1d82e2aa81260cdc33'
assert ca['codeHashes']['deployedBytecodeKeccak256']=='b1a044dc0d9a9752d0489031f0e61118ec8778b57d1bebe229af2d7cec71c115'
# Reproduce the worker's uncorrected same-session VM cache, so the parent can test it.
assert 'MC-CB0/vm/v1' in (c/'session.go').read_text()
subprocess.run(['gofmt','-w',str(v),str(a/'assets.go')]+[str(c/f) for f in ['artifact.go','cb0.go','head.go','session.go']],check=True)
subprocess.run(['go','test','./'+str((out/'capacityvfs').relative_to(root)),'./'+str(c.relative_to(root))],cwd=root,check=True)
(out/'reconstructed.json').write_text(json.dumps({'vfsRuntimeBytes':len(vb),'vfsRuntimeSHA256':hashlib.sha256(vb).hexdigest(),'coordinatorArtifactSHA256':hashlib.sha256((r/'combinedartifacts/CB0ClassCoordinator.json').read_bytes()).hexdigest(),'codePinsMatched':True,'knownPendingRepairs':['same-session VM domain cache','exact constructor argument bound','trace instrumentation and gates']},indent=2)+'\n')
print('PASS: exact worker experiment independently compiled; NOT accepted and cache defect still present')
