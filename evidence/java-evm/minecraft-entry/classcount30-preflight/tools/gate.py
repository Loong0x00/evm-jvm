#!/usr/bin/env python3
"""Generated-only raw-class-count30 EVM gate; no original JAR/class/world input.

Required coverage: exact 29/30 q1/q7/direct/reopen/canonical worlds, reordered 30,
independently reached 31-class atomic refusals at the driver, product-coordinator and
product-engine layers, and the 262144/262145 aggregate byte boundaries.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time

here = Path(__file__).resolve().parent; root = here.parents[4]
build = Path(sys.argv[1]).resolve(); fixtures = Path(sys.argv[2]).resolve(); out = Path(sys.argv[3]).resolve()
assert build.parent == root / 'build' and fixtures.parent == root / 'build' and out.parent == root / 'build'
assert out.name.startswith('java-diff-mc-classcount30-') and not out.exists()
out.mkdir(); logs = out / 'logs'; logs.mkdir(); start = time.monotonic(); commands = []
pins = json.loads((here.parent / 'pins.json').read_text())
assert pins['rawLimits'] == [30, 262144] and pins['diagnosticClassBound'] == 113 and pins['bootstrapCount'] == 83
assert pins['globalNativeBindings'] == 12 and pins['domain'] == 'MC-ENUM-SET-PARENT3'


def names(label):
    return ','.join(json.loads((fixtures / (label + '.json')).read_text())['entries'])


def run(label, args, bindings=None, expect=0):
    env = dict(os.environ, TMPDIR=str(out / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    out.joinpath('tmp').mkdir(exist_ok=True)
    if bindings:
        env['MC_ENTRY_BINDINGS'] = names(bindings)
    log = logs / (label + '.log'); t = time.monotonic()
    with log.open('w') as f:
        p = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=1200)
    row = {'label': label, 'command': list(map(str, args)), 'exit': p.returncode, 'elapsedSeconds': time.monotonic() - t}
    commands.append(row); (logs / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    assert p.returncode == expect, (label, p.returncode, log)


def report(w):
    return w.parent / 'reports' / w.name


def failure(w, name):
    return json.loads((report(w) / name).read_text())


def words(x):
    return list(map(str, x['uint256Words']))


def inspect(world, n, q):
    h = json.loads((world / 'durable-head.json').read_text())
    assert h['lifecycle'] == h['outcome'] == 2 and h['result'] == 0 and len(h['decoders']) == n and h['totalClassBytes'] <= 262144
    cp = (world / 'checkpoints' / (h['checkpointSHA256'] + '.bin')).read_bytes()
    assert hashlib.sha256(cp).hexdigest() == h['checkpointSHA256']
    d.inspect(cp)
    active = {x['classIndex'] for x in d.inspect(cp)['initialization'] if x['state'] == 2}
    assert set(range(n)).issubset(active), (n, q, active)
    assert d.inspect(cp)['classCount'] == n + 83, (n, d.inspect(cp)['classCount'])
    return {'epoch': h['epoch'], 'jvmSteps': h['jvmSteps'], 'internalSteps': h['internalSteps'],
            'machineRoot': h['machineRoot'], 'opaquePayloadSHA256': hashlib.sha256(cp[280:]).hexdigest(),
            'totalClassBytes': h['totalClassBytes'], 'counters': h['counters']}


spec = importlib.util.spec_from_file_location('checkpoint_diagnostic', here / 'checkpoint_diagnostic.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

node_env = dict(os.environ, NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules', PYTHONDONTWRITEBYTECODE='1')


def error_selectors(path):
    js = ("const fs=require('fs'),{keccak256}=require('js-sha3');const a=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
          "console.log(JSON.stringify(a.filter(x=>x.type==='error').map(e=>[e.name+'('+e.inputs.map(i=>i.type).join(',')+')','0x'+keccak256(e.name+'('+e.inputs.map(i=>i.type).join(',')+')').slice(0,8)])))")
    r = subprocess.run(['node', '-e', js, str(path)], env=node_env, capture_output=True, text=True, check=True)
    return dict(json.loads(r.stdout))


driver = build / 'driver'; coord = build / 'coordinator/MCEntryCoordinator.json'; engine = build / 'engine/MCEntryInterpreter.json'
ENGINE_ERRORS = error_selectors(build / 'engine/MCEntryInterpreter.abi.json')
COORD_ERRORS = error_selectors(build / 'coordinator/MCEntryCoordinator.abi.json')
assert COORD_ERRORS['MR0Error(uint256)'] == '0xab23ed08' and ENGINE_ERRORS['LinkError(uint256,uint256)'] == '0x427cfac5'
rows = {}

# Exact below-cap and new-cap packages: one uninterrupted q4096 direct run plus independent
# q1/q7 checkpoint/reopen chains.  Canonical terminal machine and opaque blobs must be
# quantum invariant; reordered raw bindings are intentionally a distinct package root.
for n in (29, 30):
    baseline = None
    for tag, q in (('q1', 1), ('q7', 7), ('direct', 4096)):
        w = out / ('world-%d-%s' % (n, tag))
        run('%d-%s-start' % (n, tag), [driver, 'setup-chain', w, coord, engine, fixtures / (str(n) + '.zip'), str(q)], str(n))
        run('%d-%s-finish' % (n, tag), [driver, 'finish', w, coord, engine, fixtures / (str(n) + '.zip'), str(q)], str(n))
        run('%d-%s-reopen' % (n, tag), [driver, 'verify', w, coord, engine, fixtures / (str(n) + '.zip'), str(q)], str(n))
        x = inspect(w, n, q); rows['%d/%s' % (n, tag)] = x
        if baseline is None:
            baseline = x
        else:
            for k in ('machineRoot', 'opaquePayloadSHA256'):
                assert x[k] == baseline[k], (n, tag, k)
w = out / 'world-30-reordered'
run('30-reordered-start', [driver, 'setup-chain', w, coord, engine, fixtures / '30.zip', '4096'], '30-reordered')
run('30-reordered-finish', [driver, 'finish', w, coord, engine, fixtures / '30.zip', '4096'], '30-reordered')
run('30-reordered-reopen', [driver, 'verify', w, coord, engine, fixtures / '30.zip', '4096'], '30-reordered')
x = inspect(w, 30, 4096); h = json.loads((w / 'durable-head.json').read_text())
base = json.loads((out / 'world-30-direct/durable-head.json').read_text())
assert h['packageRoot'] != base['packageRoot']
x['packageRoot'] = h['packageRoot']; rows['30/reordered'] = x

# Layer 1: product driver transport guard refuses 31 bindings before newEnv/world mutation.
w = out / 'world-31-driver'
run('31-driver-pre-mutation-refusal', [driver, 'setup-chain', w, coord, engine, fixtures / '31.zip', '4096'], '31', expect=2)
assert not w.exists(); rows['31/driver'] = {'layer': 'driver', 'worldExists': False}

# Layer 2: clone only the generated test transport guard so the unchanged product
# coordinator constructor is reached; its code hash and all production pins stay exact.
def test_driver(label, coordinator_art, coordinator_keccak):
    src = (here / 'Go.txt').read_text().replace('> 30', '> 31').replace(pins['coordinator']['runtimeKeccak256'], coordinator_keccak)
    path = out / (label + '.go'); path.write_text(src)
    exe = out / label
    subprocess.run(['gofmt', '-w', str(path)], cwd=root, check=True)
    subprocess.run(['go', 'build', '-trimpath', '-o', str(exe), str(path)], cwd=root, check=True)
    return exe


coord_driver = test_driver('coordinator-31-driver', coord, pins['coordinator']['runtimeKeccak256'])
w = out / 'world-31-coordinator'
run('31-coordinator-atomic-refusal', [coord_driver, 'boundary-create', w, coord, engine, fixtures / '31.zip', '4096'], '31')
b = failure(w, 'boundary-refusal.json')
assert b['selector'] == '0xab23ed08' and words(b) == ['2'] and b['rootUnchanged']; rows['31/coordinator'] = b

# Layer 3: a mechanically widened, disposable coordinator exposes the immutable product
# engine's raw-class cap.  The product engine rejects 31 and the normal call reports an
# unchanged pre-call root; no modified runtime is a product pin.
probe = out / 'engine-31-coordinator'; shutil.copytree(here.parent / 'coordinator', probe)
p = probe / 'MCEntryCoordinator.sol'
p.write_text(p.read_text().replace('[30]', '[31]').replace('n > 30', 'n > 31'))
env = dict(os.environ, NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules', TMPDIR=str(out / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
with (logs / '31-engine-coordinator-build.log').open('w') as f:
    subprocess.run(['node', str(probe / 'build.js')], cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
probe_art = probe / 'MCEntryCoordinator.json'
probe_keccak = json.loads(probe_art.read_text())['codeHashes']['runtimeKeccak256']
engine_driver = test_driver('engine-31-driver', probe_art, probe_keccak)
w = out / 'world-31-engine'
run('31-engine-atomic-refusal', [engine_driver, 'setup-chain', w, probe_art, engine, fixtures / '31.zip', '4096'], '31')
b = failure(w, 'start-refusal.json')
assert b['selector'] == '0x427cfac5' and words(b) == ['1', '31'] and b['rootUnchanged']; rows['31/engine'] = b

# Exact aggregate byte boundary: 262144 is accepted by the independent coordinator guard
# and must fail honestly inside the pinned engine parser; +1 is refused atomically by the
# coordinator aggregate guard before any engine execution.
w = out / 'world-30-262144'
run('262144-start', [driver, 'setup-chain', w, coord, engine, fixtures / '30-262144.zip', '4096'], '30-262144')
b = failure(w, 'start-refusal.json')
assert b['rootUnchanged'] and b['selector'] in ENGINE_ERRORS.values() and b['selector'] != '0xab23ed08', b['selector']
rows['30/262144-infeasible'] = b
w = out / 'world-30-262145'
run('262145-constructor-refusal', [driver, 'boundary-create', w, coord, engine, fixtures / '30-262145.zip', '4096'], '30-262145')
b = failure(w, 'boundary-refusal.json')
assert b['selector'] == '0xab23ed08' and words(b) == ['12'] and b['rootUnchanged']; rows['30/262145'] = b

# Canonical nested ABI/events/checkpoint/counter/read-range receipts over every successful
# world (independent Node verifier; generated receipts only).
labels = ['world-29-q1', 'world-29-q7', 'world-29-direct', 'world-30-q1', 'world-30-q7', 'world-30-direct']
with (out / 'canonical-receipts.json').open('w') as f:
    p = subprocess.run(['node', str(here / 'verify_receipts.js'), str(build), str(out), '1', *labels],
                       cwd=root, env=node_env, stdout=f, stderr=subprocess.STDOUT)
assert p.returncode == 0, 'canonical receipt verifier'
receipts = json.loads((out / 'canonical-receipts.json').read_text()); assert receipts['verifiedReceipts'] > 0
rows['canonicalReceipts'] = receipts['verifiedReceipts']
summary = {'profile': 'MC-CLASSCOUNT30-PREFLIGHT1', 'generatedOnly': True, 'results': rows, 'commands': commands,
           'wholeGateSeconds': time.monotonic() - start}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
