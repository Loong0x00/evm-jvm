#!/usr/bin/env python3
"""Rebuild deterministic source/artifact manifests and pinned profile facts."""
import hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT.parent/'arrays-as-list-source-base-p55'
sha=lambda b:hashlib.sha256(b).hexdigest()
base_manifest=json.loads((BASE/'source-manifest.json').read_text())
for rel,pin in base_manifest['files'].items():
    b=(BASE/rel).read_bytes();assert len(b)==pin['bytes'] and sha(b)==pin['sha256'],rel
(ROOT/'build/pins/source-base-verification.json').write_text(json.dumps({
 'verifiedFirst':True,'verifiedCount':len(base_manifest['files']),
 'baseWorktreeCommit':base_manifest['worktreeBase'],
 'acceptedGuestCodeCommit':base_manifest['acceptedGuestCodeCommit'],
 'files':base_manifest['files']},indent=2)+'\n')
engine=json.loads((ROOT/'engine/MCEntryInterpreter.json').read_text())
coord=json.loads((ROOT/'coordinator/MCEntryCoordinator.json').read_text())
old_engine=json.loads((BASE/'engine/MCEntryInterpreter.json').read_text())
old_coord=json.loads((BASE/'coordinator/MCEntryCoordinator.json').read_text())
assert engine['abi']==old_engine['abi'] and engine['storageLayout']==old_engine['storageLayout']
assert coord['abi']==old_coord['abi'] and coord['storageLayout']==old_coord['storageLayout']
root_record=json.loads((ROOT/'build/pins/bootstrap-root.json').read_text())
source_entries={}
paths=['engine/MCEntryInterpreter.sol','engine/MCEntryInterpreter.json','engine/MCEntryInterpreter.abi.json',
       'engine/MCEntryInterpreter.init.hex','engine/MCEntryInterpreter.runtime.hex','engine/build.js',
       'coordinator/MCEntryCoordinator.sol','coordinator/MCEntryCoordinator.json','coordinator/MCEntryCoordinator.abi.json',
       'coordinator/MCEntryCoordinator.init.hex','coordinator/MCEntryCoordinator.runtime.hex','coordinator/build.js',
       'canonical-driver.go.txt','root_helper.py','source_audit.py','make_pins.py']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'bootstrap/java/util').glob('*.java'))]
paths += [f'build/classes-v3/java/util/{n}.class' for n in ('Arrays','Arrays$ArrayList','Arrays$ArrayIterator')]
paths += ['README.md','rebuild_java_images.sh','rebuild_test_fixtures.py','summarize_evidence.py']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').rglob('*.java'))]
paths += ['build/arrays-as-list-fixture-v4.zip','build/arrays-as-list-single-fixture-v4.zip']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'build/refusals').rglob('*.zip'))]
paths += ['build/pins/new-images-javap-v3.txt','build/results/arrays-as-list-summary.json']
for rel in paths:
    b=(ROOT/rel).read_bytes();source_entries[rel]={'bytes':len(b),'sha256':sha(b)}
images=[]
for i,name in enumerate(('Arrays','Arrays$ArrayList','Arrays$ArrayIterator'),120):
    b=(ROOT/f'build/classes-v3/java/util/{name}.class').read_bytes()
    images.append({'index':i,'name':'java/util/'+name,'bytes':len(b),'sha256':sha(b),
                   'keccak256':__import__('subprocess').run(['node','-e',"const {keccak256:k}=require('js-sha3');console.log(k(Buffer.from(process.argv[1],'hex')))",b.hex()],cwd=ROOT,env={**os.environ,'NODE_PATH':'/home/user/evm-jvm/arrays-as-list/jvmevm/runtime/node_modules'},capture_output=True,text=True,check=True).stdout.strip()})
try:
    import root_helper
    calculated=root_helper.root_record((ROOT/'engine/MCEntryInterpreter.sol').read_text(),root_record['domain'],str(ROOT),{**os.environ,'NODE_PATH':'/home/user/evm-jvm/arrays-as-list/jvmevm/runtime/node_modules'})
    assert calculated['root']==root_record['root'] and calculated['leaves']==root_record['orderedLeaves']
except ImportError:
    sys.path.insert(0,str(ROOT));import root_helper
    calculated=root_helper.root_record((ROOT/'engine/MCEntryInterpreter.sol').read_text(),root_record['domain'],str(ROOT),{**os.environ,'NODE_PATH':'/home/user/evm-jvm/arrays-as-list/jvmevm/runtime/node_modules'})
    assert calculated['root']==root_record['root'] and calculated['leaves']==root_record['orderedLeaves']
manifest={'profile':'MC-ARRAYS-AS-LIST-BOUNDED-1','baseCommit':base_manifest['worktreeBase'],
 'acceptedGuestCodeCommit':base_manifest['acceptedGuestCodeCommit'],'verifiedSourceBaseFiles':len(base_manifest['files']),
 'files':source_entries}
(ROOT/'build/pins/candidate-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
pins={'profile':'MC-ARRAYS-AS-LIST-BOUNDED-1','basis':'P55 source-only prefix; measured genuine Arrays.asList(Object[]) fixed-size, live array-backed traversal',
 'baseCommit':base_manifest['worktreeBase'],'acceptedGuestCodeCommit':base_manifest['acceptedGuestCodeCommit'],
 'engine':{'initBytes':len(bytes.fromhex(engine['bytecode'])),'runtimeBytes':len(bytes.fromhex(engine['deployedBytecode'])),**engine['codeHashes'],'sourceSHA256':engine['sourceHashes']['MCEntryInterpreter.sol']},
 'coordinator':{'initBytes':len(bytes.fromhex(coord['bytecode'])),'runtimeBytes':len(bytes.fromhex(coord['deployedBytecode'])),**coord['codeHashes'],'sourceSHA256':coord['sourceHashes']['MCEntryCoordinator.sol']},
 'bootstrapCount':123,'bootstrapRoot':root_record['root'],'orderedBootstrapLeaves':root_record['orderedLeaves'],
 'newImages':images,'rawLimits':{'classes':150,'bytes':1063930},
 'runtimeLimits':{'arrays':8192,'arrayElements':262144,'arrayLength':65536,'objects':4096,'handles':12288,'constantPoolBytes':2097152,'runtimeBytes':1048576,'frames':128,'quantum':65536,'internalPerSlice':4096,'gasReserve':25000000},
 'localTestBudget':{'ordinaryGas':1000000000,'perCallWatchdogSeconds':30,'outerWatchdogSeconds':1200},
 'nativeBindings':{'global':22,'stringLocal':12},
 'abiAndStorageLayoutByteIdenticalToP55':True,
 'sourceBaseManifestSHA256':sha((BASE/'source-manifest.json').read_bytes()),'sourceFiles':source_entries}
(ROOT/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'engine':pins['engine'],'coordinator':pins['coordinator'],'bootstrapRoot':pins['bootstrapRoot'],'images':images},indent=2))
