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
assert OUT.parent == ROOT / 'build' and OUT.name.startswith('java-diff-mc-math-double-min-max-')
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

# The edges are an intentionally small q1 witness for every IEEE-754 class
# relevant to Math.min/max, including signed zeros and raw NaN payload order.
POS_ZERO, NEG_ZERO = 0x0000000000000000, 0x8000000000000000
POS_INF, NEG_INF = 0x7ff0000000000000, 0xfff0000000000000
POS_QNAN, NEG_QNAN = 0x7ff8000000000001, 0xfff8000000001234
POS_SNAN, NEG_SNAN = 0x7ff0000000000001, 0xfff0000000000002
POS_MAX, NEG_MAX = 0x7fefffffffffffff, 0xffefffffffffffff
POS_MIN_NORMAL, NEG_MIN_NORMAL = 0x0010000000000000, 0x8010000000000000
POS_MAX_SUB, NEG_MAX_SUB = 0x000fffffffffffff, 0x800fffffffffffff
POS_MIN_SUB, NEG_MIN_SUB = 0x0000000000000001, 0x8000000000000001
ONE, NEG_ONE = 0x3ff0000000000000, 0xbff0000000000000
edge_pairs = [
    (POS_ZERO, POS_ZERO), (NEG_ZERO, NEG_ZERO), (POS_ZERO, NEG_ZERO), (NEG_ZERO, POS_ZERO),
    (POS_QNAN, ONE), (ONE, POS_QNAN), (NEG_QNAN, POS_QNAN),
    (POS_SNAN, ONE), (ONE, NEG_SNAN),
    (NEG_INF, POS_INF), (POS_INF, POS_MAX), (NEG_MAX, NEG_INF),
    (POS_INF, POS_INF), (NEG_INF, NEG_INF),
    (POS_MIN_SUB, POS_ZERO), (NEG_MIN_SUB, POS_ZERO),
    (POS_MAX_SUB, POS_MIN_NORMAL), (NEG_MAX_SUB, NEG_MIN_NORMAL),
    (POS_MIN_NORMAL, POS_MAX), (NEG_MIN_NORMAL, NEG_MAX),
    (NEG_ONE, ONE), (ONE, ONE), (POS_MIN_SUB, NEG_MIN_SUB), (NEG_QNAN, ONE),
]
import random
rng = random.Random(0x4d415448444f5542)
random_pairs = [(rng.getrandbits(64), rng.getrandbits(64)) for _ in range(256)]
template = (src / 'MathDoubleMinMax.template').read_text()
generated_src = OUT / 'generated-fixture-src'
generated_src.mkdir()
math_inputs = {'MathDoubleMinMaxEdges': edge_pairs, 'MathDoubleMinMaxRandom': random_pairs}
for class_name, pairs in math_inputs.items():
    flat = ', '.join(f'0x{bits:016x}L' for pair in pairs for bits in pair)
    source = template.replace('__CLASS_NAME__', class_name).replace('__RAW_PAIR_BITS__', flat)
    (generated_src / f'{class_name}.java').write_text(source)

oracle_src = OUT / 'oracle-src'
oracle_classes = OUT / 'oracle-classes'
oracle_src.mkdir(); oracle_classes.mkdir()
oracle_java = oracle_src / 'MathDoubleMinMaxOracle.java'
oracle_java.write_text('''public final class MathDoubleMinMaxOracle {\n  public static void main(String[] pairs) {\n    for (String pair : pairs) {\n      int comma = pair.indexOf(',');\n      long left = Long.parseUnsignedLong(pair.substring(0, comma), 16);\n      long right = Long.parseUnsignedLong(pair.substring(comma + 1), 16);\n      double a = Double.longBitsToDouble(left);\n      double b = Double.longBitsToDouble(right);\n      long min = Double.doubleToRawLongBits(Math.min(a, b));\n      long max = Double.doubleToRawLongBits(Math.max(a, b));\n      System.out.println(Long.toHexString(min) + ':' + Long.toHexString(max));\n    }\n  }\n}\n''')
run([JAVAC, '-g:none', '-source', '8', '-target', '8', '-d', oracle_classes, oracle_java])

sources = sorted(p for p in src.glob('*.java')) + sorted(generated_src.glob('*.java'))
filler_src = OUT / 'filler-src'
filler_src.mkdir()
for i in range(150):
    (filler_src / f'Local1MFiller{i:02d}.java').write_text(
        f'public final class Local1MFiller{i:02d} {{ public int value() {{ return {i}; }} }}\n')
run([JAVAC, '-g:none', '-source', '8', '-target', '8', '-d', classes, *sources,
     *sorted(filler_src.glob('*.java'))])

# Compile only the attempted raw platform replacements against Java 8 boot
# images with those platform names removed; neither replacement is run on host.
stripped = OUT / 'replacement-rt.jar'
shutil.copyfile(RTJAR, stripped)
run(['zip', '-q', '-d', stripped, 'java/util/ArrayList.class', 'java/util/IdentityHashMap.class', 'java/lang/Math.class'])
replacement_out = OUT / 'replacement-classes'
replacement_out.mkdir()
run([JAVAC, '-g:none', '-bootclasspath', stripped, '-source', '8', '-target', '8',
     '-d', replacement_out, src / 'replacement/java/util/ArrayList.java',
     src / 'replacement/java/util/IdentityHashMap.java', src / 'replacement/java/lang/Math.java'])
replacement_bytes = (replacement_out / 'java/util/ArrayList.class').read_bytes()
identity_replacement_bytes = (replacement_out / 'java/util/IdentityHashMap.class').read_bytes()
math_replacement_bytes = (replacement_out / 'java/lang/Math.class').read_bytes()

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
            try:
                rel = path.relative_to(replacement_out).as_posix()
            except ValueError:
                rel = path.name
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
array_required = [
    'ArrayListMatrix', 'ArrayListNegativeMinusOne', 'ArrayListNegativeMin',
    'ArrayListUnboundAddConcrete', 'ArrayListUnboundAddInterface',
    'ArrayListUnboundIteratorConcrete', 'ArrayListUnboundIteratorInterface',
    'ArrayListMissingDefaultConstructor', 'ArrayListMathObjectInteger',
    'ArrayListPackedSparse', 'ArrayListQuotaBoundary', 'ArrayListQuotaOOM', 'ArrayListRawReplacementMain',
]
identity_required = [
    'IdentityHashMapMatrix', 'IdentityHashMapNegativeMinusOne', 'IdentityHashMapNegativeMin',
    'IdentityHashMapMaximumControl', 'IdentityHashMapArrayQuotaControl', 'IdentityHashMapUnboundPutConcrete',
    'IdentityHashMapUnboundPutInterface', 'IdentityHashMapUnboundGetInterface',
    'IdentityHashMapUnboundEqualsObject', 'IdentityHashMapUnboundHashCodeObject',
    'IdentityHashMapUnboundDefaultMethod', 'IdentityHashMapUnboundViews',
    'IdentityHashMapMissingDefaultConstructor', 'IdentityHashMapRawReplacementMain',
]
math_required = ['MathDoubleMinMaxEdges', 'MathDoubleMinMaxRandom']
required = array_required + identity_required + math_required
assert all(n in by_name for n in required + ['MathAbsUnsupported', 'MathRawReplacementMain']), sorted(by_name)
manifest = {'schema': 1, 'jdk': run([JAVAC, '-version']).stdout.strip(), 'cases': {}}
for name in required:
    p = by_name[name]
    manifest['cases'][name] = write_bundle(name, [p])

# Raw-name replacement check must precede ordinary classes only to ensure the
# reserved name is actually present in the attempted raw bundle.
manifest['cases']['raw-platform-replacement'] = write_bundle(
    'raw-platform-replacement', [by_name['ArrayListRawReplacementMain'], replacement_out / 'java/util/ArrayList.class'])
manifest['cases']['identity-map-raw-platform-replacement'] = write_bundle(
    'identity-map-raw-platform-replacement',
    [by_name['IdentityHashMapRawReplacementMain'], replacement_out / 'java/util/IdentityHashMap.class'])
manifest['cases']['math-raw-platform-replacement'] = write_bundle(
    'math-raw-platform-replacement',
    [by_name['MathRawReplacementMain'], replacement_out / 'java/lang/Math.class'])
manifest['cases']['math-abs-unsupported'] = write_bundle(
    'math-abs-unsupported', [by_name['MathAbsUnsupported']])
fillers = [classes / f'Local1MFiller{i:02d}.class' for i in range(150)]
assert all(p.is_file() for p in fillers)
raw150_files = [by_name['ArrayListMatrix'], *fillers[:149]]
raw151_files = [by_name['ArrayListMatrix'], *fillers[:150]]
manifest['cases']['raw150-envelope'] = write_bundle('raw150-envelope', raw150_files)
manifest['cases']['raw151-refusal'] = write_bundle('raw151-refusal', raw151_files)

base_matrix = by_name['ArrayListMatrix'].read_bytes()
assert parse_class_end(base_matrix)[3] == len(base_matrix)
# Keep every generated resource within DI0's independent 262,144-byte decoder
# output limit while exercising the aggregate engine/coordinator raw envelope.
other_bytes = sum(p.stat().st_size for p in raw150_files[4:])
target_total = 1063930 - other_bytes
base_target, remainder = divmod(target_total, 4)
exact_overrides = {}
for i, path in enumerate(raw150_files[:4]):
    relative = path.relative_to(classes).as_posix()
    target = base_target + (1 if i < remainder else 0)
    assert target <= 262144, (relative, target)
    exact_overrides[relative] = padded_to(path.read_bytes(), target)
overrides_plus_one = dict(exact_overrides)
first_name = raw150_files[0].relative_to(classes).as_posix()
first_exact = exact_overrides[first_name]
overrides_plus_one[first_name] = padded_to(base_matrix, len(first_exact) + 1)
manifest['cases']['raw-bytes-exact'] = write_bundle(
    'raw-bytes-exact', raw150_files, override=exact_overrides)
manifest['cases']['raw-bytes-over'] = write_bundle(
    'raw-bytes-over', raw150_files, override=overrides_plus_one)
assert manifest['cases']['raw-bytes-exact']['rawCount'] == 150
assert manifest['cases']['raw-bytes-exact']['rawBytes'] == 1063930
assert max(x['bytes'] for x in manifest['cases']['raw-bytes-exact']['rawClasses']) <= 262144
assert manifest['cases']['raw-bytes-over']['rawBytes'] == 1063931

bad = bytearray(base_matrix); bad[0] ^= 0xff
manifest['cases']['malformed-classfile'] = write_bundle(
    'malformed-classfile', [by_name['ArrayListMatrix']], override={'ArrayListMatrix.class': bytes(bad)})
manifest['cases']['malformed-classfile']['entryClass'] = 'ArrayListMatrix'

# Diagnostic class names/counts are based on actual generated bytes plus the
# append-only 100-image bootstrap; the old first99 image positions are retained.
for key, case in manifest['cases'].items():
    case.setdefault('entryClass', case['rawClasses'][0]['binaryName'])
    # MR01 has a u16 class-count field; this stage's enforced maximum is 250.
    # Over-cap raw151 must refuse before _prepare (its hypothetical count251 is
    # not recorded as an observed diagnostic).
    if case['rawCount'] <= 150:
        case['expectedDiagnosticClassesIfPrepared'] = case['rawCount'] + 100
        assert case['expectedDiagnosticClassesIfPrepared'] <= 250
    else:
        case['expectedDiagnosticClassesIfPrepared'] = None
        case['refusalBeforePrepare'] = True

# Host Java 8 differential oracles run only trusted generated positive and
# negative semantic fixtures. The max-int OOM control is guest-only to avoid a
# host allocation attempt; native-refusal fixtures are not semantic oracles.
host = {}
expected_iae = {'ArrayListNegativeMinusOne', 'ArrayListNegativeMin',
                'IdentityHashMapNegativeMinusOne', 'IdentityHashMapNegativeMin'}
expected_ok = (set(array_required) | {'IdentityHashMapMatrix'} | set(math_required)) - expected_iae
for name in sorted(expected_ok):
    p = run([JAVA, '-cp', classes, name], check=False)
    if p.returncode != 0:
        raise RuntimeError(f'host oracle failed for {name}: exit={p.returncode}\n{p.stdout}')
    host[name] = {'exit': p.returncode, 'expectation': 'normal-return'}
math_oracle_cases = {}
for name, pairs in math_inputs.items():
    args = [f'{left:016x},{right:016x}' for left, right in pairs]
    oracle = run([JAVA, '-cp', oracle_classes, 'MathDoubleMinMaxOracle', *args])
    lines = oracle.stdout.splitlines()
    if len(lines) != len(pairs):
        raise RuntimeError(f'Java 8 Math raw-bit oracle returned {len(lines)} rows for {name}, expected {len(pairs)}')
    actual = []
    for line in lines:
        min_bits, max_bits = line.split(':')
        actual.extend((min_bits.zfill(16), max_bits.zfill(16)))
    math_oracle_cases[name] = {
        'pairCount': len(pairs),
        'inputPairsRaw64': [[f'{left:016x}', f'{right:016x}'] for left, right in pairs],
        'expectedRawResults': actual,
        'oracle': 'read-only local Java 8 java.lang.Math.min/max and Double.raw-bit conversions; never included in EVM bundle',
    }
for name in sorted(expected_iae):
    p = run([JAVA, '-cp', classes, name], check=False)
    if p.returncode == 0 or 'java.lang.IllegalArgumentException' not in p.stdout:
        raise RuntimeError(f'host oracle did not throw IllegalArgumentException for {name}: {p.stdout}')
    host[name] = {'exit': p.returncode, 'expectation': 'java.lang.IllegalArgumentException'}
# The padded exact-limit class is still a valid Java classfile with an ignored
# attribute; run it as a host-side format oracle, then retain the input bytes.
padded_host = OUT / 'padded-host'
padded_host.mkdir()
for p in raw150_files:
    rel = p.relative_to(classes).as_posix()
    data = exact_overrides.get(rel, p.read_bytes())
    (padded_host / p.name).write_bytes(data)
p = run([JAVA, '-cp', padded_host, 'ArrayListMatrix'], check=False)
if p.returncode != 0:
    raise RuntimeError(f'exact-size generated classfile host oracle failed: {p.stdout}')
host['raw-bytes-exact'] = {'exit': p.returncode, 'expectation': 'valid-classfile-ignored-attribute'}

# Independent Java 8 oracle: report the actual private table array length from
# the local JDK runtime by reflection; no expected table formula is embedded.
capacity_oracle_src = OUT / 'capacity-oracle-src'
capacity_oracle_classes = OUT / 'capacity-oracle-classes'
capacity_oracle_src.mkdir(); capacity_oracle_classes.mkdir()
oracle_java = capacity_oracle_src / 'IdentityHashMapCapacityOracle.java'
oracle_java.write_text('''import java.lang.reflect.Field;\nimport java.util.IdentityHashMap;\npublic final class IdentityHashMapCapacityOracle {\n  public static void main(String[] args) throws Exception {\n    Field table = IdentityHashMap.class.getDeclaredField("table");\n    table.setAccessible(true);\n    for (String arg : args) {\n      int n = Integer.parseInt(arg);\n      IdentityHashMap<Object,Object> map = new IdentityHashMap<Object,Object>(n);\n      Object[] slots = (Object[]) table.get(map);\n      System.out.println(n + "=" + slots.length + ":" + map.size() + ":" + map.isEmpty());\n    }\n  }\n}\n''')
run([JAVAC, '-g:none', '-source', '8', '-target', '8', '-d', capacity_oracle_classes, oracle_java])
capacity_values = [0, 1, 2, 3, 10, 21, 512, 1024, 21845]
oracle_run = run([JAVA, '-cp', capacity_oracle_classes, 'IdentityHashMapCapacityOracle',
                  *map(str, capacity_values)])
capacity_oracle = {}
for line in oracle_run.stdout.splitlines():
    key, rest = line.split('=', 1)
    table_len, size, empty = rest.split(':')
    capacity_oracle[key] = {'tableLength': int(table_len), 'size': int(size), 'isEmpty': empty == 'true'}
if set(map(int, capacity_oracle)) != set(capacity_values):
    raise RuntimeError(f'Java 8 reflection oracle returned wrong capacity set: {capacity_oracle}')
if any(row['size'] != 0 or not row['isEmpty'] for row in capacity_oracle.values()):
    raise RuntimeError(f'Java 8 reflection oracle found non-empty new maps: {capacity_oracle}')

manifest['hostOracles'] = host
manifest['mathDoubleMinMaxOracle'] = {'cases': math_oracle_cases}
manifest['identityHashMapCapacityOracle'] = {
    'runtime': 'local Java 8 IdentityHashMap private table reflection; test-only',
    'rows': capacity_oracle,
}
manifest['replacementClass'] = {'binaryName': 'java.util.ArrayList', 'bytes': len(replacement_bytes),
                                'sha256': sha(replacement_bytes), 'execution': 'not executed on host'}
manifest['identityHashMapReplacementClass'] = {
    'binaryName': 'java.util.IdentityHashMap', 'bytes': len(identity_replacement_bytes),
    'sha256': sha(identity_replacement_bytes), 'execution': 'not executed on host'}
manifest['mathReplacementClass'] = {
    'binaryName': 'java.lang.Math', 'bytes': len(math_replacement_bytes),
    'sha256': sha(math_replacement_bytes), 'execution': 'not executed on host'}
manifest['capacityMatrix'] = capacity_values
manifest['limits'] = {'rawClasses': 150, 'rawBytes': 1063930, 'diagnosticClasses': 250,
                      'maxJvmSteps': 65536, 'maxInternalSteps': 4096,
                      'ordinaryGas': 1000000000, 'runtimeCapBytes': 1048576,
                      'checkpointCapBytes': 1048576}
manifest['sourceHashes'] = {p.relative_to(STAGE).as_posix(): sha(p.read_bytes())
                            for p in sorted(src.rglob('*.java'))}
manifest['sourceHashes'][(src / 'MathDoubleMinMax.template').relative_to(STAGE).as_posix()] = \
    sha((src / 'MathDoubleMinMax.template').read_bytes())
manifest['generatedFixtureSourceHashes'] = {
    p.name: sha(p.read_bytes()) for p in sorted(generated_src.glob('*.java'))
}
manifest['oracleSourceSHA256'] = sha(oracle_java.read_bytes())
manifest['fixtureClassHashes'] = {p.relative_to(classes).as_posix(): sha(p.read_bytes())
                                  for p in sorted(classes.rglob('*.class'))}
(OUT / 'fixture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'manifest': str(OUT / 'fixture-manifest.json'),
                  'cases': len(manifest['cases']), 'raw150Count': manifest['cases']['raw150-envelope']['rawCount'],
                  'raw150Bytes': manifest['cases']['raw150-envelope']['rawBytes'],
                  'exactBytes': manifest['cases']['raw-bytes-exact']['rawBytes'],
                  'overBytes': manifest['cases']['raw-bytes-over']['rawBytes'],
                  'raw151Count': manifest['cases']['raw151-refusal']['rawCount'],
                  'diagnosticClassMaximum': 250,
                  'hostOracleCases': len(host)}, indent=2))
