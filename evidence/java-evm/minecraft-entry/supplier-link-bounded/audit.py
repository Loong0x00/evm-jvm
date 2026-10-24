#!/usr/bin/env python3
"""Bounded source/pin audit for the generated Java 8 Supplier-link candidate."""
import hashlib, importlib.util, json, os, pathlib, re, struct, sys
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT.parent/'supplier-link-source-base-p60'
ENGINE=ROOT/'engine/MCEntryInterpreter.sol'
COORD=ROOT/'coordinator/MCEntryCoordinator.sol'
CLASS=ROOT/'java/classes/java/util/function/Supplier.class'

def sha(b): return hashlib.sha256(b).hexdigest()
def classfile(data):
    pos=0
    def u1():
        nonlocal pos; v=data[pos];pos+=1;return v
    def u2():
        nonlocal pos;v=int.from_bytes(data[pos:pos+2],'big');pos+=2;return v
    def u4():
        nonlocal pos;v=int.from_bytes(data[pos:pos+4],'big');pos+=4;return v
    assert u4()==0xcafebabe
    minor,major=u2(),u2();n=u2();cp=[None]*n;i=1
    while i<n:
        tag=u1()
        if tag==1:
            size=u2();v=data[pos:pos+size].decode('utf8');pos+=size;cp[i]=('Utf8',v)
        elif tag in (3,4): pos+=4
        elif tag in (5,6): pos+=8;i+=1
        elif tag in (7,8,16,19,20): cp[i]=(tag,u2())
        elif tag in (9,10,11,12,17,18): pos+=4
        elif tag==15: pos+=3
        else: raise AssertionError(('constant-pool-tag',tag))
        i+=1
    access=u2();this=u2();super_=u2();interfaces=[u2() for _ in range(u2())]
    fields=[]
    for _ in range(u2()):
        flags,name,desc=u2(),u2(),u2();attrs=[]
        for _ in range(u2()):
            an=cp[u2()][1];ln=u4();attrs.append((an,data[pos:pos+ln]));pos+=ln
        fields.append((flags,cp[name][1],cp[desc][1],attrs))
    methods=[]
    for _ in range(u2()):
        flags,name,desc=u2(),u2(),u2();attrs=[]
        for _ in range(u2()):
            an=cp[u2()][1];ln=u4();attrs.append((an,data[pos:pos+ln]));pos+=ln
        methods.append((flags,cp[name][1],cp[desc][1],attrs))
    attrs=[]
    for _ in range(u2()):
        an=cp[u2()][1];ln=u4();attrs.append((an,data[pos:pos+ln]));pos+=ln
    assert pos==len(data)
    return minor,major,access,cp,this,super_,interfaces,fields,methods,attrs

def expected_engine(base, supplier_hex):
    s=base.replace('MC-ARRAY-LIST-ADD-BOUNDED-1','MC-SUPPLIER-LINK-BOUNDED-1')
    changes=[
      ('bytes32[] memory h = new bytes32[](127);','bytes32[] memory h = new bytes32[](128);'),
      ('        h[126] = keccak256(_bootstrapLinkedHashMapEntryIterator());\n        return keccak256(abi.encode(DBOOT, h));','        h[126] = keccak256(_bootstrapLinkedHashMapEntryIterator());\n        // Supplier is one genuine Java 8 interface image appended after the exact P60 prefix.\n        h[127] = keccak256(_bootstrapSupplier());\n        return keccak256(abi.encode(DBOOT, h));'),
      ('|| _isNamedClass(users[i], bytes("java/util/LinkedHashMapEntryIterator"))) {','|| _isNamedClass(users[i], bytes("java/util/LinkedHashMapEntryIterator"))\n                || _isNamedClass(users[i], bytes("java/util/function/Supplier"))) {'),
      ('uint256 count = inputCount + 111 + (suppliedObject ? 0 : 1)','uint256 count = inputCount + 112 + (suppliedObject ? 0 : 1)'),
      ('p.classes[count - 22] = _parseBundleClass(_bootstrapFunction());','p.classes[count - 23] = _parseBundleClass(_bootstrapFunction());'),
      ('p.classes[count - 21] = _parseBundleClass(_bootstrapNavigableMap());','p.classes[count - 22] = _parseBundleClass(_bootstrapNavigableMap());'),
      ('p.classes[count - 20] = _parseBundleClass(_bootstrapComparator());','p.classes[count - 21] = _parseBundleClass(_bootstrapComparator());'),
      ('p.classes[count - 19] = _parseBundleClass(_bootstrapSortedSet());','p.classes[count - 20] = _parseBundleClass(_bootstrapSortedSet());'),
      ('p.classes[count - 18] = _parseBundleClass(_bootstrapNavigableSet());','p.classes[count - 19] = _parseBundleClass(_bootstrapNavigableSet());'),
      ('p.classes[count - 11] = _parseBundleClass(_bootstrapReflectArray());','p.classes[count - 12] = _parseBundleClass(_bootstrapReflectArray());'),
      ('p.classes[count - 10] = _parseBundleClass(_bootstrapCollections());','p.classes[count - 11] = _parseBundleClass(_bootstrapCollections());'),
      ('p.classes[count - 9] = _parseBundleClass(_bootstrapSingletonList());','p.classes[count - 10] = _parseBundleClass(_bootstrapSingletonList());'),
      ('p.classes[count - 8] = _parseBundleClass(_bootstrapSingletonIterator());','p.classes[count - 9] = _parseBundleClass(_bootstrapSingletonIterator());'),
      ('p.classes[count - 7] = _parseBundleClass(_bootstrapArrays());','p.classes[count - 8] = _parseBundleClass(_bootstrapArrays());'),
      ('p.classes[count - 6] = _parseBundleClass(_bootstrapArraysArrayList());','p.classes[count - 7] = _parseBundleClass(_bootstrapArraysArrayList());'),
      ('p.classes[count - 5] = _parseBundleClass(_bootstrapArraysArrayIterator());','p.classes[count - 6] = _parseBundleClass(_bootstrapArraysArrayIterator());'),
      ('        p.classes[classSlot + 87].data = _bootstrapLinkedHashMapEntryIterator();\n    }','        p.classes[classSlot + 87].data = _bootstrapLinkedHashMapEntryIterator();\n        // Supplier is image 128 and uses the next previously unassigned physical slot.\n        p.classes[classSlot + 88].data = _bootstrapSupplier();\n    }'),
      ('    function _bootstrapReflectiveOperationException() private pure returns (bytes memory) {','    function _bootstrapSupplier() private pure returns (bytes memory) { return hex"'+supplier_hex+'"; }\n\n    function _bootstrapReflectiveOperationException() private pure returns (bytes memory) {'),
    ]
    for old,new in changes:
        assert s.count(old)==1,('replacement-count',old[:80],s.count(old))
        s=s.replace(old,new)
    return s

manifest=json.loads((BASE/'source-manifest.json').read_text())
for name,expected in manifest['files'].items():
    b=(BASE/name).read_bytes();v=expected
    assert len(b)==v['bytes'] and sha(b)==v['sha256'],name
supplier=CLASS.read_bytes();minor,major,access,cp,this,super_,ifs,fields,methods,attrs=classfile(supplier)
assert (minor,major)==(0,52) and access==0x0601 and cp[this][0]==7 and cp[cp[this][1]][1]=='java/util/function/Supplier'
assert cp[cp[super_][1]][1]=='java/lang/Object' and ifs==[] and fields==[]
assert len(methods)==1
flags,name,desc,mattrs=methods[0]
assert (flags,name,desc)==(0x0401,'get','()Ljava/lang/Object;')
assert {n for n,_ in mattrs}=={'Signature'}
assert len(attrs)==1 and attrs[0][0]=='Signature'
assert supplier[0:4]==bytes.fromhex('cafebabe') and len(supplier)==195
hexsupplier=supplier.hex()
base_engine=(BASE/'engine/MCEntryInterpreter.sol').read_text()
assert ENGINE.read_text()==expected_engine(base_engine,hexsupplier),'engine delta escaped bounded Supplier link patch'
base_coord=(BASE/'coordinator/MCEntryCoordinator.sol').read_text()
coord=COORD.read_text()
base_engine_json=json.loads((BASE/'engine/MCEntryInterpreter.json').read_text())
engine_json=json.loads((ROOT/'engine/MCEntryInterpreter.json').read_text())
coord_json=json.loads((ROOT/'coordinator/MCEntryCoordinator.json').read_text())
expected_coord=base_coord.replace('MC-ARRAY-LIST-ADD-BOUNDED-1','MC-SUPPLIER-LINK-BOUNDED-1')
old_keccak='f16a96a46bec49a5c7fb00072571dbd60d07ca5bf3b1420a2ce551452d5ce369'
assert expected_coord.count(old_keccak)==1
expected_coord=expected_coord.replace(old_keccak,engine_json['codeHashes']['runtimeKeccak256'])
assert coord==expected_coord,'coordinator delta escaped fresh domains and engine hash pin'
assert engine_json['abi']==base_engine_json['abi']
assert engine_json['storageLayout']==base_engine_json['storageLayout']
base_coord_json=json.loads((BASE/'coordinator/MCEntryCoordinator.json').read_text())
assert coord_json['abi']==base_coord_json['abi'] and coord_json['storageLayout']==base_coord_json['storageLayout']
assert len(engine_json['deployedBytecode'])//2<=1048576
assert len(coord_json['deployedBytecode'])//2==5411
assert coord_json['codeHashes']['runtimeKeccak256']=='81d2f439c5dd7bcbead3dbfa2f08b9621617a3870aab4e24146cd2cad69bb6f4'
assert 'MC-SUPPLIER-LINK-BOUNDED-1' in ENGINE.read_text() and 'MC-ARRAY-LIST-ADD-BOUNDED-1' not in ENGINE.read_text()
# Candidate root is exactly the prior 127 leaves followed by one Supplier leaf.
pins=json.loads((BASE/'pins.json').read_text());record=json.loads((ROOT/'root-record.json').read_text())
assert pins['bootstrapCount']==127 and pins['bootstrapRoot']==pins['expectedBootstrapRoot']
assert len(record['leaves'])==128 and record['leaves'][:127]==pins['orderedBootstrapLeaves']
assert record['root']=='cc8f91923d7ea181f19178b2f8d4e08bf7af5337fc58ebe4cc5cbaddf017f593'
assert record['leaves'][127]=='80f004e245a068059e13a541d1f659069f27e6d8f09428499b6972fcc334ea85'
# Index/count corrections are deliberately complete and preserve old absolute staging slots.
source=ENGINE.read_text()
for before,after in ((22,23),(21,22),(20,21),(19,20),(18,19),(11,12),(10,11),(9,10),(8,9),(7,8),(6,7),(5,6)):
    assert f'count - {after}' in source
assert 'p.classes[classSlot + 84].data = _bootstrapEnumMap();' in source
assert 'p.classes[classSlot + 85].data = _bootstrapLinkedHashMapEntry();' in source
assert 'p.classes[classSlot + 86].data = _bootstrapLinkedHashMapEntrySet();' in source
assert 'p.classes[classSlot + 87].data = _bootstrapLinkedHashMapEntryIterator();' in source
assert 'p.classes[classSlot + 88].data = _bootstrapSupplier();' in source
# Raw cap, internal/array/checkpoint caps and ABI are unchanged from authoritative P60.
for needle in ('MAX_RAW_CLASSES = 150','MAX_RAW_BYTES = 1063930','MAX_ARRAYS = 8192','MAX_ARRAY_LENGTH = 65536','MAX_ARRAY_ELEMENTS = 262144','MAX_OBJECTS = 4096','MAX_CHECKPOINT_BYTES = 2097152','MAX_FRAMES = 128'):
    assert needle in source,needle
assert len(re.findall(r'function _bootstrapSupplier\(',source))==1
print('Supplier classfile/source/slot/root/ABI/storage/domain/pin audit PASS')
print('classBytes=195 classSHA256='+sha(supplier))
print('bootstrapRoot='+record['root']+' newLeaf='+record['leaves'][127])
print('engineRuntimeBytes='+str(len(engine_json['deployedBytecode'])//2)+' engineKeccak='+engine_json['codeHashes']['runtimeKeccak256'])
print('coordinatorRuntimeBytes='+str(len(coord_json['deployedBytecode'])//2)+' coordinatorKeccak='+coord_json['codeHashes']['runtimeKeccak256'])
