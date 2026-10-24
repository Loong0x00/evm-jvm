#!/usr/bin/env python3
"""Recompute pins from the exact P53 source-only basis and this candidate."""
import hashlib, importlib.util, json, os, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/'source-base-p53'
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text())
base_manifest=load(BASE/'source-manifest.json')
assert base_manifest['acceptedGuestCodeCommit']=='52cc8e84594698c92d119eca158a094cd27ec2a4'
assert len(base_manifest['files'])==16
for rel,pin in base_manifest['files'].items():
 raw=(BASE/rel).read_bytes()
 assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],rel
spec=importlib.util.spec_from_file_location('array_list_typed_root_helper',ROOT/'root_helper.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
engine=(ROOT/'engine/MCEntryInterpreter.sol').read_text()
match=re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\);',engine)
assert match and match.group(1)=='JVMEVM:MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1:BOOTSTRAP:1'
root=helper.root_record(engine,match.group(1),str(ROOT),{**os.environ,'NODE_PATH':'/home/user/evm-jvm/array-list-to-array/jvmevm/runtime/node_modules'})
base_engine=(BASE/'engine/MCEntryInterpreter.sol').read_text()
base_domain=re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\);',base_engine).group(1)
base_root=helper.root_record(base_engine,base_domain,str(ROOT),{**os.environ,'NODE_PATH':'/home/user/evm-jvm/array-list-to-array/jvmevm/runtime/node_modules'})
diff=[i for i,(old,new) in enumerate(zip(base_root['leaves'],root['leaves'])) if old!=new]
assert len(root['leaves'])==len(base_root['leaves'])==117 and diff==[98],diff
image=bytes.fromhex((ROOT/'ArrayList.class.hex').read_text().strip())
assert len(image)>0 and image[:8]==bytes.fromhex('cafebabe00000034')
e=load(ROOT/'engine/MCEntryInterpreter.json'); c=load(ROOT/'coordinator/MCEntryCoordinator.json')
co_source=(ROOT/'coordinator/MCEntryCoordinator.sol').read_text()
assert engine.count('JVMEVM:MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1:')==9
assert all(co_source.count('MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1/'+x+'/v1')==1 for x in ('package','class','selected-resource','vm'))
pins={
 'profile':'MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1',
 'baseGuestCodeCommit':base_manifest['acceptedGuestCodeCommit'],
 'sourceBase':'source-base-p53',
 'sourceBaseManifestSHA256':sha((BASE/'source-manifest.json').read_bytes()),
 'verifiedSourceManifestFiles':16,
 'bootstrapCount':117,'changedBootstrapLeaves':diff,
 'bootstrapDomain':match.group(1),'bootstrapRoot':root['root'],'orderedBootstrapLeaves':root['leaves'],
 'arrayListImage':{'index':98,'name':'java/util/ArrayList','bytes':len(image),'sha256':sha(image),'keccak256':root['leaves'][98]},
 'engine':{'bytes':len(bytes.fromhex(e['deployedBytecode'])),'initBytes':len(bytes.fromhex(e['bytecode'])),'runtimeSHA256':e['codeHashes']['runtimeSHA256'],'runtimeKeccak256':e['codeHashes']['runtimeKeccak256'],'initSHA256':e['codeHashes']['initSHA256'],'sourceSHA256':e['sourceHashes']['MCEntryInterpreter.sol']},
 'coordinator':{'bytes':len(bytes.fromhex(c['deployedBytecode'])),'initBytes':len(bytes.fromhex(c['bytecode'])),'runtimeSHA256':c['codeHashes']['runtimeSHA256'],'runtimeKeccak256':c['codeHashes']['runtimeKeccak256'],'initSHA256':c['codeHashes']['initSHA256'],'sourceSHA256':c['sourceHashes']['MCEntryCoordinator.sol'],'engineCodeHash':e['codeHashes']['runtimeKeccak256']},
 'engineProfileDomains':[f'JVMEVM:MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1:{x}:1' for x in ('MAIN:EMPTY-STRING-ARRAY','ROOT','ARTIFACT','BOOTSTRAP','CONFIG','MACHINE','SEED','VFS','FILE')],
 'coordinatorDomains':[f'MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1/{x}/v1' for x in ('package','class','selected-resource','vm')],
 'globalNativeBindings':22,'stringLocalBinding':12,'rawClassCountLimit':150,'rawByteLimit':1063930,
 'limitsUnchanged':True,'allOldBootstrapImagesExceptArrayListExact':True,
 'nonemptyElementCopyBranchExecuted':False,'shortTargetRefusalBranchExecuted':False,
 'runtimeCapBytes':1048576,'checkpointCapBytes':2097152,'localGas':1000000000,'gasReserve':25000000,'quantumMax':65536,'internalPerCallMax':4096
}
(ROOT/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(ROOT/'source-base-verification.json').write_text(json.dumps({
 'status':'verified before implementation','acceptedGuestCodeCommit':base_manifest['acceptedGuestCodeCommit'],
 'sourceManifestSHA256':pins['sourceBaseManifestSHA256'],'verifiedFileCount':len(base_manifest['files']),
 'files':{k:{'bytes':v['bytes'],'sha256':v['sha256']} for k,v in base_manifest['files'].items()},
 'originalMinecraftInputsInspected':False,'parentReviewEvidenceInspected':False,'networkUsed':False
},indent=2)+'\n')
print(json.dumps({'sourceManifestFiles':16,'leafCount':117,'changedLeafIndexes':diff,'bootstrapRoot':root['root'],'arrayListBytes':len(image),'arrayListSHA256':sha(image),'engineBytes':pins['engine']['bytes'],'engineRuntimeSHA256':pins['engine']['runtimeSHA256'],'engineRuntimeKeccak256':pins['engine']['runtimeKeccak256'],'coordinatorBytes':pins['coordinator']['bytes']},indent=2))
