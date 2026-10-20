#!/usr/bin/env python3
"""Generate trusted Java 8 ArrayList probes and exact raw-envelope controls."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
JDK = Path('/usr/lib/jvm/java-8-openjdk')
JAVAC = JDK / 'bin/javac'
JAVA = JDK / 'bin/java'
RTJAR = JDK / 'jre/lib/rt.jar'
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / 'build' and OUT.name.startswith('java-diff-mc-array-list-local1m-')
assert not OUT.exists()
assert JAVAC.is_file() and JAVA.is_file() and RTJAR.is_file()
classes = OUT / 'fixtures'
classes.mkdir(parents=True)
src = STAGE / 'fixtures/src'


def run(args, *, cwd=ROOT, env=None, check=True):
    merged = dict(os.environ, GOPROXY='off', GOSUMDB='off', PYTHONDONTWRITEBYTECODE='1')
    if env:
        merged.update(env)
    p = subprocess.run(list(map(str, args)), cwd=cwd, env=merged,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if check and p.returncode:
        raise RuntimeError(f'command failed ({p.returncode}): {args}\n{p.stdout}')
    return p


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

sources = sorted(p for p in src.glob('*.java'))
filler_src = OUT / 'filler-src'
filler_src.mkdir()
for i in range(75):
    (filler_src / f'Local1MFiller{i:02d}.java').write_text(
        f'public final class Local1MFiller{i:02d} {{ public int value() {{ return {i}; }} }}\n')
run([JAVAC, '-g:none', '-source', '8', '-target', '8', '-d', classes, *sources,
     *sorted(filler_src.glob('*.java'))])

# Compile only the attempted raw java.util.ArrayList replacement against a
# Java 8 boot image without the platform ArrayList; it is never run as authority.
stripped = OUT / 'replacement-rt.jar'
shutil.copyfile(RTJAR, stripped)
run(['zip', '-q', '-d', stripped, 'java/util/ArrayList.class'])
replacement_out = OUT / 'replacement-classes'
replacement_out.mkdir()
run([JAVAC, '-g:none', '-bootclasspath', stripped, '-source', '8', '-target', '8',
     '-d', replacement_out, src / 'replacement/java/util/ArrayList.java'])
replacement_bytes = (replacement_out / 'java/util/ArrayList.class').read_bytes()

# Add one valid unknown class-level attribute to a generated classfile. This
# makes the aggregate raw byte array exactly the pinned envelope boundary.
def u2(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at+2], 'big')

def parse_class_end(data: bytes) -> tuple[int, int, int, int]:
    assert data[:4] == bytes.fromhex('cafebabe')
    cp_count = u2(data, 8)
    at = 10
    i = 1
    while i < cp_count:
        tag = data[at]
        at += 1
        if tag == 1:
            n = u2(data, at); at += 2 + n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; i += 1
        elif tag in (7, 8, 16, 19, 20): at += 2
        elif tag in (9, 10, 11, 12, 17, 18): at += 4
        elif tag == 15: at += 3
        else: raise ValueError(f'unsupported cp tag {tag}')
        i += 1
    cp_end = at
    access = at
    at += 6
    n = u2(data, at); at += 2 + n * 2
    for _ in range(2):
        members = u2(data, at); at += 2
        for _ in range(members):
            at += 6
            attrs = u2(data, at); at += 2
            for _ in range(attrs):
                length = int.from_bytes(data[at+2:at+6], 'big')
                at += 6 + length
    class_attrs_at = at
    attrs = u2(data, at); at += 2
    for _ in range(attrs):
        length = int.from_bytes(data[at+2:at+6], 'big')
        at += 6 + length
    assert at == len(data), (at, len(data))
    return cp_count, cp_end, class_attrs_at, at


def padded_to(data: bytes, target: int) -> bytes:
    cp_count, cp_end, attrs_at, end = parse_class_end(data)
    name = b'Local1MRawEnvelopePadding'
    cp_entry = b'\x01' + len(name).to_bytes(2, 'big') + name
    payload = target - end - len(cp_entry) - 6
    if payload < 0:
        raise ValueError('generated class already exceeds target')
    patched = bytearray(data)
    patched[8:10] = (cp_count + 1).to_bytes(2, 'big')
    patched[cp_end:cp_end] = cp_entry
    # Appending the CP entry shifts the class attribute count by its exact length.
    new_attrs_at = attrs_at + len(cp_entry)
    patched[new_attrs_at:new_attrs_at+2] = (u2(data, attrs_at) + 1).to_bytes(2, 'big')
    patched.extend(cp_count.to_bytes(2, 'big'))
    patched.extend(payload.to_bytes(4, 'big'))
    patched.extend(bytes(payload))
    assert len(patched) == target, (len(patched), target)
    return bytes(patched)


def write_bundle(name: str, files: list[Path], *, override: dict[str, bytes] | None = None):
    override = override or {}
    dest = OUT / 'bundles' / name
    dest.mkdir(parents=True)
    entries = []
    for i, path in enumerate(files):
        try:
            rel = path.relative_to(classes).as_posix()
        except ValueError:
            rel = 'java/util/ArrayList.class'
        data = override.get(rel, path.read_bytes())
        target = dest / f'{i:03d}-{path.name}'
        target.write_bytes(data)
        binary_name = rel[:-6].replace('/', '.')
        entries.append({'index': i, 'binaryName': binary_name, 'file': target.name,
                        'bytes': len(data), 'sha256': sha(data)})
    manifest = {'name': name, 'rawCount': len(entries), 'rawBytes': sum(x['bytes'] for x in entries),
                'rawClasses': entries}
    (dest / 'bundle.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest



by_name = {p.stem: p for p in classes.glob('*.class')}
required = [
    'ArrayListMatrix', 'ArrayListNegativeMinusOne', 'ArrayListNegativeMin',
    'ArrayListUnboundAddConcrete', 'ArrayListUnboundAddInterface',
    'ArrayListUnboundIteratorConcrete', 'ArrayListUnboundIteratorInterface',
    'ArrayListMissingDefaultConstructor', 'ArrayListMathObjectInteger',
    'ArrayListPackedSparse', 'ArrayListQuotaBoundary', 'ArrayListQuotaOOM', 'ArrayListRawReplacementMain',
]
assert all(n in by_name for n in required), sorted(by_name)
manifest = {'schema': 1, 'jdk': run([JAVAC, '-version']).stdout.strip(), 'cases': {}}
for name in required:
    p = by_name[name]
    manifest['cases'][name] = write_bundle(name, [p])

# Raw-name replacement check must precede ordinary classes only to ensure the
# reserved name is actually present in the attempted raw bundle.
manifest['cases']['raw-platform-replacement'] = write_bundle(
    'raw-platform-replacement', [by_name['ArrayListRawReplacementMain'], replacement_out / 'java/util/ArrayList.class'])
fillers = [classes / f'Local1MFiller{i:02d}.class' for i in range(75)]
assert all(p.is_file() for p in fillers)
raw75_files = [by_name['ArrayListMatrix'], *fillers[:74]]
raw76_files = [by_name['ArrayListMatrix'], *fillers[:75]]
manifest['cases']['raw75-envelope'] = write_bundle('raw75-envelope', raw75_files)
manifest['cases']['raw76-refusal'] = write_bundle('raw76-refusal', raw76_files)

base_matrix = by_name['ArrayListMatrix'].read_bytes()
assert parse_class_end(base_matrix)[3] == len(base_matrix)
exact = padded_to(base_matrix, 531965 - sum(p.stat().st_size for p in raw75_files[1:]))
over = padded_to(base_matrix, 531966 - sum(p.stat().st_size for p in raw75_files[1:]))
manifest['cases']['raw-bytes-exact'] = write_bundle(
    'raw-bytes-exact', raw75_files, override={'ArrayListMatrix.class': exact})
manifest['cases']['raw-bytes-over'] = write_bundle(
    'raw-bytes-over', raw75_files, override={'ArrayListMatrix.class': over})
assert manifest['cases']['raw-bytes-exact']['rawBytes'] == 531965
assert manifest['cases']['raw-bytes-over']['rawBytes'] == 531966

bad = bytearray(base_matrix); bad[0] ^= 0xff
manifest['cases']['malformed-classfile'] = write_bundle(
    'malformed-classfile', [by_name['ArrayListMatrix']], override={'ArrayListMatrix.class': bytes(bad)})
manifest['cases']['malformed-classfile']['entryClass'] = 'ArrayListMatrix'

# Diagnostic class names / counts are pinned from actual generated bytes plus
# the exact99-image candidate bootstrap (the root is computed by check_pins.py).
for key, case in manifest['cases'].items():
    case.setdefault('entryClass', case['rawClasses'][0]['binaryName'])
    # This is a preparation-time expectation only. Refusals before _prepare
    # materializes the hierarchy must not be misreported as observed classes.
    case['expectedDiagnosticClassesIfPrepared'] = case['rawCount'] + 99

# Host Java 8 differential oracles use only these generated fixtures.
host = {}
expected_iae = {'ArrayListNegativeMinusOne', 'ArrayListNegativeMin'}
expected_ok = set(required) - expected_iae
for name in sorted(expected_ok):
    p = run([JAVA, '-cp', classes, name], check=False)
    if p.returncode != 0:
        raise RuntimeError(f'host oracle failed for {name}: exit={p.returncode}\n{p.stdout}')
    host[name] = {'exit': p.returncode, 'expectation': 'normal-return'}
for name in sorted(expected_iae):
    p = run([JAVA, '-cp', classes, name], check=False)
    if p.returncode == 0 or 'java.lang.IllegalArgumentException' not in p.stdout:
        raise RuntimeError(f'host oracle did not throw IllegalArgumentException for {name}: {p.stdout}')
    host[name] = {'exit': p.returncode, 'expectation': 'java.lang.IllegalArgumentException'}
# The padded exact-limit class is still a valid Java classfile with an ignored
# attribute; run it as a host-side format oracle, then retain the input bytes.
padded_host = OUT / 'padded-host'
padded_host.mkdir()
for p in raw75_files[1:]: shutil.copyfile(p, padded_host / p.name)
(padded_host / 'ArrayListMatrix.class').write_bytes(exact)
p = run([JAVA, '-cp', padded_host, 'ArrayListMatrix'], check=False)
if p.returncode != 0:
    raise RuntimeError(f'exact-size generated classfile host oracle failed: {p.stdout}')
host['raw-bytes-exact'] = {'exit': p.returncode, 'expectation': 'valid-classfile-ignored-attribute'}

manifest['hostOracles'] = host
manifest['replacementClass'] = {'binaryName': 'java.util.ArrayList', 'bytes': len(replacement_bytes),
                                'sha256': sha(replacement_bytes), 'execution': 'not executed on host'}
manifest['capacityMatrix'] = [0, 1, 3, 10, 1024]
manifest['limits'] = {'rawClasses': 75, 'rawBytes': 531965, 'maxJvmSteps': 65536,
                      'maxInternalSteps': 4096, 'ordinaryGas': 1000000000,
                      'runtimeCapBytes': 1048576}
manifest['sourceHashes'] = {p.relative_to(STAGE).as_posix(): sha(p.read_bytes())
                            for p in sorted(src.rglob('*.java'))}
manifest['fixtureClassHashes'] = {p.relative_to(classes).as_posix(): sha(p.read_bytes())
                                  for p in sorted(classes.rglob('*.class'))}
(OUT / 'fixture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'manifest': str(OUT / 'fixture-manifest.json'),
                  'cases': len(manifest['cases']), 'raw75Count': manifest['cases']['raw75-envelope']['rawCount'],
                  'raw75Bytes': manifest['cases']['raw75-envelope']['rawBytes'],
                  'exactBytes': manifest['cases']['raw-bytes-exact']['rawBytes'],
                  'overBytes': manifest['cases']['raw-bytes-over']['rawBytes'],
                  'hostOracleCases': len(host)}, indent=2))
