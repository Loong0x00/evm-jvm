#!/usr/bin/env python3
"""Strict source-only guard for the bounded CopyOnWriteArrayList append."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile

here=Path(__file__).resolve().parent
stage=here.parent
root=here.parents[4]
prior=root/'evidence/java-evm/minecraft-entry/class-new-instance-preflight'
pins=json.loads((stage/'pins.json').read_text())
engine=(stage/'engine/MCEntryInterpreter.sol').read_text()
coord=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
old_engine=(prior/'engine/MCEntryInterpreter.sol').read_text()
old_coord=(prior/'coordinator/MCEntryCoordinator.sol').read_text()
new_domain='MC-COPY-ON-WRITE-ARRAY-LIST-PREFLIGHT1'
old_domain='MC-CLASS-NEW-INSTANCE-PREFLIGHT1'
new_images=('List','RandomAccess','CopyOnWriteArrayList','CopyOnWriteArrayListIterator')

assert pins['profile']==new_domain
assert pins['rawLimits']==[25,262144] and pins['bootstrapCount']==75
assert pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10
assert pins['exceptionKinds']==14 and pins['maxFrames']==128
assert pins['runtimeCap']==393216 and pins['checkpointCap']==1048576 and pins['headCap']==32768
assert 'MAX_RAW_CLASSES = 25' in engine and 'MAX_RAW_BYTES = 262144;' in engine
assert 'new bytes32[](75)' in engine and 'new uint256[](14)' in engine
assert engine.count(new_domain)==9 and coord.count(new_domain)==3
assert pins['address'][2:] in coord and pins['engine']['runtimeKeccak256'] in coord
assert 'return 11;' in engine and 'bytes("newInstance")' in engine
assert 'uint256 count = inputCount + 69 +' in engine
for name in new_images:
    assert f'_bootstrap{name}()' in engine
for name in ('java/util/List','java/util/RandomAccess','java/util/concurrent/CopyOnWriteArrayList','java/util/concurrent/CopyOnWriteArrayListIterator'):
    assert f'bytes("{name}")' in engine

# Rebuild all dependent Java 8 subset sources against a bootclasspath from which every
# replacement is absent. Existing inputs must remain exactly byte-identical.
with tempfile.TemporaryDirectory(dir=root/'build') as td:
    td=Path(td); api=td/'rt.jar'; out=td/'classes'; out.mkdir()
    shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
    stripped=[
        'java/lang/'+x+'.class' for x in ('String','System','Class','Number','NumberFormatException','Integer')
    ] + [
        'java/util/'+x+'.class' for x in ('Iterator','Collection','AbstractCollection','NoSuchElementException','List','RandomAccess')
    ] + [
        'java/util/concurrent/CopyOnWriteArrayList.class',
        'java/util/concurrent/CopyOnWriteArrayList$COWIterator.class',
    ]
    subprocess.run(['zip','-q','-d',api,*stripped],check=True)
    src=sorted(stage.glob('bootstrap/java/lang/*.java')) + sorted(stage.glob('bootstrap/java/util/*.java')) + sorted(stage.glob('bootstrap/java/util/concurrent/*.java'))
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out,*src],check=True)
    classes={
        'String':'java/lang/String.class','System':'java/lang/System.class','Class':'java/lang/Class.class',
        'Number':'java/lang/Number.class','NumberFormatException':'java/lang/NumberFormatException.class','Integer':'java/lang/Integer.class',
        'Iterator':'java/util/Iterator.class','Collection':'java/util/Collection.class','AbstractCollection':'java/util/AbstractCollection.class','NoSuchElementException':'java/util/NoSuchElementException.class',
        'List':'java/util/List.class','RandomAccess':'java/util/RandomAccess.class',
        'CopyOnWriteArrayList':'java/util/concurrent/CopyOnWriteArrayList.class',
        'CopyOnWriteArrayListIterator':'java/util/concurrent/CopyOnWriteArrayListIterator.class',
    }
    rebuilt={name:(out/path).read_bytes() for name,path in classes.items()}
    assert {name:hashlib.sha256(data).hexdigest() for name,data in rebuilt.items()}==pins['bootstrapSHA256']

# All 71 accepted byte images stay literal-identical. The only new immutable images
# are the four append-only entries above.
def image_map(source):
    return {m.group(1):m.group(2) for m in re.finditer(r'function (_bootstrap\w+)\([^)]*\).*?hex"([0-9a-f]+)"',source,re.S)}
old_images=image_map(old_engine); new_engine_images=image_map(engine)
assert len(old_images)==71 and len(new_engine_images)==75
for name,hexdata in old_images.items(): assert new_engine_images[name]==hexdata,name
for name in new_images:
    assert bytes.fromhex(new_engine_images['_bootstrap'+name])==rebuilt[name],name

# Reverse the narrowly permitted append/domain changes and require the exact accepted
# source. This rejects hidden semantic edits, altered historical images or reordering.
added_root='''        // Copy-on-write subset appends only after the complete 71-image tail.
        h[71] = keccak256(_bootstrapList());
        h[72] = keccak256(_bootstrapRandomAccess());
        h[73] = keccak256(_bootstrapCopyOnWriteArrayList());
        h[74] = keccak256(_bootstrapCopyOnWriteArrayListIterator());
'''
added_prepare='''        // Four immutable copy-on-write subset images append after the full 71-image tail.
        p.classes[classSlot + 32].data = _bootstrapList();
        p.classes[classSlot + 33].data = _bootstrapRandomAccess();
        p.classes[classSlot + 34].data = _bootstrapCopyOnWriteArrayList();
        p.classes[classSlot + 35].data = _bootstrapCopyOnWriteArrayListIterator();
'''
added_reserved='''
            || _isNamedClass(c, bytes("java/util/List"))
            || _isNamedClass(c, bytes("java/util/RandomAccess"))
            || _isNamedClass(c, bytes("java/util/concurrent/CopyOnWriteArrayList"))
            || _isNamedClass(c, bytes("java/util/concurrent/CopyOnWriteArrayListIterator"))'''
added_functions=''.join('    function _bootstrap%s() private pure returns (bytes memory) { return hex"%s"; }\n' % (name,new_engine_images['_bootstrap'+name]) for name in new_images)+'\n'
reversed_engine=engine.replace(new_domain,old_domain).replace('new bytes32[](75)','new bytes32[](71)').replace('uint256 count = inputCount + 69 +','uint256 count = inputCount + 65 +')
assert reversed_engine.count(added_root)==1 and reversed_engine.count(added_prepare)==1 and reversed_engine.count(added_reserved)==1 and reversed_engine.count(added_functions)==1
reversed_engine=reversed_engine.replace(added_root,'').replace(added_prepare,'').replace(added_reserved,'').replace(added_functions,'')
assert reversed_engine==old_engine
reversed_coord=coord.replace(new_domain,old_domain).replace(pins['address'][2:],'4d432d434c4153532d4e45572d494e5354303145').replace(pins['engine']['runtimeKeccak256'],'a3db4ed598190f09f38ae3f77fc3c95e465f37d5d2f0c34819fcd63123189a73')
assert reversed_coord==old_coord
print(json.dumps({'profile':pins['profile'],'bootstrapImages':75,'priorImagesUnchanged':71,'newImages':{n:pins['bootstrapSHA256'][n] for n in new_images},'engineBytes':pins['engine']['bytes'],'coordinatorBytes':pins['coordinator']['bytes']},indent=2))
