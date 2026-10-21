#!/usr/bin/env python3
"""Re-run generated raw150 gates against independently built P35 code/domain/pins."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];STAGE=H.parent/'hash-map-default-constructor'
build,fixtures,out=map(lambda p:Path(p).resolve(),sys.argv[1:4]);assert build.parent==fixtures.parent==out.parent==ROOT/'build' and not out.exists() and not fixtures.exists()
pins=json.load(open(build/'pins.json'));assert pins['rawLimits']==[150,1063930] and pins['bootstrapCount']==101 and pins['runtimeCap']==1048576 and pins['maxCheckpointBytes']==2097152
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'))
subprocess.run([sys.executable,STAGE/'tools/generate_fixtures.py',fixtures],cwd=ROOT,env=env,check=True,stdout=(out/'fixtures.log').open('w'),stderr=subprocess.STDOUT,timeout=300)
tools=out/'tools';tools.mkdir();patches=[]
for name in ('evm_driver.go','coordinator_route.go'):
 text=(STAGE/'tools'/name).read_text();old='0x4d432d52414e444f4d2d434c4153532d5031006c';n=text.count(old);text=text.replace(old,pins['address']).replace('0x4d432d52414e444f4d2d434c4153532d5031006d',pins['owner']);k=text.count('MC-CHECKPOINT-2M-P34');text=text.replace('MC-CHECKPOINT-2M-P34',pins['domain']);(tools/name).write_text(text);patches.append({'file':name,'addressOccurrences':n,'domainOccurrences':k})
subprocess.run(['go','build','-trimpath','-o',out/'generated-driver','./'+tools.relative_to(ROOT).as_posix()],cwd=ROOT,env=env,check=True,timeout=300)
spec=importlib.util.spec_from_file_location('raw150_gate',STAGE/'tools/run_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);t=time.monotonic();result=m.run_attempt(1,1_000_000_000,1200,build_dir=build,fixture_dir=fixtures,driver_bin=out/'generated-driver',engine_path=build/'engine/MCEntryInterpreter.json',coordinator_path=build/'coordinator/MCEntryCoordinator.json',attempt_dir=out/'attempt-1',env=env)
assert result['status']=='passed' and result['gasBudget']==1000000000;result['parentDomain']=pins['domain'];result['parentRuntimeSHA256']=pins['engine']['runtimeSHA256'];result['actualGateSeconds']=time.monotonic()-t;result['testDriverOnlyPatches']=patches;result['notOriginalInputs']=True;(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'domain':pins['domain'],'seconds':result['actualGateSeconds'],'coordinatorCalls':result['coordinator']['evmCallCount'],'maximumGas':result['coordinator']['maxCallGas'],'rawCount':result['coordinator']['rawCount'],'rawBytes':result['coordinator']['rawBytes'],'checkpointBytes':result['coordinator']['checkpointBytes']}))
