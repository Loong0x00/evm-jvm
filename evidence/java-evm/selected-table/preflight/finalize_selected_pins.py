#!/usr/bin/env python3
"""Bind the isolated coordinator only to the freshly compiled selected COPY engine."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4]
out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-owncapacity-selected-')
vfs=out/'selectedvfsassets'/'artifacts'/'VFS0aInterpreter.json'
coord=out/'selectedcb0'/'runtime'
a=json.loads(vfs.read_text());engine=bytes.fromhex(a['deployedBytecode'])
# The copied coordinator has js-sha3 pinned by its copied lockfile; do not use a
# host/global compiler or a non-Keccak SHA3 substitute.
node="const fs=require('fs'),{keccak256}=require(process.argv[1]);const a=JSON.parse(fs.readFileSync(process.argv[2]));console.log(keccak256(Buffer.from(a.deployedBytecode,'hex')));"
module=str(coord/'node_modules'/'js-sha3')
engine_keccak=subprocess.check_output(['node','-e',node,module,str(vfs)],text=True).strip()
assert len(engine)==292605 and len(engine_keccak)==64
old='2beb5ef477d93f1479cdf7dfcb18e37792de9b0643b0ee57e15ba74f9e9d59e6'
def replace(path, before, after):
    s=path.read_text(); assert before in s,(path,before); path.write_text(s.replace(before,after))
replace(coord/'CB0ClassCoordinator.sol',old,engine_keccak)
replace(coord/'CB0ClassCoordinator.sol','MC-CAPACITY-PREFLIGHT','MC-SELECTED-TABLE-PREFLIGHT')
replace(coord/'build.js',old,engine_keccak)
replace(out/'selectedcb0'/'artifact.go',old,engine_keccak)
replace(out/'selectedcb0'/'cb0.go','MC-CAPACITY-PREFLIGHT','MC-SELECTED-TABLE-PREFLIGHT')
env=dict(os.environ,TMPDIR=str(out/'tmp'))
with (out/'selected-coordinator-build.log').open('w') as log:
    subprocess.run(['node',str(coord/'build.js')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
artifact=coord/'combinedartifacts'/'CB0ClassCoordinator.json'
d=json.loads(artifact.read_text())
# Go's json.Marshal on map/interface is the artifact validator's canonical form.
helper=out/'canonical_sha.go'
helper.write_text(r'''package main
import("crypto/sha256";"encoding/hex";"encoding/json";"fmt";"os")
func h(b []byte)string{x:=sha256.Sum256(b);return hex.EncodeToString(x[:])}
func main(){var d map[string]interface{}; b,_:=os.ReadFile(os.Args[1]); if json.Unmarshal(b,&d)!=nil{panic("json")}; for _,k:=range []string{"abi","storageLayout"}{x,_:=json.Marshal(d[k]);fmt.Println(k,h(x))}}''')
canon=dict(line.split() for line in subprocess.check_output(['go','run',str(helper),str(artifact)],cwd=root,env=env,text=True).splitlines())
init=bytes.fromhex(d['bytecode']);runtime=bytes.fromhex(d['deployedBytecode'])
# Reuse the copied pinned js-sha3 for the actual EVM code hash.
node_runtime="const fs=require('fs'),{keccak256}=require(process.argv[1]);const a=JSON.parse(fs.readFileSync(process.argv[2]));console.log(keccak256(Buffer.from(a.deployedBytecode,'hex')));"
runtime_keccak=subprocess.check_output(['node','-e',node_runtime,module,str(artifact)],text=True).strip()
values={
 'cb0ArtifactSHA256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
 'cb0SourceSHA256':hashlib.sha256((coord/'CB0ClassCoordinator.sol').read_bytes()).hexdigest(),
 'cb0InitSHA256':hashlib.sha256(init).hexdigest(),
 'cb0RuntimeSHA256':hashlib.sha256(runtime).hexdigest(),
 'cb0ABISHA256':canon['abi'], 'cb0LayoutSHA256':canon['storageLayout'],
 'cb0RuntimeKeccak':runtime_keccak,
}
p=out/'selectedcb0'/'artifact.go';s=p.read_text()
import re
for key,value in values.items():
    s,n=re.subn(r'('+key+r'\s*=\s*)"[0-9a-f]+"',r'\g<1>"'+value+'"',s,count=1)
    assert n==1,key
p.write_text(s)
(out/'selected-pins.json').write_text(json.dumps({
 'engineRuntimeBytes':len(engine),'engineRuntimeSHA256':hashlib.sha256(engine).hexdigest(),
 'engineRuntimeKeccak256':engine_keccak,'engineSourceSHA256':a['sourceHashes']['VFS0aInterpreter.sol'],
 'coordinatorArtifactSHA256':values['cb0ArtifactSHA256'],'coordinatorRuntimeKeccak256':runtime_keccak,
 'coordinatorRuntimeBytes':len(runtime),'domain':'MC-SELECTED-TABLE-PREFLIGHT'
},indent=2)+'\n')
print((out/'selected-pins.json').read_text(),end='')
