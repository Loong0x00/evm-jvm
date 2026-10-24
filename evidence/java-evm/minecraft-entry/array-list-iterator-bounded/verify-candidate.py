#!/usr/bin/env python3
"""Independent local source/artifact/run checks for the bounded iterator candidate."""
import hashlib, importlib.util, json, os, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = REPO / 'evidence/java-evm/minecraft-entry/array-list-iterator-source-base-p51'
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_text())

# Verify the user's exact source-only P51 provenance before any candidate claims.
manifest = load(BASE / 'source-manifest.json')
assert manifest['acceptedGuestCodeCommit'] == '9bf0cdfc61e539225c3b4a494a325b72cd58f98d'
assert manifest['worktreeBase'] == '2419d7de64f6b2f75b80e161a4464a83c18868fc'
assert len(manifest['files']) == 16
for name, pin in manifest['files'].items():
    raw = (BASE / name).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], name
source_record = load(ROOT / 'source-base-verification.json')
assert source_record['baseManifestSHA256'] == sha((BASE / 'source-manifest.json').read_bytes())
assert len(source_record['files']) == 16

spec = importlib.util.spec_from_file_location('array_list_iterator_root_helper', ROOT / 'root_helper.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
base_source = (BASE / 'engine/MCEntryInterpreter.sol').read_text()
source = (ROOT / 'engine/MCEntryInterpreter.sol').read_text()
old_leaves, leaves = helper.leaf_pairs(base_source), helper.leaf_pairs(source)
assert len(old_leaves) == 115 and len(leaves) == 116
assert [i for i, (x, y) in enumerate(zip(old_leaves, leaves)) if x != y] == [98]
assert leaves[:98] == old_leaves[:98] and leaves[99:115] == old_leaves[99:115]
assert re.search(r'new bytes32\[\]\(116\)', source)
assert re.search(r'h\[115\] = keccak256\(_bootstrapArrayListItr\(\)\);', source)
assert re.search(r'p\.classes\[classSlot \+ 71\]\.data = _bootstrapHashMapEntrySet\(\);', source)
assert re.search(r'p\.classes\[classSlot \+ 72\]\.data = _bootstrapHashMapEntryIterator\(\);', source)
assert re.search(r'p\.classes\[classSlot \+ 76\]\.data = _bootstrapArrayListItr\(\);', source)
assert re.search(r'uint256 count = inputCount \+ 109 \+', source)
assert 'bytes("java/util/ArrayList$Itr")' in source
for idx, fn in zip(range(105, 110), ('Function','NavigableMap','Comparator','SortedSet','NavigableSet')):
    assert re.search(rf'p\.classes\[count - {11-(idx-105)}\] = _parseBundleClass\(_bootstrap{fn}\(\)\);', source), (idx, fn)
assert not re.search(r'p\.classes\[count - 6\]\s*=', source)
# Slot 110 remains the EntrySet from classSlot+71; shifting the final tail must not overwrite it.
for domain in load(ROOT / 'pins.json')['engineProfileDomains']:
    assert domain in source
assert source.count('JVMEVM:MC-ARRAYLIST-ITERATOR-BOUNDED-1:') == 9
assert 'JVMEVM:MC-LIST-ITERATOR-LINK-1:' not in source

pins = load(ROOT / 'pins.json')
root = helper.root_record(source, pins['bootstrapDomain'], str(ROOT),
                          {**os.environ, 'NODE_PATH': str(REPO / 'jvmevm/runtime/node_modules')})
assert root['root'] == pins['bootstrapRoot'] and root['leaves'] == pins['orderedBootstrapLeaves']
array_bytes = bytes.fromhex((ROOT / 'ArrayList.class.hex').read_text().strip())
itr_bytes = (ROOT / 'build/repro-classes/java/util/ArrayList$Itr.class').read_bytes()
assert len(array_bytes) == pins['arrayListImage']['bytes'] and sha(array_bytes) == pins['arrayListImage']['sha256']
assert len(itr_bytes) == pins['helperImage']['bytes'] and sha(itr_bytes) == pins['helperImage']['sha256']
assert root['leaves'][98] == pins['arrayListImage']['keccak256']
assert root['leaves'][115] == pins['helperImage']['keccak256']

javap_list = (ROOT / 'build/ArrayList.javap.txt').read_text()
javap_itr = (ROOT / 'build/ArrayList-Itr.javap.txt').read_text()
assert re.search(r'private final java\.util\.ArrayList owner;', javap_itr)
assert re.search(r'private int cursor;', javap_itr)
assert 'ArrayList.access$000:(Ljava/util/ArrayList;)I' in javap_itr
assert 'ArrayList.access$100:(Ljava/util/ArrayList;)[Ljava/lang/Object;' in javap_itr
assert 'java/util/NoSuchElementException' in javap_itr and 'athrow' in javap_itr
assert re.search(r'public native void remove\(\);', javap_itr)
assert 'java/util/ArrayList.size:()I' not in javap_itr
assert 'public java.util.Iterator iterator();' in javap_list
assert 'java/util/ArrayList$Itr."<init>":(Ljava/util/ArrayList;)V' in javap_list
assert 'ArrayList$1' not in javap_itr
array_source = (ROOT / 'bootstrap/java/util/ArrayList.java').read_text()
base_array = (BASE / 'bootstrap/java/util/ArrayList.java').read_text()
int_ctor = re.compile(r'    public ArrayList\(int initialCapacity\) \{.*?\n    \}', re.S)
assert int_ctor.search(array_source).group() == int_ctor.search(base_array).group()
assert 'private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA' in array_source
assert 'public native boolean add(Object value);' in array_source

# Pinned artifact/coordinator relationship; exact current deployed runtime bytes, not initcode.
engine = load(ROOT / 'engine/MCEntryInterpreter.json')
coord = load(ROOT / 'coordinator/MCEntryCoordinator.json')
assert len(bytes.fromhex(engine['deployedBytecode'])) == pins['engine']['runtimeBytes']
assert sha(bytes.fromhex(engine['deployedBytecode'])) == pins['engine']['runtimeSHA256']
assert engine['codeHashes']['runtimeKeccak256'] == pins['engine']['runtimeKeccak256']
assert len(bytes.fromhex(coord['deployedBytecode'])) == pins['coordinator']['runtimeBytes']
assert sha(bytes.fromhex(coord['deployedBytecode'])) == pins['coordinator']['runtimeSHA256']
assert coord['codeHashes']['runtimeKeccak256'] == pins['coordinator']['runtimeKeccak256']
co_source = (ROOT / 'coordinator/MCEntryCoordinator.sol').read_text()
assert pins['coordinator']['engineCodeHash'] == pins['engine']['runtimeKeccak256']
assert re.search(r'ENGINE_CODEHASH = hex"' + pins['engine']['runtimeKeccak256'] + r'"', co_source)
for name, literal in pins['coordinatorDomains'].items():
    assert literal in co_source, name
assert pins['globalNativeBindings'] == 21 and pins['stringLocalBinding'] == 12
assert pins['rawClassCountLimit'] == 150 and pins['rawByteLimit'] == 1063930
assert pins['runtimeCapBytes'] == 1048576 and pins['limitsUnchanged']

# Fresh independent-process q1/q7/q128 generated fixture equivalence.
run = ROOT / 'runs/iterator-final-001'
qs = {}
for q in (1, 7, 128):
    d = load(run / f'q{q}/durable-head.json')
    world = load(run / 'reports' / f'q{q}/world-report.json')
    assert world['manifest']['stage'] == 'final-reopened'
    assert d['stage'] == 'final-reopened' and d['lifecycle'] == 2 and d['outcome'] == 2
    assert d['result'] == 0 and d['javaKind'] == 0
    qs[str(q)] = {k: d[k] for k in ('epoch','jvmSteps','internalSteps','machineRoot','vfsRoot','checkpointRoot','checkpointSHA256','lifecycle','outcome','result','javaKind')}
assert len({x['machineRoot'] for x in qs.values()}) == 1
assert len({x['vfsRoot'] for x in qs.values()}) == 1
assert {q: x['jvmSteps'] for q, x in qs.items()} == {'1':416,'7':416,'128':416}
assert len({x['checkpointSHA256'] for x in qs.values()}) == 3
refusals = {}
for op in ('add','get','to-array','equals','hash','clone'):
    x = load(ROOT / f'runs/iterator-refusal-final-001/reports/{op}/resume-refusal.json')
    assert x['selector'] == '0xd631c3a4' and x['rootUnchanged'] and x['durableHeadUnchanged']
    refusals[op] = {k:x[k] for k in ('selector','uint256Words','gas','rootUnchanged','durableHeadUnchanged')}
raw = load(ROOT / 'runs/iterator-refusal-final-001/reports/raw-helper/start-refusal.json')
assert raw['selector'] == '0x6a23ad80' and raw['rootUnchanged'] and raw['durableHeadUnchanged']

report = {
    'status':'source and historical worker receipts verified; independent parent proof recorded separately',
    'sourceBaseFilesVerified':16,
    'oldBootstrapImages':115,
    'newBootstrapImages':116,
    'changedExistingLeafIndexes':[98],
    'appendedHelperLeafIndex':115,
    'bootstrapRoot':root['root'],
    'engineRuntimeBytes':pins['engine']['runtimeBytes'],
    'engineRuntimeSHA256':pins['engine']['runtimeSHA256'],
    'engineRuntimeKeccak256':pins['engine']['runtimeKeccak256'],
    'coordinatorRuntimeBytes':pins['coordinator']['runtimeBytes'],
    'coordinatorRuntimeKeccak256':pins['coordinator']['runtimeKeccak256'],
    'generatedFixtureOnly':True,
    'originalMinecraftInputsInspected':False,
    'q1q7q128':qs,
    'unsupportedRefusals':refusals,
    'privateHelperRawReplacement':{k:raw[k] for k in ('selector','uint256Words','rootUnchanged','durableHeadUnchanged','gas')},
    'limitsUnchanged':True,
    'nonemptyIterationTested':False,
    'addOrMutationImplemented':False,
    'fullArrayListConformanceClaim':False,
}
(ROOT / 'runs/candidate-verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'bootstrapRoot':root['root'],'q1q7q128MachineRoot':qs['1']['machineRoot'],'jvmSteps':416,'refusals':list(refusals)+['raw-helper-replacement']},indent=2))
