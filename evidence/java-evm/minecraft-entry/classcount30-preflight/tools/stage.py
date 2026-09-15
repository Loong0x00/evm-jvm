#!/usr/bin/env python3
"""Deterministic cap29->30 source staging from the accepted parent-3ed302a92 artifacts.

Only mechanical count/domain changes are applied; every other engine byte, all 83
bootstrap images, the 12 native bindings and every fixed limit are inherited verbatim
from the parent evidence.  The strict reverse verifier re-derives the same expectation
and compares against the staged files.
"""
from pathlib import Path
import argparse, hashlib, json

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PARENT = STAGE.parent / 'parent-3ed302a92'

DOMAIN_OLD = 'MC-ENUM-SET-PARENT2'
DOMAIN = 'MC-ENUM-SET-PARENT3'
ADDR_OLD = '4d432d454e554d2d5345542d5032000000000001'
ADDR = '4d432d454e554d2d5345542d5033000000000001'
OWNER_OLD = '4d432d454e554d2d5345542d4f32000000000002'
OWNER = '4d432d454e554d2d5345542d4f33000000000002'
ENGINE_SHA_OLD = '8bdc4b6d2159009fcab50faa861d56bff01eafe25cf9551383f6046ff5d14ae0'
ENGINE_KECCAK_OLD = '193fb2fa9fad5417924977b956f06a11c52952c797892c1e2a074c3aa3850c00'
COORD_KECCAK_OLD = 'd036eb145986d342d0cc30130ddbffc2e83cf4474aae05fde1ccfa513d8be5e8'
ZERO64 = '0' * 64

p = argparse.ArgumentParser()
p.add_argument('--engine-json', type=Path)
p.add_argument('--coordinator-json', type=Path)
a = p.parse_args()

engine_keccak = ZERO64
engine_sha = ZERO64
engine_bytes = 0
coord_keccak = ZERO64
coord_bytes = 0
if a.engine_json is not None:
    e = json.loads(a.engine_json.read_text())
    engine_keccak = e['codeHashes']['runtimeKeccak256']
    engine_sha = e['codeHashes']['runtimeSHA256']
    engine_bytes = len(e['deployedBytecode']) // 2
if a.coordinator_json is not None:
    c = json.loads(a.coordinator_json.read_text())
    coord_keccak = c['codeHashes']['runtimeKeccak256']
    coord_bytes = len(c['deployedBytecode']) // 2


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def copy_js(src, dst):
    write(dst, src.read_text())


# --- engine: fresh equal-length domain, one cap constant and one config word ------
e0 = (PARENT / 'artifacts/engine/MCEntryInterpreter.sol').read_text()
assert e0.count(DOMAIN_OLD) == 9 and e0.count('MAX_RAW_CLASSES = 29') == 1
assert e0.count('uint32(29), uint32(262144)') == 1
engine = (e0.replace(DOMAIN_OLD, DOMAIN)
            .replace('MAX_RAW_CLASSES = 29', 'MAX_RAW_CLASSES = 30')
            .replace('uint32(29), uint32(262144)', 'uint32(30), uint32(262144)'))
write(STAGE / 'engine/MCEntryInterpreter.sol', engine)
copy_js(PARENT / 'artifacts/engine/build.js', STAGE / 'engine/build.js')

# --- coordinator: same domain, widened fixed arrays/guard, fresh anchored address --
c0 = (PARENT / 'artifacts/coordinator/MCEntryCoordinator.sol').read_text()
assert c0.count(DOMAIN_OLD) == 3 and c0.count('[29]') == 4 and c0.count('n > 29') == 1
assert c0.count(ADDR_OLD) == 1 and c0.count(ENGINE_KECCAK_OLD) == 1
coordinator = (c0.replace(DOMAIN_OLD, DOMAIN)
                 .replace('[29]', '[30]')
                 .replace('n > 29', 'n > 30')
                 .replace(ADDR_OLD, ADDR)
                 .replace(ENGINE_KECCAK_OLD, engine_keccak))
write(STAGE / 'coordinator/MCEntryCoordinator.sol', coordinator)
copy_js(PARENT / 'artifacts/coordinator/build.js', STAGE / 'coordinator/build.js')

# --- driver: fresh domain/addresses/hash pins, two transport count guards ----------
d0 = (PARENT / 'executed-driver.go.txt').read_text()
assert d0.count(DOMAIN_OLD) == 5 and d0.count('> 29') == 2
assert d0.count('0x' + ADDR_OLD) == 1 and d0.count('0x' + OWNER_OLD) == 1
assert d0.count(ENGINE_SHA_OLD) == 1
assert d0.count('0x' + ENGINE_KECCAK_OLD) == 1 and d0.count('0x' + COORD_KECCAK_OLD) == 1
driver = (d0.replace(DOMAIN_OLD, DOMAIN)
            .replace('0x' + ADDR_OLD, '0x' + ADDR)
            .replace('0x' + OWNER_OLD, '0x' + OWNER)
            .replace('> 29', '> 30')
            .replace(ENGINE_SHA_OLD, engine_sha)
            .replace('0x' + ENGINE_KECCAK_OLD, '0x' + engine_keccak)
            .replace('0x' + COORD_KECCAK_OLD, '0x' + coord_keccak))
write(STAGE / 'tools/Go.txt', driver)

# --- diagnostic: total-class bound 113 for raw30 plus 83 bootstrap images ----------
diag0 = (PARENT / 'checkpoint_frames.py').read_text()
assert diag0.count('classes<=112') == 1
write(STAGE / 'tools/checkpoint_diagnostic.py', diag0.replace('classes<=112', 'classes<=113'))

# --- pins -------------------------------------------------------------------------
base = json.loads((PARENT / 'pins.json').read_text())
pins = dict(base)
pins.update({
    'basis': '5b55d0ce6',
    'parentEvidence': 'parent-3ed302a92',
    'worker': 'bench-formal-t1-cap30-deepseek',
    'phase': 'staged' if engine_bytes == 0 or coord_bytes == 0 else 'built',
    'domain': DOMAIN,
    'address': '0x' + ADDR,
    'owner': '0x' + OWNER,
    'runtimeCap': 393216,
    'bootstrapCount': 83,
    'globalNativeBindings': 12,
    'stringLocalBinding': 10,
    'exceptionKinds': 14,
    'externalLocalGas': 1000000000,
    'reserve': 25000000,
    'maxFrames': 128,
    'rawLimits': [30, 262144],
    'checkpointCap': 1048576,
    'headCap': 32768,
    'diagnosticClassBound': 113,
    'engine': {'bytes': engine_bytes or 393205, 'initSHA256': ZERO64, 'runtimeSHA256': engine_sha, 'runtimeKeccak256': engine_keccak},
    'coordinator': {'bytes': coord_bytes or 4146, 'initSHA256': ZERO64, 'runtimeSHA256': ZERO64, 'runtimeKeccak256': coord_keccak},
})
if engine_bytes:
    pins['engine'] = {'bytes': engine_bytes, **json.loads(a.engine_json.read_text())['codeHashes']}
if coord_bytes:
    pins['coordinator'] = {'bytes': coord_bytes, **json.loads(a.coordinator_json.read_text())['codeHashes']}
pins.pop('parentAmendment', None)
write(STAGE / 'pins.json', json.dumps(pins, indent=2) + '\n')

# --- parent input digests ----------------------------------------------------------
inputs = {
    'artifacts/engine/MCEntryInterpreter.sol': hashlib.sha256((PARENT / 'artifacts/engine/MCEntryInterpreter.sol').read_bytes()).hexdigest(),
    'artifacts/coordinator/MCEntryCoordinator.sol': hashlib.sha256((PARENT / 'artifacts/coordinator/MCEntryCoordinator.sol').read_bytes()).hexdigest(),
    'executed-driver.go.txt': hashlib.sha256((PARENT / 'executed-driver.go.txt').read_bytes()).hexdigest(),
    'checkpoint_frames.py': hashlib.sha256((PARENT / 'checkpoint_frames.py').read_bytes()).hexdigest(),
}
write(STAGE / 'parent-input.json', json.dumps({'basis': '5b55d0ce6', 'parentEvidence': 'parent-3ed302a92', 'sha256': inputs}, indent=2) + '\n')
print(json.dumps({'staged': str(STAGE), 'engineKeccak': engine_keccak, 'coordinatorKeccak': coord_keccak, 'phase': pins['phase']}, indent=2))
