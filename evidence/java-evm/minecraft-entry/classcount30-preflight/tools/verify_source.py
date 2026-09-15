#!/usr/bin/env python3
"""Strict reverse verifier: cap30 source == accepted parent-3ed302a92 + mechanical delta only.

No original artifact is read.  The staged engine must differ from the parent engine in
exactly nine equal-length domain strings, one raw-class constant and one config word; the
coordinator in domain/arrays/guard/address/engine-codehash; the driver in
domain/addresses/limits/hash pins; the diagnostic in one total-class bound.  All 83
bootstrap images, all native bindings and every other limit must be byte-identical.
"""
from pathlib import Path
import argparse, hashlib, json, re, sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PARENT = STAGE.parent / 'parent-3ed302a92'
AP = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None

DOMAIN_OLD = 'MC-ENUM-SET-PARENT2'
DOMAIN = 'MC-ENUM-SET-PARENT3'
ADDR_OLD = '4d432d454e554d2d5345542d5032000000000001'
ADDR = '4d432d454e554d2d5345542d5033000000000001'
OWNER_OLD = '4d432d454e554d2d5345542d4f32000000000002'
OWNER = '4d432d454e554d2d5345542d4f33000000000002'
ENGINE_SHA_OLD = '8bdc4b6d2159009fcab50faa861d56bff01eafe25cf9551383f6046ff5d14ae0'
ENGINE_KECCAK_OLD = '193fb2fa9fad5417924977b956f06a11c52952c797892c1e2a074c3aa3850c00'
COORD_KECCAK_OLD = 'd036eb145986d342d0cc30130ddbffc2e83cf4474aae05fde1ccfa513d8be5e8'

pins = json.loads((STAGE / 'pins.json').read_text())
new_engine_keccak = pins['engine']['runtimeKeccak256']
new_engine_sha = pins['engine']['runtimeSHA256']
new_coord_keccak = pins['coordinator']['runtimeKeccak256']

# --- parent input pinning -------------------------------------------------------
want_inputs = {
    'artifacts/engine/MCEntryInterpreter.sol': hashlib.sha256((PARENT / 'artifacts/engine/MCEntryInterpreter.sol').read_bytes()).hexdigest(),
    'artifacts/coordinator/MCEntryCoordinator.sol': hashlib.sha256((PARENT / 'artifacts/coordinator/MCEntryCoordinator.sol').read_bytes()).hexdigest(),
    'executed-driver.go.txt': hashlib.sha256((PARENT / 'executed-driver.go.txt').read_bytes()).hexdigest(),
    'checkpoint_frames.py': hashlib.sha256((PARENT / 'checkpoint_frames.py').read_bytes()).hexdigest(),
}
assert json.loads((STAGE / 'parent-input.json').read_text()) == {'basis': '5b55d0ce6', 'parentEvidence': 'parent-3ed302a92', 'sha256': want_inputs}

# --- engine ---------------------------------------------------------------------
e0 = (PARENT / 'artifacts/engine/MCEntryInterpreter.sol').read_text()
e = (STAGE / 'engine/MCEntryInterpreter.sol').read_text()
want = (e0.replace(DOMAIN_OLD, DOMAIN)
          .replace('MAX_RAW_CLASSES = 29', 'MAX_RAW_CLASSES = 30')
          .replace('uint32(29), uint32(262144)', 'uint32(30), uint32(262144)'))
assert e == want, 'engine differs beyond the mechanical cap/domain delta'
assert e.count(DOMAIN) == 9 and e.count('MAX_RAW_CLASSES = 30') == 1 and e.count('uint32(30), uint32(262144)') == 1
assert DOMAIN_OLD not in e and 'MAX_RAW_CLASSES = 29' not in e and 'uint32(29), uint32(262144)' not in e
assert 'MAX_RAW_BYTES = 262144;' in e and 'MAX_CHECKPOINT_BYTES = 1048576;' in e
assert 'COMMIT_RESERVE = 25_000_000;' in e and 'LOCAL_MC_VFS0A_BOUNDARY_GAS_CAP = 1_000_000_000;' in e
pat = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
b0 = re.findall(pat, e0); b = re.findall(pat, e)
assert len(b0) == len(b) == 83 and b0 == b, 'bootstrap images/order changed'
assert e.count('new bytes32[](83)') == 1 and e.count('new uint256[](14)') == 1
assert 'return 11;' in e and 'return 12;' in e  # native binding descriptor ids 11/12 preserved
m = re.search(r'DBOOT_ENUMSET = keccak256\(hex"([0-9a-f]+)"\)', e)
assert m and hashlib.sha256(bytes.fromhex(m.group(1))).hexdigest() == pins['bootstrapSHA256']['EnumSet']

# --- coordinator ----------------------------------------------------------------
c0 = (PARENT / 'artifacts/coordinator/MCEntryCoordinator.sol').read_text()
c = (STAGE / 'coordinator/MCEntryCoordinator.sol').read_text()
want = (c0.replace(DOMAIN_OLD, DOMAIN).replace('[29]', '[30]').replace('n > 29', 'n > 30')
          .replace(ADDR_OLD, ADDR).replace(ENGINE_KECCAK_OLD, new_engine_keccak))
assert c == want, 'coordinator differs beyond the mechanical cap/domain delta'
assert c.count(DOMAIN) == 3 and c.count('[30]') == 4 and c.count('n > 30') == 1 and c.count(ADDR) == 1
assert c.count(new_engine_keccak) == 1 and DOMAIN_OLD not in c and '[29]' not in c and 'n > 29' not in c
assert 'uint8 public classCount;' in c and 'totalClassBytes' in c

# --- driver ---------------------------------------------------------------------
d0 = (PARENT / 'executed-driver.go.txt').read_text()
d = (STAGE / 'tools/Go.txt').read_text()
want = (d0.replace(DOMAIN_OLD, DOMAIN)
          .replace('0x' + ADDR_OLD, '0x' + ADDR).replace('0x' + OWNER_OLD, '0x' + OWNER)
          .replace('> 29', '> 30')
          .replace(ENGINE_SHA_OLD, new_engine_sha)
          .replace('0x' + ENGINE_KECCAK_OLD, '0x' + new_engine_keccak)
          .replace('0x' + COORD_KECCAK_OLD, '0x' + new_coord_keccak))
assert d == want, 'driver differs beyond the mechanical cap/domain delta'
assert d.count(DOMAIN) == 5 and d.count('> 30') == 2 and d.count(ADDR) == 1 and d.count(OWNER) == 1
assert 'const format = "%s-BOUNDED-1"' % DOMAIN in d
for x in (new_engine_sha, new_engine_keccak, new_coord_keccak, '0x' + ADDR, '0x' + OWNER):
    assert x in d
assert DOMAIN_OLD not in d and '> 29' not in d

# --- diagnostic -----------------------------------------------------------------
diag0 = (PARENT / 'checkpoint_frames.py').read_text()
assert (STAGE / 'tools/checkpoint_diagnostic.py').read_text() == diag0.replace('classes<=112', 'classes<=113')
assert (STAGE / 'tools/checkpoint_diagnostic.py').read_text().count('classes<=113') == 1

# --- pins / fixed limits --------------------------------------------------------
assert pins['rawLimits'] == [30, 262144] and pins['runtimeCap'] == 393216
assert pins['bootstrapCount'] == 83 and pins['globalNativeBindings'] == 12 and pins['stringLocalBinding'] == 10
assert pins['exceptionKinds'] == 14 and pins['maxFrames'] == 128
assert pins['externalLocalGas'] == 1000000000 and pins['reserve'] == 25000000
assert pins['checkpointCap'] == 1048576 and pins['headCap'] == 32768 and pins['diagnosticClassBound'] == 113
assert pins['domain'] == DOMAIN and pins['address'] == '0x' + ADDR and pins['owner'] == '0x' + OWNER
assert pins['parentEvidence'] == 'parent-3ed302a92' and pins['basis'] == '5b55d0ce6'

# --- optional built-artifact agreement ------------------------------------------
artifacts = None
if AP is not None:
    ea = json.loads((AP / 'engine/MCEntryInterpreter.json').read_text())
    ca = json.loads((AP / 'coordinator/MCEntryCoordinator.json').read_text())
    egot = {'bytes': len(ea['deployedBytecode']) // 2, **ea['codeHashes']}
    cgot = {'bytes': len(ca['deployedBytecode']) // 2, **ca['codeHashes']}
    assert egot == pins['engine'] and cgot == pins['coordinator'], (egot, cgot)
    assert egot['bytes'] <= pins['runtimeCap'] and cgot['bytes'] == 4146 and egot['bytes'] == 393205
    artifacts = {'engine': egot, 'coordinator': cgot}

print(json.dumps({
    'parentEvidence': 'parent-3ed302a92', 'parentInputsVerified': len(want_inputs),
    'bootstrapImages': 83, 'globalNativeBindings': 12, 'stringLocalBinding': 10, 'exceptionKinds': 14,
    'rawClassCount': 30, 'rawByteCount': 262144, 'diagnosticClassBound': 113,
    'domain': DOMAIN, 'address': '0x' + ADDR, 'owner': '0x' + OWNER,
    'engine': pins['engine'], 'coordinator': pins['coordinator'], 'artifacts': artifacts,
}, indent=2))
