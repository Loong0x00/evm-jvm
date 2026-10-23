import hashlib, importlib.util, json, os, pathlib, subprocess
R=pathlib.Path(__file__).resolve().parent
REPO=R.parents[3]
base=json.loads((R/'source-base/source-manifest.json').read_text())
source={}
for rel,spec in base['files'].items():
 b=(R/'source-base'/rel).read_bytes(); got=hashlib.sha256(b).hexdigest()
 assert len(b)==spec['bytes'] and got==spec['sha256'], rel
 source[rel]={'bytes':len(b),'sha256':got}
# Recompute append-only bootstrap root and require exact prior prefix.
spec=importlib.util.spec_from_file_location('roothelper',R/'root_helper.py');rh=importlib.util.module_from_spec(spec);spec.loader.exec_module(rh)
domain='JVMEVM:MC-LIST-ITERATOR-LINK-1:BOOTSTRAP:1'
record=rh.root_record((R/'engine.sol').read_text(),domain,str(REPO),os.environ)
assert len(record['leaves'])==115
pins0=json.loads((R/'source-base/pins.json').read_text())
assert record['leaves'][:114]==pins0['orderedBootstrapLeaves']
assert (R/'ListIterator.class').read_bytes()==bytes.fromhex(''.join((R/'engine.sol').read_text().split('_bootstrapListIterator() private pure returns (bytes memory) { return hex"',1)[1].split('"',1)[0].split()))
# Candidate source / generated input file pin set.
paths=['README.md','engine.sol','engine/MCEntryInterpreter.sol','engine/MCEntryInterpreter.json','engine/MCEntryInterpreter.abi.json','engine/MCEntryInterpreter.init.hex','engine/MCEntryInterpreter.runtime.hex','engine/build.js','coordinator/MCEntryCoordinator.sol','coordinator/MCEntryCoordinator.json','coordinator/MCEntryCoordinator.abi.json','coordinator/MCEntryCoordinator.init.hex','coordinator/MCEntryCoordinator.runtime.hex','coordinator/build.js','bootstrap/java/util/ListIterator.java','compiler-support/java/lang/Object.java','compiler-support/java/lang/Throwable.java','compiler-support/java/util/Iterator.java','build-bootstrap.sh','build-java-fixtures.sh','root_helper.py','write-manifests.py','tests/gate.go','tests/src/LinkCheck.java','tests/src/ApiCalls.java']
files={}
for rel in paths:
 b=(R/rel).read_bytes();files[rel]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
classes=['ListIterator.class']+[str(p.relative_to(R)) for p in sorted((R/'tests/raw150-classes').glob('*.class'))]
for rel in classes:
 b=(R/rel).read_bytes();files[rel]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
for sub in ['tests/classes','tests/api-classes']:
 for p in sorted((R/sub).glob('*.class')):
  rel=str(p.relative_to(R));b=p.read_bytes();files[rel]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
eng=json.loads((R/'engine/MCEntryInterpreter.json').read_text());co=json.loads((R/'coordinator/MCEntryCoordinator.json').read_text())
coordbase=pins0['coordinator'];assert co['codeHashes']['runtimeSHA256']==coordbase['runtimeSHA256'];assert co['codeHashes']['runtimeKeccak256']==coordbase['runtimeKeccak256']
# ABI and non-target limit invariants.
baseabi=json.loads((R/'source-base/engine/MCEntryInterpreter.json').read_text())['abi']
assert eng['abi']==baseabi
sol=(R/'engine.sol').read_text();old=(R/'source-base/engine/MCEntryInterpreter.sol').read_text()
for token in ['MAX_RAW_CLASSES = 150','MAX_RAW_BYTES = 1063930','MAX_CHECKPOINT_BYTES = 2097152','COMMIT_RESERVE = 25_000_000','MAX_FRAMES = 128']:
 assert token in sol and token in old,token
pins={
 'profile':'MC-LIST-ITERATOR-LINK-BOUNDED-1-candidate-unaccepted',
 'baseCommit':'a71d393cec807e9a8c5d612f9fb0283a8f47560e',
 'acceptedGuestCodeCommit':'f205c7776b5c491665c5b4e59e39b3c6f56dd6bc',
 'verifiedSourceOnlyManifest9':source,
 'domains':{'artifact':'JVMEVM:MC-LIST-ITERATOR-LINK-1:ARTIFACT:1','bootstrap':domain},
 'engine':{'initBytes':len(eng['bytecode'])//2,'runtimeBytes':len(eng['deployedBytecode'])//2,**eng['codeHashes'],'sourceSHA256':eng['sourceHashes']['MCEntryInterpreter.sol']},
 'coordinator':{'initBytes':len(co['bytecode'])//2,'runtimeBytes':len(co['deployedBytecode'])//2,**co['codeHashes'],'sourceSHA256':co['sourceHashes']['MCEntryCoordinator.sol'],'sourceUnchangedFromP50':True},
 'bootstrapCount':115,'baseBootstrapCount':114,'oldLeavesByteAndOrderPinned':True,'newLeaf':{'index':114,'class':'java/util/ListIterator','classBytes':len((R/'ListIterator.class').read_bytes()),'sha256':hashlib.sha256((R/'ListIterator.class').read_bytes()).hexdigest(),'keccak256':record['leaves'][114]},
 'bootstrapRoot':record['root'],'orderedBootstrapLeaves':record['leaves'],
 'highRawGate':{'rawClasses':150,'rawBytes':sum((R/'tests/raw150-classes').glob('*.class'),start=0) if False else sum(p.stat().st_size for p in (R/'tests/raw150-classes').glob('*.class')),'ListIteratorActualClassIndex':264,'typedArrayMetadata':hex(0x100+264),'actualEVMTest':'raw150/high-index-typed-array-clone'},
 'bounds':{'rawClasses':150,'rawBytes':1063930,'runtimeBytes':1048576,'perCallGas':1000000000,'perCallWatchdogSeconds':30,'commitReserve':25000000,'frames':128,'rawOrInternalIndexWidthsChanged':False},
 'ABIUnchanged':True,'nativeBindingsUnchanged':21,'stringLocalBindingUnchanged':12,
 'verifiedInputFiles':files,
 'verificationLimitations':['no durable separate-process reopen','no coordinator session execution','awaiting independent parent review','not original Minecraft execution']
}
(R/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
# Candidate-source hash manifest, with pinned supplied source-only manifest nested above.
manifest={'profile':pins['profile'],'sourceBaseManifestSHA256':hashlib.sha256((R/'source-base/source-manifest.json').read_bytes()).hexdigest(),'files':files}
(R/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'newBootstrapRoot':record['root'],'newLeaf':record['leaves'][114],'sourceFileCount':len(files),'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
