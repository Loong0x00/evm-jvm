#!/usr/bin/env python3
"""Strict reverse source guard for the four-image bounded lock append."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile

here=Path(__file__).resolve().parent
stage=here.parent
root=here.parents[4]
prior=root/'evidence/java-evm/minecraft-entry/copy-on-write-array-list-preflight'
pins=json.loads((stage/'pins.json').read_text())
engine=(stage/'engine/MCEntryInterpreter.sol').read_text()
coord=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
old_engine=(prior/'engine/MCEntryInterpreter.sol').read_text()
old_coord=(prior/'coordinator/MCEntryCoordinator.sol').read_text()
new_domain='MC-REENTRANT-LOCKS-PREFLIGHT1'
old_domain='MC-COPY-ON-WRITE-ARRAY-LIST-PREFLIGHT1'
new_images=('Lock','ReadWriteLock','ReentrantLock','ReentrantReadWriteLock')

assert pins['profile']==new_domain
assert pins['rawLimits']==[25,262144] and pins['bootstrapCount']==79
assert pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10
assert pins['exceptionKinds']==14 and pins['maxFrames']==128
assert pins['runtimeCap']==393216 and pins['checkpointCap']==1048576 and pins['headCap']==32768
assert 'MAX_RAW_CLASSES = 25' in engine and 'MAX_RAW_BYTES = 262144;' in engine
assert 'new bytes32[](79)' in engine and 'new uint256[](14)' in engine
assert engine.count(new_domain)==9 and coord.count(new_domain)==3
assert pins['address'][2:] in coord and pins['engine']['runtimeKeccak256'] in coord
assert 'return 11;' in engine and 'bytes("newInstance")' in engine
assert 'uint256 count = inputCount + 73 +' in engine
for name in new_images: assert f'_bootstrap{name}()' in engine
for name in ('java/util/concurrent/locks/Lock','java/util/concurrent/locks/ReadWriteLock','java/util/concurrent/locks/ReentrantLock','java/util/concurrent/locks/ReentrantReadWriteLock'):
    assert f'bytes("{name}")' in engine

# Rebuild the entire Java 8 subset from a bootclasspath stripped of every owned
# replacement. The four append images are accepted only if their exact class bytes
# derive from the source beside this verifier.
with tempfile.TemporaryDirectory(dir=root/'build') as td:
    td=Path(td); api=td/'rt.jar'; out=td/'classes'; out.mkdir()
    shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
    stripped=['java/lang/'+x+'.class' for x in ('String','System','Class','Number','NumberFormatException','Integer')]+[
        'java/util/'+x+'.class' for x in ('Iterator','Collection','AbstractCollection','NoSuchElementException','List','RandomAccess')
    ]+[
        'java/util/concurrent/CopyOnWriteArrayList.class','java/util/concurrent/CopyOnWriteArrayList$COWIterator.class',
        'java/util/concurrent/locks/Lock.class','java/util/concurrent/locks/ReadWriteLock.class',
        'java/util/concurrent/locks/ReentrantLock.class','java/util/concurrent/locks/ReentrantReadWriteLock.class'
    ]
    subprocess.run(['zip','-q','-d',api,*stripped],check=True)
    src=sorted(stage.glob('bootstrap/**/*.java'))
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out,*src],check=True)
    names={
        'String':'java/lang/String.class','System':'java/lang/System.class','Class':'java/lang/Class.class',
        'Number':'java/lang/Number.class','NumberFormatException':'java/lang/NumberFormatException.class','Integer':'java/lang/Integer.class',
        'Iterator':'java/util/Iterator.class','Collection':'java/util/Collection.class','AbstractCollection':'java/util/AbstractCollection.class','NoSuchElementException':'java/util/NoSuchElementException.class',
        'List':'java/util/List.class','RandomAccess':'java/util/RandomAccess.class',
        'CopyOnWriteArrayList':'java/util/concurrent/CopyOnWriteArrayList.class','CopyOnWriteArrayListIterator':'java/util/concurrent/CopyOnWriteArrayListIterator.class',
        'Lock':'java/util/concurrent/locks/Lock.class','ReadWriteLock':'java/util/concurrent/locks/ReadWriteLock.class',
        'ReentrantLock':'java/util/concurrent/locks/ReentrantLock.class','ReentrantReadWriteLock':'java/util/concurrent/locks/ReentrantReadWriteLock.class',
    }
    rebuilt={name:(out/path).read_bytes() for name,path in names.items()}
    assert {name:hashlib.sha256(data).hexdigest() for name,data in rebuilt.items()}==pins['bootstrapSHA256']

def image_map(source):
    return {m.group(1):m.group(2) for m in re.finditer(r'function (_bootstrap\w+)\([^)]*\).*?hex"([0-9a-f]+)"',source,re.S)}
old_images=image_map(old_engine); new_engine_images=image_map(engine)
assert len(old_images)==75 and len(new_engine_images)==79
for name,hexdata in old_images.items(): assert new_engine_images[name]==hexdata,name
for name in new_images: assert bytes.fromhex(new_engine_images['_bootstrap'+name])==rebuilt[name],name

added_root='''        // Bounded single-guest-thread lock family appends after all 75 prior images.
        h[75] = keccak256(_bootstrapLock());
        h[76] = keccak256(_bootstrapReadWriteLock());
        h[77] = keccak256(_bootstrapReentrantLock());
        h[78] = keccak256(_bootstrapReentrantReadWriteLock());
'''
added_prepare='''        // Four bounded lock images append after the complete 75-image tail.
        p.classes[classSlot + 36].data = _bootstrapLock();
        p.classes[classSlot + 37].data = _bootstrapReadWriteLock();
        p.classes[classSlot + 38].data = _bootstrapReentrantLock();
        p.classes[classSlot + 39].data = _bootstrapReentrantReadWriteLock();
'''
added_condition='''
                || _isReservedLockClass(users[i])'''
added_reserved='''    // The interpreter owns this deliberately narrow lock family. It is not a
    // concurrency implementation: images provide only single-thread field mutation.
    function _isReservedLockClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/util/concurrent/locks/Lock"))
            || _isNamedClass(c, bytes("java/util/concurrent/locks/ReadWriteLock"))
            || _isNamedClass(c, bytes("java/util/concurrent/locks/ReentrantLock"))
            || _isNamedClass(c, bytes("java/util/concurrent/locks/ReentrantReadWriteLock"));
    }

'''
added_functions=''.join('    function _bootstrap%s() private pure returns (bytes memory) { return hex"%s"; }\n' % (name,new_engine_images['_bootstrap'+name]) for name in new_images)
reversed_engine=engine.replace(new_domain,old_domain).replace('new bytes32[](79)','new bytes32[](75)').replace('uint256 count = inputCount + 73 +','uint256 count = inputCount + 69 +')
for piece in (added_root,added_prepare,added_condition,added_reserved,added_functions): assert reversed_engine.count(piece)==1
reversed_engine=reversed_engine.replace(added_root,'').replace(added_prepare,'').replace(added_condition,'').replace(added_reserved,'').replace(added_functions,'')
assert reversed_engine==old_engine
reversed_coord=coord.replace(new_domain,old_domain).replace(pins['address'][2:],'4d432d434f572d41525241592d4c4953542d3031').replace(pins['engine']['runtimeKeccak256'],'0b1215626372b160fea2a13dd804bcb13628ca70e85c8f576c9745e74a147da4')
assert reversed_coord==old_coord
print(json.dumps({'profile':pins['profile'],'bootstrapImages':79,'priorImagesUnchanged':75,'newImages':{n:pins['bootstrapSHA256'][n] for n in new_images},'engineBytes':pins['engine']['bytes'],'coordinatorBytes':pins['coordinator']['bytes']},indent=2))
