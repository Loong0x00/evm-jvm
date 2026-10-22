#!/usr/bin/env python3
"""Verify disposable P42 artifact output against immutable P41 source baseline."""
import argparse, importlib.util, json, os, pathlib

parser=argparse.ArgumentParser()
parser.add_argument('--profile',type=pathlib.Path,required=True)
parser.add_argument('--repo-root',type=pathlib.Path)
a=parser.parse_args();D=a.profile.resolve();ROOT=a.repo_root.resolve() if a.repo_root else next(p for p in D.parents if (p/'.git').exists())
BASE=ROOT/'evidence/java-evm/minecraft-entry/regex-anchor-plus-source-base-p41'
spec=importlib.util.spec_from_file_location('root_helper',D/'reference/root_helper.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
env=os.environ.copy();env['NODE_PATH']=str(ROOT/'jvmevm/runtime/node_modules')
domain='JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1'
record=mod.root_record((D/'engine/MCEntryInterpreter.sol').read_text(),domain,str(ROOT),env)
base=mod.root_record((BASE/'engine/MCEntryInterpreter.sol').read_text(),domain,str(ROOT),env)
changed=[i for i,(x,y) in enumerate(zip(base['leaves'],record['leaves'])) if x!=y]
assert len(record['leaves'])==len(base['leaves'])==105
assert changed==[101,103],changed
pins=json.loads((D/'pins.json').read_text())
assert pins['bootstrapRoot']==record['root'] and pins['expectedBootstrapRoot']==record['root']
assert pins['globalNativeBindings']==21 and pins['maxArrays']==8192 and pins['maxObjects']==4096 and pins['maxHandles']==12545
for name,idx in [('Pattern',101),('PatternSyntaxException',102),('Matcher',103),('String',None)]:
 def image(source):
  import re
  m=re.search(r'function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',source)
  assert m,name
  return bytes.fromhex(m.group(1))
 x=image((D/'engine/MCEntryInterpreter.sol').read_text());y=image((BASE/'engine/MCEntryInterpreter.sol').read_text())
 if idx in (102,None): assert x==y,name
artifacts={}
for name,rel in [('engine','engine/MCEntryInterpreter.json'),('coordinator','coordinator/MCEntryCoordinator.json')]:
 fresh=json.loads((D/rel).read_text());old=json.loads((BASE/rel).read_text());artifacts[name]=fresh
 assert fresh['abi']==old['abi'],name+' ABI changed'
 assert fresh['storageLayout']==old['storageLayout'],name+' storage layout changed'
 obj=pins[name]
 assert fresh['codeHashes']['runtimeSHA256']==obj['runtimeSHA256']
 assert fresh['codeHashes']['runtimeKeccak256']==obj['runtimeKeccak256']
assert artifacts['engine']['compiler']['version']=='0.8.30+commit.73712a01.Emscripten.clang'
engine_hash=artifacts['engine']['codeHashes']['runtimeKeccak256']
coordinator_source=(D/'coordinator/MCEntryCoordinator.sol').read_text()
assert 'ENGINE_CODEHASH = hex"'+engine_hash+'"' in coordinator_source
base_coordinator=(BASE/'coordinator/MCEntryCoordinator.sol').read_text()
import re
normalize=lambda text: re.sub(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',r'\\1ENGINE_CODEHASH\\2',text)
assert normalize(coordinator_source)==normalize(base_coordinator),'coordinator source changed beyond authenticated engine codehash'
report={'checks':'PASS','bootstrapCount':105,'changedBootstrapSlots':changed,'unchangedBootstrapLeaves':103,'bootstrapRoot':record['root'],'p41BootstrapRoot':base['root'],'engineRuntimeBytes':len(bytes.fromhex(json.loads((D/'engine/MCEntryInterpreter.json').read_text())['deployedBytecode'])),'engineRuntimeSHA256':pins['engine']['runtimeSHA256'],'engineRuntimeKeccak256':pins['engine']['runtimeKeccak256'],'coordinatorRuntimeSHA256':pins['coordinator']['runtimeSHA256'],'coordinatorRuntimeKeccak256':pins['coordinator']['runtimeKeccak256'],'engineABIStorageEntries':len(json.loads((D/'engine/MCEntryInterpreter.json').read_text())['abi']),'coordinatorABIStorageEntries':len(json.loads((D/'coordinator/MCEntryCoordinator.json').read_text())['abi']),'globalNativeBindings':21,'maxArrays':8192,'maxObjects':4096,'maxHandles':12545,'StringAndPatternSyntaxExceptionImagesByteIdentical':True,'originalInputsIncluded':False}
(D/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
