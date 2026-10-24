#!/usr/bin/env python3
"""Source-only P61-to-RAW160 audit; does not inspect or open any world database."""
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT.parent / 'raw160-source-base-p61'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def exact_replacement(relative, replacements):
    original = (BASE / relative).read_text()
    for old, new in replacements:
        assert old in original, (relative, old)
        original = original.replace(old, new)
    assert (ROOT / relative).read_text() == original, relative

base_manifest = json.loads((BASE / 'source-manifest.json').read_text())
assert base_manifest['worktreeBase'] == '89883b2dc6d47beee80de2c430e3e634f41cf3a4'
assert base_manifest['acceptedGuestCodeCommit'] == '0832116b3649833e8930ca4a4eb9ddd9bb6b769e'
for relative, metadata in base_manifest['files'].items():
    source = BASE / relative
    assert source.stat().st_size == metadata['bytes'] and sha(source) == metadata['sha256'], relative

exact_replacement('engine/MCEntryInterpreter.sol', [
    ('MC-SUPPLIER-LINK-BOUNDED-1', 'MC-RAW160-BOUNDED-1'),
    ('uint256 private constant MAX_RAW_CLASSES = 150;', 'uint256 private constant MAX_RAW_CLASSES = 160;'),
    ('uint32(150), uint32(1063930)', 'uint32(160), uint32(1063930)'),
])
exact_replacement('coordinator/MCEntryCoordinator.sol', [
    ('MC-SUPPLIER-LINK-BOUNDED-1', 'MC-RAW160-BOUNDED-1'),
    ('hex"cb0719839a5b81d48d19ff0adfa8ea6e3bce8d8cc834165962d8364f8145cee2"',
     'hex"02593391ee49cf1b8b9e67f2f45563cd498b30a93ded342b522300566a3bab33"'),
    ('address[150]', 'address[160]'), ('bytes32[150]', 'bytes32[160]'),
    ('uint32[150]', 'uint32[160]'), ('bytes[150]', 'bytes[160]'), ('n > 150', 'n > 160'),
])
exact_replacement('canonical-driver.go.txt', [
    ('MC-SUPPLIER-LINK-BOUNDED-1', 'MC-RAW160-BOUNDED-1'), ('> 150', '> 160'),
    ('455564', '455565'),
    ('dfa8d02fb2556300f5dfdb5bed542eee0fcc1bf4e563ac5f9a7b2b627d0cbdeb',
     'b385d221ca1f44fd476e23846aad83d0b3fa1de5d2d19fc62353259501e6f545'),
    ('0xcb0719839a5b81d48d19ff0adfa8ea6e3bce8d8cc834165962d8364f8145cee2',
     '0x02593391ee49cf1b8b9e67f2f45563cd498b30a93ded342b522300566a3bab33'),
    ('0x81d2f439c5dd7bcbead3dbfa2f08b9621617a3870aab4e24146cd2cad69bb6f4',
     '0x75b40eebc76278e48069620e7e3c56bed92c2e75f13489aee59a626f1d4bce34'),
])
assert (ROOT / 'canonical-driver.go').read_bytes() == (ROOT / 'canonical-driver.go.txt').read_bytes()
assert (ROOT / 'root_helper.py').read_text() == (BASE / 'root_helper.py').read_text().replace(
    'Exact ordered source commitments for the append-only Arrays.asList profile.',
    'Exact ordered source commitments for the bounded LOCAL raw160 profile.')

engine_src = (ROOT / 'engine/MCEntryInterpreter.sol').read_text()
coord_src = (ROOT / 'coordinator/MCEntryCoordinator.sol').read_text()
assert engine_src.count('JVMEVM:MC-RAW160-BOUNDED-1:') == 9
assert coord_src.count('MC-RAW160-BOUNDED-1/') == 4
assert 'MAX_RAW_BYTES = 1063930' in engine_src
assert coord_src.count('1063930') == 2
assert 'MAX_SELECTED_RESOURCE_BYTES = 4096' in coord_src
assert 'uint32(160), uint32(1063930), uint32(64), uint32(32), uint32(65536)' in engine_src

base_pins = json.loads((BASE / 'pins.json').read_text())
pins = json.loads((ROOT / 'pins.json').read_text())
assert pins['profile'] == pins['domain'] == 'MC-RAW160-BOUNDED-1'
assert pins['rawLimits'] == [160, 1063930]
assert pins['diagnosticClassBound'] == 288 and pins['maxClassIndexAtRaw160'] == 287
assert len(pins['engineDomains']) == 9 and len(pins['coordinatorDomains']) == 4
assert pins['engine']['bytes'] == 455565 and pins['coordinator']['bytes'] == 5411
assert pins['engine']['runtimeSHA256'] == 'b385d221ca1f44fd476e23846aad83d0b3fa1de5d2d19fc62353259501e6f545'
assert pins['engine']['runtimeKeccak256'] == '02593391ee49cf1b8b9e67f2f45563cd498b30a93ded342b522300566a3bab33'
assert pins['coordinator']['runtimeKeccak256'] == '75b40eebc76278e48069620e7e3c56bed92c2e75f13489aee59a626f1d4bce34'
assert pins['orderedBootstrapLeaves'] == base_pins['orderedBootstrapLeaves'] and len(pins['orderedBootstrapLeaves']) == 128

for name in ('MCEntryInterpreter', 'MCEntryCoordinator'):
    subdir = 'engine' if name == 'MCEntryInterpreter' else 'coordinator'
    baseline = json.loads((BASE / subdir / f'{name}.json').read_text())
    candidate = json.loads((ROOT / subdir / f'{name}.json').read_text())
    assert baseline['abi'] == candidate['abi'], f'{name}: ABI changed'
    if name == 'MCEntryInterpreter':
        assert baseline['storageLayout'] == candidate['storageLayout'], f'{name}: engine storage layout changed'
    assert candidate['compiler'] == baseline['compiler']
    assert candidate['codeHashes']['runtimeSHA256'] == pins[subdir]['runtimeSHA256']
    assert candidate['codeHashes']['runtimeKeccak256'] == pins[subdir]['runtimeKeccak256']
    assert candidate['sourceHashes'][f'{name}.sol'] == sha(ROOT / subdir / f'{name}.sol')

print('PASS: P61 source snapshot, exact bounded count/domain delta, ABI, engine storage, byte cap, 128 leaves, candidate pins')
print('NOTE: coordinator private fixed-array storage slots necessarily shift in the new constructor-only 160-class profile; external ABI and checkpoint codec are unchanged.')
