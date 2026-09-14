#!/usr/bin/env python3
"""Strict Java-8 and reverse-source guard for the two-image queue append."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile

here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
parent=root/'evidence/java-evm/minecraft-entry/classcount26-preflight'
pins=json.loads((stage/'pins.json').read_text())
engine=(stage/'engine/MCEntryInterpreter.sol').read_text()
coord=(stage/'coordinator/MCEntryCoordinator.sol').read_text()
driver=(stage/'tools/Go.txt').read_text()
old_engine=(parent/'engine/MCEntryInterpreter.sol').read_text()
old_coord=(parent/'coordinator/MCEntryCoordinator.sol').read_text()
old_driver=(parent/'tools/Go.txt').read_text()
old='MC-CLASSCOUNT26-PREFLIGHT1'; new='MC-CONCURRENT-LINKED-QUEUE-PREFLIGHT1'
old_address='4d43434c415353434f554e543236000000000001'
new_address=pins['address'][2:]
old_owner='4d432d434c415353434f554e5432364f574e4552'
new_owner=pins['owner'][2:]
new_images=('Queue','ConcurrentLinkedQueue')

assert pins['profile']==new and pins['rawLimits']==[26,262144]
assert pins['bootstrapCount']==81 and pins['globalNativeBindings']==11 and pins['stringLocalBinding']==10
assert pins['exceptionKinds']==14 and pins['maxFrames']==128 and pins['runtimeCap']==393216
assert pins['checkpointCap']==1048576 and pins['headCap']==32768
assert 'MAX_RAW_CLASSES = 26' in engine and 'uint32(26), uint32(262144)' in engine
assert 'new bytes32[](81)' in engine and 'new uint256[](14)' in engine
assert engine.count(new)==9 and coord.count(new)==3
assert new_address in coord and pins['engine']['runtimeKeccak256'] in coord
assert 'return 11;' in engine and 'bytes("newInstance")' in engine
assert 'uint256 count = inputCount + 75 +' in engine
for name in new_images: assert f'_bootstrap{name}()' in engine
for name in ('java/util/Queue','java/util/concurrent/ConcurrentLinkedQueue'):
    assert f'bytes("{name}")' in engine

# Compile every owned image against an rt.jar stripped of every replacement.
with tempfile.TemporaryDirectory(dir=root/'build') as td:
    td=Path(td); api=td/'rt.jar'; out=td/'classes'; out.mkdir()
    shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api)
    stripped=['java/lang/'+x+'.class' for x in ('String','System','Class','Number','NumberFormatException','Integer')]+[
        'java/util/'+x+'.class' for x in ('Iterator','Collection','AbstractCollection','NoSuchElementException','List','RandomAccess','Queue')
    ]+[
        'java/util/concurrent/CopyOnWriteArrayList.class','java/util/concurrent/CopyOnWriteArrayList$COWIterator.class',
        'java/util/concurrent/ConcurrentLinkedQueue.class',
        'java/util/concurrent/locks/Lock.class','java/util/concurrent/locks/ReadWriteLock.class',
        'java/util/concurrent/locks/ReentrantLock.class','java/util/concurrent/locks/ReentrantReadWriteLock.class'
    ]
    subprocess.run(['zip','-q','-d',api,*stripped],check=True)
    src=sorted(stage.glob('bootstrap/**/*.java'))
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',out,*src],check=True)
    paths={
        'String':'java/lang/String.class','System':'java/lang/System.class','Class':'java/lang/Class.class',
        'Number':'java/lang/Number.class','NumberFormatException':'java/lang/NumberFormatException.class','Integer':'java/lang/Integer.class',
        'Iterator':'java/util/Iterator.class','Collection':'java/util/Collection.class','AbstractCollection':'java/util/AbstractCollection.class','NoSuchElementException':'java/util/NoSuchElementException.class',
        'List':'java/util/List.class','RandomAccess':'java/util/RandomAccess.class','Queue':'java/util/Queue.class',
        'CopyOnWriteArrayList':'java/util/concurrent/CopyOnWriteArrayList.class','CopyOnWriteArrayListIterator':'java/util/concurrent/CopyOnWriteArrayListIterator.class',
        'ConcurrentLinkedQueue':'java/util/concurrent/ConcurrentLinkedQueue.class',
        'Lock':'java/util/concurrent/locks/Lock.class','ReadWriteLock':'java/util/concurrent/locks/ReadWriteLock.class',
        'ReentrantLock':'java/util/concurrent/locks/ReentrantLock.class','ReentrantReadWriteLock':'java/util/concurrent/locks/ReentrantReadWriteLock.class',
    }
    rebuilt={name:(out/path).read_bytes() for name,path in paths.items()}
    assert {n:hashlib.sha256(x).hexdigest() for n,x in rebuilt.items()}==pins['bootstrapSHA256']

def image_map(source):
    return {m.group(1):m.group(2) for m in re.finditer(r'function (_bootstrap\w+)\([^)]*\).*?hex"([0-9a-f]+)"',source,re.S)}
old_images=image_map(old_engine); new_engine_images=image_map(engine)
assert len(old_images)==79 and len(new_engine_images)==81
for name,hexdata in old_images.items(): assert new_engine_images[name]==hexdata,name
for name in new_images: assert bytes.fromhex(new_engine_images['_bootstrap'+name])==rebuilt[name],name

added_root='''        // Queue/ConcurrentLinkedQueue append after the complete 79-image lock tail.
        h[79] = keccak256(_bootstrapQueue());
        h[80] = keccak256(_bootstrapConcurrentLinkedQueue());
'''
added_prepare='''        // Queue/ConcurrentLinkedQueue append after the complete 79-image lock tail.
        p.classes[classSlot + 40].data = _bootstrapQueue();
        p.classes[classSlot + 41].data = _bootstrapConcurrentLinkedQueue();
'''
added_condition='''
                || _isReservedQueueClass(users[i])'''
added_reserved='''    // This queue subset is guest-owned Object[] copying only; it deliberately
    // does not provide host/native/concurrent progress or broader Queue APIs.
    function _isReservedQueueClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/util/Queue"))
            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentLinkedQueue"));
    }

'''
added_functions='\n\n' + '\n'.join('    function _bootstrap%s() private pure returns (bytes memory) { return hex"%s"; }' % (name,new_engine_images['_bootstrap'+name]) for name in new_images) + '\n'
reversed_engine=engine.replace(new,old).replace('new bytes32[](81)','new bytes32[](79)').replace('uint256 count = inputCount + 75 +','uint256 count = inputCount + 73 +')
for piece in (added_root,added_prepare,added_condition,added_reserved,added_functions): assert reversed_engine.count(piece)==1
reversed_engine=reversed_engine.replace(added_root,'').replace(added_prepare,'').replace(added_condition,'').replace(added_reserved,'').replace(added_functions,'')
assert reversed_engine==old_engine
reversed_coord=coord.replace(new,old).replace(new_address,old_address).replace(pins['engine']['runtimeKeccak256'],'9517f8a6b65f0942bb73b35322075baa36a819799c2c632639f584d1894e8009')
assert reversed_coord==old_coord
reversed_driver=(driver.replace(new,old).replace(new_address,old_address).replace(new_owner,old_owner).replace('388963','385212')
 .replace(pins['engine']['runtimeSHA256'],'fd1a480ba34474a519d38909f098cddaa7374f7754fac18c25cdd9bdc96b39af')
 .replace(pins['engine']['runtimeKeccak256'],'9517f8a6b65f0942bb73b35322075baa36a819799c2c632639f584d1894e8009')
 .replace(pins['coordinator']['runtimeKeccak256'],'d706f2ebc5e6a0fc87ac78e64c516872e72a1115f3deab872f69ced2697a4b6e'))
assert reversed_driver==old_driver
print(json.dumps({'profile':pins['profile'],'bootstrapImages':81,'priorImagesUnchanged':79,
 'newImages':{n:pins['bootstrapSHA256'][n] for n in new_images},'engineBytes':pins['engine']['bytes'],
 'coordinatorBytes':pins['coordinator']['bytes'],'rawLimits':pins['rawLimits'],'diagnosticClassBound':107},indent=2))
