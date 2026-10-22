#!/usr/bin/env python3
"""Build an isolated public-driver harness from the exact P39 source snapshot."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'evidence/java-evm/minecraft-entry/max-arrays-8192-source-base-p39'
OUT=Path(sys.argv[1]).resolve()
assert OUT.parent==ROOT/'build' and OUT.name.startswith('java-diff-mc-max-arrays-8192-build-') and not OUT.exists()
node=ROOT/'jvmevm/runtime/node_modules'; assert node.is_dir()
def sha(b): return hashlib.sha256(b).hexdigest()
OUT.mkdir(); shutil.copytree(HERE/'engine',OUT/'engine'); shutil.copytree(HERE/'coordinator',OUT/'coordinator')
engine=json.loads((OUT/'engine/MCEntryInterpreter.json').read_text())
assert len(engine['deployedBytecode'])//2==418986
eng_sha=engine['codeHashes']['runtimeSHA256']; eng_k=engine['codeHashes']['runtimeKeccak256']
coord_src=(OUT/'coordinator/MCEntryCoordinator.sol').read_text()
assert coord_src.count('0x'+eng_k)==0 and coord_src.count(eng_k)==1
# Coordinator build emits ABI/runtime artifact from the exact package-specific source.
env={**os.environ,'NODE_PATH':str(node),'npm_config_offline':'true','GOPROXY':'off','GOSUMDB':'off','GOTOOLCHAIN':'local'}
with (OUT/'coordinator-build.log').open('w') as f: subprocess.run(['node',OUT/'coordinator/build.js'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
coord=json.loads((OUT/'coordinator/MCEntryCoordinator.json').read_text()); coord_k=coord['codeHashes']['runtimeKeccak256']
assert len(coord['deployedBytecode'])//2==5411
# Compile immutable driver source with only profile and immutable-code pins changed.
driver=(HERE/'reference/canonical-driver.go.txt').read_text().replace('MC-HASH-MAP-PUT-BOUNDED-P39','MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192')
repls={
'const immutableEngineSHA256 = "694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6"':f'const immutableEngineSHA256 = "{eng_sha}"',
'const immutableEngineKeccak = "0x26a2d279a04c878d99b094fa93acad3992045500fa68b265d5a021e74530cf3f"':f'const immutableEngineKeccak = "0x{eng_k}"',
'const immutableCoordinatorKeccak = "0xcf82564c399ca2ba8111d0aaedb6287e8e9975db7781fd210abd61c8ecc90b31"':f'const immutableCoordinatorKeccak = "0x{coord_k}"',
}
for a,b in repls.items(): assert driver.count(a)==1,a; driver=driver.replace(a,b)
assert driver.count('const ordinaryGas = uint64(1_000_000_000)')==1
driver=driver.replace('const ordinaryGas = uint64(1_000_000_000)','const ordinaryGas = uint64(32_000_000_000)')
driver=driver.replace('LOCAL1B-USER-AUTHORIZED','LOCAL32B-ARRAY-8192-MEASURED-USER-BUDGET')
(OUT/'driver.go').write_text(driver)
subprocess.run(['gofmt','-w',OUT/'driver.go'],check=True)
assert (OUT/'driver.go').read_text()==(HERE/'reference/p41-driver-snapshot.go.txt').read_text(),'generated driver differs from frozen P41 local harness snapshot'
with (OUT/'go-build.log').open('w') as f: subprocess.run(['go','build','-trimpath','-o',OUT/'driver',OUT/'driver.go'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
with (OUT/'go-vet.log').open('w') as f: subprocess.run(['go','vet',OUT/'driver.go'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
# Preserve exact current pins while refreshing built artifacts and explicit cap metadata.
pins=json.loads((HERE/'pins.json').read_text()); pins['engine']={'bytes':418986,'initSHA256':engine['codeHashes']['initSHA256'],'runtimeSHA256':eng_sha,'runtimeKeccak256':eng_k}; pins['coordinator']={'bytes':5411,'initSHA256':coord['codeHashes']['initSHA256'],'runtimeSHA256':coord['codeHashes']['runtimeSHA256'],'runtimeKeccak256':coord_k}; pins['driverSHA256']=sha((OUT/'driver.go').read_bytes()); pins['sourceHashes']={'engine':sha((HERE/'engine/MCEntryInterpreter.sol').read_bytes()),'coordinator':sha((HERE/'coordinator/MCEntryCoordinator.sol').read_bytes()),'engineBuild':sha((HERE/'engine/build.js').read_bytes()),'coordinatorBuild':sha((HERE/'coordinator/build.js').read_bytes()),'driver':pins['driverSHA256']}; pins['bootstrapRoot']=pins['expectedBootstrapRoot']='ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd'; pins['coordinatorABIUnchangedFromP39']=True; pins['engineABIAndStorageUnchangedFromP39']=True
(OUT/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'buildDir':str(OUT),'engine':pins['engine'],'coordinator':pins['coordinator'],'maxArrays':pins['maxArrays'],'maxObjects':pins['maxObjects'],'maxHandles':pins['maxHandles'],'driverSHA256':pins['driverSHA256']},indent=2))
