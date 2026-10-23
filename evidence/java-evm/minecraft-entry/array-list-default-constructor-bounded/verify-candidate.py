#!/usr/bin/env python3
"""Read-only checks for this bounded candidate and its allowed P49 source base."""
import hashlib, importlib.util, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = REPO / 'evidence/java-evm/minecraft-entry/array-list-default-source-base-p49'

def sha(b): return hashlib.sha256(b).hexdigest()

def load(path): return json.loads(path.read_text())

manifest = load(BASE / 'source-manifest.json')
assert manifest['acceptedBaseCommit'] == '451c7619135e8d38d87ed74fbadba650603f9b6a'
assert len(manifest['files']) == 12
for name, pin in manifest['files'].items():
    raw = (BASE / name).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], name

pins = load(ROOT / 'pins.json')
engine_base = load(BASE / 'engine/MCEntryInterpreter.json')
engine = load(ROOT / 'engine/MCEntryInterpreter.json')
coord_base = load(BASE / 'coordinator/MCEntryCoordinator.json')
coord = load(ROOT / 'coordinator/MCEntryCoordinator.json')
assert engine['abi'] == engine_base['abi']
assert engine['storageLayout'] == engine_base['storageLayout']
assert coord['abi'] == coord_base['abi']
assert coord['storageLayout'] == coord_base['storageLayout']
for prefix, art in (('engine', engine), ('coordinator', coord)):
    runtime = bytes.fromhex(art['deployedBytecode'])
    init = bytes.fromhex(art['bytecode'])
    p = pins[prefix]
    assert len(runtime) == p['runtimeBytes']
    assert len(init) == p['initBytes']
    assert sha(runtime) == p['runtimeSHA256'] == art['codeHashes']['runtimeSHA256']
    assert art['codeHashes']['runtimeKeccak256'] == p['runtimeKeccak256']
    assert sha(init) == p['initSHA256'] == art['codeHashes']['initSHA256']
assert len(bytes.fromhex(engine['deployedBytecode'])) <= pins['runtimeCap']
assert engine['codeHashes']['runtimeKeccak256'] in (ROOT/'coordinator/MCEntryCoordinator.sol').read_text()

spec = importlib.util.spec_from_file_location('arraylist_root_helper', ROOT/'root_helper.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
base_source = (BASE/'engine/MCEntryInterpreter.sol').read_text()
candidate_source = (ROOT/'engine/MCEntryInterpreter.sol').read_text()
base_pairs = helper.leaf_pairs(base_source)
candidate_pairs = helper.leaf_pairs(candidate_source)
root_record = helper.root_record(candidate_source, pins['domains']['bootstrap'], str(ROOT), {**os.environ, 'NODE_PATH': str(REPO/'jvmevm/runtime/node_modules')})
assert len(base_pairs) == len(candidate_pairs) == pins['bootstrapCount'] == 114
assert [i for i,(a,b) in enumerate(zip(base_pairs,candidate_pairs)) if a != b] == [98]
assert re.search(r'bytes32 private constant DBOOT = keccak256\("JVMEVM:MC-ARRAYLIST-DEFAULT-CONSTRUCTOR-P50:BOOTSTRAP:1"\);', candidate_source)
assert pins['bootstrapRoot'] == pins['expectedBootstrapRoot'] == root_record['root']
assert pins['bootstrapRoot'] == load(ROOT/'bootstrap-root.json')['root']
assert pins['replacedImage']['keccak256'] == root_record['leaves'][98]
assert load(ROOT/'bootstrap-root.json')['domain'] == pins['domains']['bootstrap']
assert re.search(r'p\.classes\[classSlot \+ 59\]\.data = _bootstrapArrayList\(\);', candidate_source)
assert re.search(r'uint256 private constant MAX_RAW_CLASSES = 150;', candidate_source)
assert re.search(r'uint256 private constant MAX_RAW_BYTES = 1063930;', candidate_source)
assert re.search(r'uint256 private constant MAX_CHECKPOINT_BYTES = 2097152;', candidate_source)
assert pins['globalNativeBindings'] == 21 and pins['stringLocalBinding'] == 12
assert pins['rawLimits'] == [150,1063930] and pins['runtimeCap'] == 1048576

array_source = (ROOT/'bootstrap/java/util/ArrayList.java').read_text()
base_array_source = (BASE/'bootstrap/java/util/ArrayList.java').read_text()
int_ctor = re.compile(r'    public ArrayList\(int initialCapacity\) \{.*?\n    \}', re.S)
assert int_ctor.search(array_source).group(0) == int_ctor.search(base_array_source).group(0)
class_hex = bytes.fromhex((ROOT/'ArrayList.class.hex').read_text().strip())
assert class_hex[:8] == bytes.fromhex('cafebabe00000034')
assert len(class_hex) == pins['replacedImage']['bytes']
assert sha(class_hex) == pins['replacedImage']['sha256']
assert pins['replacedImage']['keccak256'] == load(ROOT/'bootstrap-root.json')['orderedLeaves'][98]
assert re.search(r'private static final java\.lang\.Object\[\] DEFAULTCAPACITY_EMPTY_ELEMENTDATA;', (ROOT/'build/repro-javap.txt').read_text())

report = load(ROOT/'runs/candidate-gates-006-verification-report.json')
assert report['runId'] == 'candidate-gates-006'
assert report['equivalence']['machineRootEqualAcrossQ1Q7Q128']
assert report['equivalence']['vfsRootEqualAcrossQ1Q7Q128']
assert report['intNegativeCaught'] and len(report['unsupportedRawRefusals']) == 7
assert report['intOnlyFirstUse']['firstUseExecutesOrdinaryClassClinit']
assert report['intOnlyFirstUse']['jvmSteps'] == 84
assert report['intOnlyFirstUse']['maxSingleEvmCallGas'] < 1_000_000_000
assert report['rawArrayListReplacement']['rootUnchanged'] and report['rawArrayListReplacement']['durableHeadUnchanged']
print(json.dumps({'baseManifestFiles':len(manifest['files']),'bootstrapCount':len(candidate_pairs),'changedLeafIndexes':[98],'runtimeBytes':pins['engine']['runtimeBytes'],'engineRuntimeKeccak256':pins['engine']['runtimeKeccak256'],'coordinatorRuntimeBytes':pins['coordinator']['runtimeBytes'],'bootstrapRoot':pins['bootstrapRoot'],'runId':report['runId'],'status':'source verified; parent acceptance recorded separately'},indent=2))
