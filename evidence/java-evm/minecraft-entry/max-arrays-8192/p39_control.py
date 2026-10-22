#!/usr/bin/env python3
"""Generated-only regression check that exact P39 still OOMs at array 4097."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=ROOT/'evidence/java-evm/minecraft-entry/max-arrays-8192-source-base-p39';NODE=ROOT/'jvmevm/runtime/node_modules'
OUT=Path(sys.argv[1]).resolve();FIX=Path(sys.argv[2]).resolve();assert OUT.parent==ROOT/'build' and OUT.name.startswith('java-diff-mc-max-arrays-8192-p39-control-') and not OUT.exists();assert FIX.parent==ROOT/'build'
OUT.mkdir();env={**os.environ,'NODE_PATH':str(NODE),'npm_config_offline':'true','GOPROXY':'off','GOSUMDB':'off','GOTOOLCHAIN':'local'}
for sub in ('engine','coordinator'):
 shutil.copytree(BASE/sub,OUT/sub)
with (OUT/'engine-build.log').open('w') as f:subprocess.run(['node',OUT/'engine/build.js'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
eng=json.loads((OUT/'engine/MCEntryInterpreter.json').read_text());assert eng['codeHashes']['runtimeSHA256']=='694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6'
with (OUT/'coordinator-build.log').open('w') as f:subprocess.run(['node',OUT/'coordinator/build.js'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
co=json.loads((OUT/'coordinator/MCEntryCoordinator.json').read_text());assert co['codeHashes']['runtimeKeccak256']=='cf82564c399ca2ba8111d0aaedb6287e8e9975db7781fd210abd61c8ecc90b31'
driver=(BASE/'reference/canonical-driver.go.txt').read_text();needle='const ordinaryGas = uint64(1_000_000_000)';assert driver.count(needle)==1;driver=driver.replace(needle,'const ordinaryGas = uint64(32_000_000_000)').replace('LOCAL1B-USER-AUTHORIZED','LOCAL32B-P39-GENERATED-CONTROL')
(OUT/'driver.go').write_text(driver);subprocess.run(['gofmt','-w',OUT/'driver.go'],check=True)
with (OUT/'go-build.log').open('w') as f:subprocess.run(['go','build','-trimpath','-o',OUT/'driver',OUT/'driver.go'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
with (OUT/'go-vet.log').open('w') as f:subprocess.run(['go','vet',OUT/'driver.go'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
world=OUT/'world-4097-q4096';env['MC_ENTRY_BINDINGS']='generated/ArrayCount4097.class';args=[OUT/'driver']
for phase in ('setup-chain','finish','verify'):
 t=time.monotonic();log=OUT/(phase+'.log')
 with log.open('w') as f:r=subprocess.run([*args,phase,world,OUT/'coordinator/MCEntryCoordinator.json',OUT/'engine/MCEntryInterpreter.json',FIX/'array-count-4097.zip','4096'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 assert r.returncode==0,(phase,log)
head=json.loads((world/'durable-head.json').read_text());blob=(world/'checkpoints'/(head['checkpointSHA256']+'.bin')).read_bytes();spec=importlib.util.spec_from_file_location('p39diag',HERE/'checkpoint_diagnostic.py');dmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(dmod);d=dmod.inspect(blob)
assert head['lifecycle']==head['outcome']==3 and head['javaKind']==7 and d['heapCounts']['ordinaryArrays']==4096
assert d['heapCounts']['ordinaryObjects']==0 and d['heapCounts']['arrayElements']<262144
arrays=[x for x in d['heap'] if int(x['metadata'],16)>>255==0];assert len(arrays)==4096
summary={'schema':1,'profile':'exact P39 source-only baseline','generatedOnly':True,'targetArrays':4097,'actualOrdinaryArrays':d['heapCounts']['ordinaryArrays'],'ordinaryObjects':d['heapCounts']['ordinaryObjects'],'arrayElements':d['heapCounts']['arrayElements'],'arrayRecords':len(arrays),'lifecycle':head['lifecycle'],'javaKind':head['javaKind'],'terminalOOM':True,'quantum':4096,'epoch':head['epoch'],'machineRoot':head['machineRoot'],'checkpointSHA256':head['checkpointSHA256'],'checkpointBytes':len(blob),'distinctProcessVerify':True,'sourceBaseEngineSHA256':'4c7b622910e6a379270682c7e9d3477f1ea8e15a6e89bd9111ce937aedf0d54e','baselineRuntimeSHA256':eng['codeHashes']['runtimeSHA256'],'noOriginalInputs':True}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
