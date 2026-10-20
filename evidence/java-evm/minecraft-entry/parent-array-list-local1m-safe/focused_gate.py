#!/usr/bin/env python3
"""Independent ordinary1B constructor/reopen/eager-storage and atomic-refusal gate."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
build,fixtures,out=map(lambda x:Path(x).resolve(),sys.argv[1:4]);assert build.parent==fixtures.parent==out.parent==ROOT/'build' and not out.exists();out.mkdir();(out/'logs').mkdir();started=time.monotonic();pins=json.load(open(build/'pins.json'));assert pins['bootstrapCount']==99 and pins['runtimeCap']==1048576
spec=importlib.util.spec_from_file_location('cp',ROOT/'evidence/java-evm/minecraft-entry/raw75-byte531965/tools/checkpoint_diagnostic.py');diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
commands=[];canonical=[];results={}
def run(label,args,entries):
 env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),MC_ENTRY_BINDINGS=','.join(entries),GOPROXY='off',GOSUMDB='off');env.pop('MC_ENTRY_SELECTED_RESOURCE',None);t=time.monotonic()
 with (out/'logs'/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
 row={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};commands.append(row);assert p.returncode==0,row
for label in ('constructor','add-refusal','iterator-refusal','interface-add-refusal','interface-iterator-refusal','default-refusal','list-object-fallback','equals-refusal','object-hash-refusal'):
 meta=json.load(open(fixtures/(label+'.json')));values={}
 for q in ((1,7,4096,65536) if label=='constructor' else (1,)):
  world=out/(label+'-q'+str(q));args=[world,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',fixtures/(label+'.zip'),str(q)]
  run(label+f'-q{q}-start',[build/'driver','setup-chain',*args],meta['entries']);run(label+f'-q{q}-finish',[build/'driver','finish',*args],meta['entries']);reports=out/'reports'/world.name;h=json.load(open(world/'durable-head.json'));rf=reports/'resume-refusal.json';sf=reports/'start-refusal.json'
  if label!='constructor':
   refusal=json.load(open(rf if rf.exists() else sf));assert refusal['rootUnchanged'] and refusal['durableHeadUnchanged'] and refusal['checkpointBytes']==0;assert refusal['selector']=='0xd631c3a4';assert refusal['uint256Words'][0]==('3' if label=='default-refusal' else '4');run(label+'-reopen',[build/'driver','verify',*args],meta['entries']);values[str(q)]={'atomic':True,'selector':refusal['selector'],'words':refusal['uint256Words'],'root':h['trieRoot'],'epoch':h['epoch']};continue
  assert not rf.exists() and not sf.exists() and h['lifecycle']==2 and h['javaKind']==0;run(label+f'-q{q}-reopen',[build/'driver','verify',*args],meta['entries']);blob=(world/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();s=diag.inspect(blob);assert s['classCount']==100
  statics=next(v for v in s['initialization'] if v['classIndex']==0)['staticValues'];assert int(statics[1]['packedValue'],16)==(1<<64)|12345
  lists=[v for v in s['heap'] if v['classIndex']==99 and int(v['metadata'],16)>>255];assert len(lists)==7
  allheap={v['handle']:v for v in s['heap']};capacities=[]
  for v in lists:
   assert len(v['cells'])==2 and int(v['cells'][1],16)==1<<64
   handle=int(v['cells'][0],16)&((1<<64)-1)
   if handle:
    backing=allheap[handle];assert backing['rank']==1 and backing['metadata']=='0x101' and all(int(x,16)==0 for x in backing['cells']);capacities.append(backing['count'])
  assert sorted(capacities)==[0,1,3,10,1024]
  values[str(q)]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'mr01SHA256':hashlib.sha256(blob[280:]).hexdigest(),'backingCapacities':capacities,'resultField':12345};canonical.append(world.name)
 if label=='constructor':
  assert len({(x['jvmSteps'],x['internalSteps'],x['machineRoot'],x['mr01SHA256']) for x in values.values()})==1
 results[label]=values
# Canonical verifier on successful constructor chains; refusals checked directly against immutable prior heads.
module=ROOT/'jvmevm/runtime/node_modules';env=dict(os.environ,NODE_PATH=str(module));p=subprocess.run(['node',H/'verify_receipts.js',build,out,'1',*canonical],cwd=ROOT,env=env,text=True,capture_output=True,check=True);verification=json.loads(p.stdout)
elapsed=time.monotonic()-started;assert elapsed<=1200;summary={'scope':'generated-only independent LOCAL1M constructor profile; no original inputs/results','seconds':elapsed,'runtimeBytes':pins['engine']['bytes'],'runtimeCap':1048576,'bootstrapRoot':pins['bootstrapRoot'],'results':results,'canonicalReceipts':verification,'commands':commands,'unhandledListHashEqualityMutationIteratorRefuseAtomically':True};(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'seconds':elapsed,'verifiedReceipts':verification['verifiedReceipts'],'constructorJvmSteps':results['constructor']['1']['jvmSteps'],'nativeRefusalControls':len(results)-1}))
