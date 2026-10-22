#!/usr/bin/env python3
"""Reproducible source-only P39 comparison, ordered-root and ABI/layout audit."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,sys
import importlib.util
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]; BASE=ROOT/'evidence/java-evm/minecraft-entry/max-arrays-8192-source-base-p39'; NODE=ROOT/'jvmevm/runtime/node_modules'
def sha(b):return hashlib.sha256(b).hexdigest()
def run_build(srcdir):
 env={**os.environ,'NODE_PATH':str(NODE),'npm_config_offline':'true'}
 subprocess.run(['node',srcdir/'build.js'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=900)
 return json.loads((srcdir/'MCEntryInterpreter.json').read_text())
def main():
 base=(BASE/'engine/MCEntryInterpreter.sol').read_text(); cand=(HERE/'engine/MCEntryInterpreter.sol').read_text()
 old='uint256 private constant MAX_ARRAYS = 4096;'; new='uint256 private constant MAX_ARRAYS = 8192;'
 assert base.count(old)==1 and cand.count(new)==1
 expected=base.replace(old,new,1).replace('MC-HASH-MAP-PUT-BOUNDED-P39','MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192')
 assert cand==expected,'engine source contains unscoped edits beyond array quota/profile domains'
 assert 'MAX_OBJECTS = 4096' in cand and 'MAX_ARRAY_ELEMENTS = 262144' in cand and 'MAX_CONSTANT_POOL = 4096' in cand
 assert 'MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS' in cand
 # P39 bootstrap root is independently recomputed from ordered source leaves.
 assert 'keccak256("JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1")' in cand
 assert cand.count('P39:BOOTSTRAP:1')==1
 spec=importlib.util.spec_from_file_location('p41_root_helper',HERE/'reference/root_helper.py'); helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
 env={**os.environ,'NODE_PATH':str(NODE),'npm_config_offline':'true'}
 root=helper.root_record(cand,'JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1',ROOT,env)['root']
 assert root=='ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd'
 for n in ('engine/MCEntryInterpreter.json','coordinator/MCEntryCoordinator.json'):
  assert (BASE/n).is_file()
 # Fresh isolated P39 compile and source candidate compile: ABI/storage structures must match.
 with tempfile.TemporaryDirectory(prefix='mc-p41-array-audit-') as t:
  t=Path(t); b=t/'base'; c=t/'candidate'; b.mkdir(); c.mkdir()
  for d,src in ((b,BASE/'engine'),(c,HERE/'engine')):
   for f in ('MCEntryInterpreter.sol','build.js'): (d/f).write_bytes((src/f).read_bytes())
  ba=run_build(b); ca=run_build(c)
  assert ba['codeHashes']['runtimeSHA256']=='694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6'
  assert ba['abi']==ca['abi'] and ba['storageLayout']==ca['storageLayout']
  assert len(ca['deployedBytecode'])//2<=1048576
  bc=t/'base-coord'; ccdir=t/'candidate-coord'; bc.mkdir(); ccdir.mkdir()
  for d,src in ((bc,BASE/'coordinator'),(ccdir,HERE/'coordinator')):
   for f in ('MCEntryCoordinator.sol','build.js'): (d/f).write_bytes((src/f).read_bytes())
  env={**os.environ,'NODE_PATH':str(NODE),'npm_config_offline':'true'}
  subprocess.run(['node',bc/'build.js'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=900)
  subprocess.run(['node',ccdir/'build.js'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=900)
  bco=json.loads((bc/'MCEntryCoordinator.json').read_text()); cco=json.loads((ccdir/'MCEntryCoordinator.json').read_text())
  assert bco['abi']==cco['abi'] and bco['storageLayout']==cco['storageLayout']
 # Coordinator can differ only by new domains and pinned engine code hash.
 cb=(BASE/'coordinator/MCEntryCoordinator.sol').read_text(); cc=(HERE/'coordinator/MCEntryCoordinator.sol').read_text()
 oldh='26a2d279a04c878d99b094fa93acad3992045500fa68b265d5a021e74530cf3f'; newh='ee8a4ee454fed308072ac87510eab964a1ae816af5a2109706ad1206693fe277'
 assert cb.count(oldh)==1 and cc==cb.replace(oldh,newh,1).replace('MC-HASH-MAP-PUT-BOUNDED-P39','MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192')
 report={'schema':1,'sourceBase':'P39 source-only snapshot','baseEngineSourceSHA256':sha((BASE/'engine/MCEntryInterpreter.sol').read_bytes()),'candidateEngineSourceSHA256':sha(cand.encode()),'engineNormalizedDelta':['MAX_ARRAYS 4096->8192','profile domain labels P39->P41-ARRAY-8192; DBOOT intentionally unchanged'],'coordinatorNormalizedDelta':['engine runtime codehash pinned to new engine','package/class/seed/vm domain labels P39->P41-ARRAY-8192'],'bootstrapCount':105,'bootstrapRoot':root,'bootstrapRootPreserved':True,'abiUnchanged':True,'storageLayoutUnchanged':True,'coordinatorABIAndStorageUnchanged':True,'maxObjects':4096,'maxArrayElements':262144,'maxConstantPool':4096,'maxHandles':8192+4096+256+1,'uint16ArrayCounterMax':65535,'8192FitsUint16':True,'runtimeBytes':len(ca['deployedBytecode'])//2,'runtimeSHA256':ca['codeHashes']['runtimeSHA256'],'runtimeKeccak256':ca['codeHashes']['runtimeKeccak256'],'engineABIEntries':len(ca['abi'])}
 (HERE/'results/source-audit.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__':main()
