#!/usr/bin/env python3
"""Reproducible LOCAL384 cap30 build; output is ignored and contains no original input."""
from pathlib import Path
import json, os, shutil, subprocess, sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / 'build' and out.name.startswith('java-diff-mc-classcount30-') and not out.exists()
out.mkdir(); (out / 'tmp').mkdir()
node = '/home/user/evm-jvm/geth/jvmevm/runtime/node_modules'; assert Path(node).is_dir()
env = dict(os.environ, TMPDIR=str(out / 'tmp'), NODE_PATH=node, PYTHONDONTWRITEBYTECODE='1')


def run(name, args):
    with (out / (name + '.log')).open('w') as f:
        subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)


run('stage-engine', [sys.executable, here / 'stage.py'])
shutil.copytree(stage / 'engine', out / 'engine')
run('engine-build', ['node', out / 'engine/build.js'])
run('stage-coordinator', [sys.executable, here / 'stage.py', '--engine-json', out / 'engine/MCEntryInterpreter.json'])
shutil.copytree(stage / 'coordinator', out / 'coordinator')
run('coordinator-build', ['node', out / 'coordinator/build.js'])
run('stage-driver', [sys.executable, here / 'stage.py', '--engine-json', out / 'engine/MCEntryInterpreter.json',
                     '--coordinator-json', out / 'coordinator/MCEntryCoordinator.json'])
shutil.copy2(stage / 'tools/Go.txt', out / 'main.go')
run('gofmt', ['gofmt', '-w', out / 'main.go'])
run('go-build', ['go', 'build', '-trimpath', '-o', out / 'driver', out / 'main.go'])
run('go-vet', ['go', 'vet', out / 'main.go'])

pins = json.loads((stage / 'pins.json').read_text())
for kind, name, key in (('engine', 'MCEntryInterpreter', 'engine'), ('coordinator', 'MCEntryCoordinator', 'coordinator')):
    a = json.loads((out / kind / (name + '.json')).read_text())
    got = {'bytes': len(a['deployedBytecode']) // 2, **a['codeHashes']}
    assert got == pins[key], (key, got, pins[key])
(out / 'pins.json').write_text(json.dumps(pins, indent=2) + '\n')
print(json.dumps({'build': str(out), 'engine': pins['engine'], 'coordinator': pins['coordinator']}, indent=2))
