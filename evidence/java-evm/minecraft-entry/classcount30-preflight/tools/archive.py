#!/usr/bin/env python3
"""Archive reproducible cap30 build/gate evidence under artifacts/ with hashes.

Inputs are ignored build directories; only public generated evidence is copied.
No original Minecraft artifact, JAR, class or world is read or produced.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

here = Path(__file__).resolve().parent
stage = here.parent
art = stage / 'artifacts'
build = Path(sys.argv[1]).resolve()
gate = Path(sys.argv[2]).resolve()
regress = Path(sys.argv[3]).resolve()
assert build.name.startswith('java-diff-mc-classcount30-') and gate.name.startswith('java-diff-mc-classcount30-')

for d in ('engine', 'coordinator', 'fixtures', 'heads', 'logs'):
    (art / d).mkdir(parents=True, exist_ok=True)
for n in ('MCEntryInterpreter.abi.json', 'MCEntryInterpreter.init.hex', 'MCEntryInterpreter.json', 'MCEntryInterpreter.runtime.hex'):
    shutil.copy2(build / 'engine' / n, art / 'engine' / n)
for n in ('MCEntryCoordinator.abi.json', 'MCEntryCoordinator.init.hex', 'MCEntryCoordinator.json', 'MCEntryCoordinator.runtime.hex'):
    shutil.copy2(build / 'coordinator' / n, art / 'coordinator' / n)
for p in sorted((Path(sys.argv[4]).resolve()).glob('*.json')):
    shutil.copy2(p, art / 'fixtures' / p.name)
for w in sorted(gate.glob('world-*')):
    shutil.copy2(w / 'durable-head.json', art / 'heads' / (w.name + '.json'))
for p in sorted((gate / 'logs').glob('*.json')):
    shutil.copy2(p, art / 'logs' / p.name)
shutil.copy2(gate / 'summary.json', art / 'generated-gate-summary.json')
shutil.copy2(gate / 'canonical-receipts.json', art / 'canonical-receipts.json')
shutil.copy2(build / 'pins.json', art / 'build.json')

logs = []
for n in ('stage-engine', 'engine-build', 'stage-coordinator', 'coordinator-build', 'stage-driver', 'gofmt', 'go-build', 'go-vet'):
    if (build / (n + '.log')).exists():
        logs.append('== %s\n%s' % (n, (build / (n + '.log')).read_text()))
(build / 'build.log').write_text(''.join(logs))
shutil.copy2(build / 'build.log', art / 'build.log')
try:
    build_seconds = build.joinpath('go-vet.log').stat().st_mtime - build.joinpath('stage-engine.log').stat().st_mtime
except FileNotFoundError:
    build_seconds = None
(art / 'build.monitor.json').write_text(json.dumps({
    'engineBuildLog': 'engine-build.log', 'wholeBuildSecondsFromLogMtimes': build_seconds,
    'engineBytes': json.loads((art / 'build.json').read_text())['engine']['bytes'],
    'coordinatorBytes': json.loads((art / 'build.json').read_text())['coordinator']['bytes'],
}, indent=2) + '\n')

gate_summary = json.loads((gate / 'summary.json').read_text())
(art / 'gate.monitor.json').write_text(json.dumps({
    'wholeGateSeconds': gate_summary['wholeGateSeconds'],
    'commandCount': len(gate_summary['commands']),
    'results': list(gate_summary['results'].keys()),
}, indent=2) + '\n')
shutil.copy2(Path('/tmp/cap30-gate.out'), art / 'gate.log')

rev = subprocess.run([sys.executable, str(here / 'verify_source.py'), str(build)], capture_output=True, text=True, check=True)
(art / 'reverse-verifier.json').write_text(rev.stdout)

raw = Path('/tmp/cap30-enumset.out').read_text()
shutil.copy2('/tmp/cap30-enumset.out', art / 'logs/enumset-regression.log')
tail = raw[raw.index('{'):]
(art / 'enumset-regression.json').write_text(tail)

files = sorted(p for p in art.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
manifest = []
with (art / 'SHA256SUMS').open('w') as f:
    for p in files:
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.append({'path': str(p.relative_to(art)), 'bytes': p.stat().st_size, 'sha256': h})
        f.write('%s  %s\n' % (h, p.relative_to(art)))
(art / 'manifest.json').write_text(json.dumps({'files': manifest, 'fileCount': len(manifest)}, indent=2) + '\n')
print(json.dumps({'archived': str(art), 'files': len(manifest)}, indent=2))
