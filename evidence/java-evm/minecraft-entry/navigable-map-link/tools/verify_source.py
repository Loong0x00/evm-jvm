#!/usr/bin/env python3
"""Source/image and commitment audit against the exact frozen P43 baseline."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, subprocess, sys
root=Path(__file__).resolve().parents[5]
out=Path(__file__).resolve().parents[1]
base=root/'evidence/java-evm/minecraft-entry/navigable-map-source-base-p43'
engine=out/'engine/MCEntryInterpreter.sol'; old=(base/'engine/MCEntryInterpreter.sol').read_text(); new=engine.read_text()
source_manifest=json.loads((base/'source-manifest.json').read_text())
for name,row in source_manifest['files'].items():
 b=(base/name).read_bytes(); assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],name
spec=importlib.util.spec_from_file_location('root_helper',out/'tools/root_helper.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
old_pairs=mod.leaf_pairs(old); new_pairs=mod.leaf_pairs(new)
assert len(old_pairs)==106 and len(new_pairs)==107
assert old_pairs==new_pairs[:106], 'one of the old 106 bootstrap leaves/order changed'
assert 'uint256[] memory h = new uint256[](107);' not in new
assert 'bytes32[] memory h = new bytes32[](107);' in new
assert 'p.classes[count - 2] = _parseBundleClass(_bootstrapFunction());' in new
assert 'p.classes[count - 1] = _parseBundleClass(_bootstrapNavigableMap());' in new
assert 'inputCount + 100 +' in new
assert '|| _isNamedClass(users[i], bytes("java/util/NavigableMap")))' in new
assert '_isNamedClass(c, bytes("java/util/NavigableMap"));' in new
cf=out/'generatedfixtures/java/util/NavigableMap.class'; data=cf.read_bytes()
assert data[:4]==bytes.fromhex('cafebabe') and data[4:8]==bytes.fromhex('00000034')
assert hashlib.sha256(data).hexdigest()=='44efe011ca8062c1bb5bb1e8519bb0ab9fe7eb76c1133b7eea678609055d14e1'
assert data.hex() in new
assert new_pairs[106]==['image',data.hex()]
# Coherent source-domain/code-auth pin audit.
coord=(out/'coordinator/MCEntryCoordinator.sol').read_text(); art=json.loads((out/'engine/MCEntryInterpreter.json').read_text()); coart=json.loads((out/'coordinator/MCEntryCoordinator.json').read_text())
base_engine_art=json.loads((base/'engine/MCEntryInterpreter.json').read_text()); base_coord_art=json.loads((base/'coordinator/MCEntryCoordinator.json').read_text())
assert art['abi']==base_engine_art['abi'] and coart['abi']==base_coord_art['abi'], 'ABI changed'
assert art['codeHashes']['runtimeSHA256']=='990d44aa156e1392379494311d27326efe19ed886cb659c596ede35046306cae'
assert art['codeHashes']['runtimeKeccak256']=='c6d83a5101673e785ccb03e191d522743c3f401b6b0fb43a52d1b421bdec6065'
assert 'ENGINE_CODEHASH = hex"c6d83a5101673e785ccb03e191d522743c3f401b6b0fb43a52d1b421bdec6065"' in coord
assert coart['codeHashes']['runtimeKeccak256']=='fec02a9b7446aa43bcad5e7f47f9750e9d557a5d3950d587722d35d781da04d1'
assert 'P44-NAVIGABLE-MAP' in coord
# Actual raw binding count is deliberately not the derived class count.
assert 'uint8 public classCount;' in coord and 'n > 150' in coord
# Link widths: class IDs remain uint256 in execution frames/heap arrays and 16-bit on checkpoint wire.
assert 'uint256 classIndex;' in new and 'uint256[] heapClasses' not in new
assert 'new uint256[][](p.classes.length)' in new
assert 'at = _put(out, at, p.classes.length, 2);' in new
assert 'at = _put(out, at, f.classIndex, 2);' in new
# only method/opcode and constant-pool fields should narrow to byte; no class-ID cast found.
for bad in ('uint8(f.classIndex)','uint8(classIndex)','uint8(ci)','uint8(targetClass)','uint8(p.classes.length)'):
 assert bad not in new,bad
script=out/'tools/root_helper.py'; os.environ['NODE_PATH']='/home/user/evm-jvm/navigable-map-link/jvmevm/runtime/node_modules'
rec=mod.root_record(new,'JVMEVM:MC-HASH-MAP-PUT-P44-NAVIGABLE-MAP:BOOTSTRAP:1',str(root),os.environ)
(out/'results/root-commitment.json').write_text(json.dumps({'imageCount':len(new_pairs),'previousImageCount':len(old_pairs),'oldPrefixIdentical':True,'navigableMapLeafIndex':106,'navigableMapImageBytes':len(data),'navigableMapImageSHA256':hashlib.sha256(data).hexdigest(),'bootstrapRoot':rec['root'],'leaves':rec['leaves'],'engineRuntimeSHA256':art['codeHashes']['runtimeSHA256'],'engineRuntimeKeccak256':art['codeHashes']['runtimeKeccak256'],'coordinatorRuntimeKeccak256':coart['codeHashes']['runtimeKeccak256']},indent=2)+'\n')
print(json.dumps({'oldBootstrapPrefixIdentical':True,'oldImages':len(old_pairs),'newImages':len(new_pairs),'newLeafIndex':106,'classfileBytes':len(data),'classfileSHA256':hashlib.sha256(data).hexdigest(),'bootstrapRoot':rec['root'],'runtimeSHA256':art['codeHashes']['runtimeSHA256'],'runtimeKeccak256':art['codeHashes']['runtimeKeccak256'],'coordinatorKeccak256':coart['codeHashes']['runtimeKeccak256']},indent=2))
