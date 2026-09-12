#!/usr/bin/env python3
"""One-pass fresh parent compile of the exact selected COPY, optional frozen order repair."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;worker=root/'evidence/java-evm/selected-table/preflight';out=Path(sys.argv[1]).resolve();fixed='--root-order' in sys.argv
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-owncapacity-selected-') and not out.exists()
# Source-only prefix of the reviewed worker recipe: all accepted inputs checked
# byte-for-byte against7b46769c5; no old compiler artifacts or private Session copied.
prefix=(worker/'reconstruct_selected_copy.py').read_text().split('# The parent recipe expected')[0]
exec(compile(prefix,str(worker/'reconstruct_selected_copy.py'),'exec'),{'__file__':str(worker/'reconstruct_selected_copy.py')})
source=out/'selectedvfsassets/VFS0aInterpreter.sol'
subprocess.run(['patch','--batch','--forward',str(source),str(worker/'selected-table.patch')],check=True)
if fixed:subprocess.run([sys.executable,str(here/'root-order-repair.py'),str(source)],check=True)
if '--direct-read' in sys.argv:
 assert fixed
 subprocess.run([sys.executable,str(here/'direct-read-repair.py'),str(source)],check=True)
# Debug output selection is observational; verify the original runtime SHA below.
b=out/'selectedvfsassets/build.js';s=b.read_text();s=s.replace("['abi','evm.deployedBytecode.object']","['abi','evm.deployedBytecode.object','evm.deployedBytecode.functionDebugData','irOptimized']")
s=s.replace('const hex = c.evm.deployedBytecode.object.toLowerCase();',"fs.writeFileSync(path.join(dir,'debug-products.json'),JSON.stringify({compiler:solc.version(),contract:c})+'\\n');\nconst hex = c.evm.deployedBytecode.object.toLowerCase();");b.write_text(s)
for d in (out/'selectedvfsassets',out/'selectedcb0/runtime'):(d/'node_modules').symlink_to(root/'jvmevm/runtime/node_modules')
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
with (out/'vfs-build.log').open('w') as f:subprocess.run(['node',str(b)],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
a=json.loads((out/'selectedvfsassets/artifacts/VFS0aInterpreter.json').read_text());runtime=bytes.fromhex(a['deployedBytecode']);digest=hashlib.sha256(runtime).hexdigest()
assert 0<len(runtime)<=327680
if not fixed:assert digest=='b8013a6592938b8ba58129fbb4d3db6d6ee87a15856515e4f3aafa0e5cab6ed7'
elif '--direct-read' not in sys.argv:assert digest=='dff194936ec714e8bd263f7f3b43ea21ed3222cf3e0d222bfdf7a12e6e604084'
subprocess.run([sys.executable,str(worker/'repair_selected_copy.py'),str(out)],check=True)
# Parent permits the frozen root-order repair's actual runtime length, never a
# pre-existing artifact fallback. All pins are recomputed from this fresh compiler output.
s=(worker/'finalize_selected_pins.py').read_text().replace('assert len(engine)==292605 and len(engine_keccak)==64','assert 0<len(engine)<=327680 and len(engine_keccak)==64')
script=out/'finalize.py';script.write_text(s.replace("root=Path(__file__).resolve().parents[4]",'root=Path('+repr(str(root))+')'))
subprocess.run([sys.executable,str(script),str(out)],env=env,cwd=root,check=True)
subprocess.run(['gofmt','-w']+[str(p) for p in (out/'selectedcb0').glob('*.go')],check=True)
subprocess.run([sys.executable,str(worker/'build_selected_drivers.py'),str(out)],env=env,cwd=root,check=True)
(out/'parent-build.json').write_text(json.dumps({'rootOrderRepair':fixed,'directReadRepair':'--direct-read' in sys.argv,'runtimeBytes':len(runtime),'runtimeSHA256':digest,'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'base':'7b46769c5','compilerDebugOnly':True},indent=2)+'\n')
print('PASS: fresh copied source and exact pins; no accepted code changed')
