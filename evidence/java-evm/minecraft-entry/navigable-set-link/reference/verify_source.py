#!/usr/bin/env python3
"""Reproducible source/image/root checks for the P45 NavigableSet link derivative."""
import hashlib, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from root_helper import leaf_pairs, root_record

HERE = pathlib.Path(__file__).resolve().parents[1]
BASE = HERE.parent / 'navigable-set-source-base-p45'
SRC = HERE / 'engine' / 'MCEntryInterpreter.sol'
source = SRC.read_text()
base = (BASE / 'engine' / 'MCEntryInterpreter.sol').read_text()
assert leaf_pairs(source)[:108] == leaf_pairs(base), 'P45 bootstrap image/root prefix changed'
record = root_record(source, 'JVMEVM:MC-HASH-MAP-PUT-BOUNDED-P45-COMPARATOR:BOOTSTRAP:1', str(HERE.parents[3]), os.environ)
pins = json.loads((HERE / 'pins.json').read_text())
assert len(record['leaves']) == 110
assert record['root'] == pins['bootstrapRoot']
assert record['leaves'][108:] == [x['keccak256'] for x in pins['newImages']]
for idx, name in ((108, 'SortedSet'), (109, 'NavigableSet')):
    m = __import__('re').search(r'function _bootstrap' + name + r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', source)
    assert m
    raw = bytes.fromhex(m.group(1))
    cls = (HERE / 'java-classes' / 'java' / 'util' / (name + '.class')).read_bytes()
    pin = pins['newImages'][idx - 108]
    assert raw == cls, name + ' materializer differs from reproducible javac image'
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    assert record['leaves'][idx] == pin['keccak256']
assert 'new bytes32[](110)' in source
assert 'MAX_RAW_CLASSES = 150' in source and 'MAX_RAW_BYTES = 1063930' in source
assert '_isNamedClass(users[i], bytes("java/util/SortedSet"))' in source
assert '_isNamedClass(users[i], bytes("java/util/NavigableSet"))' in source
print(json.dumps({'bootstrapRoot': record['root'], 'bootstrapCount': 110,
                  'p45PrefixUnchanged': True, 'newImages': pins['newImages']}, indent=2))
