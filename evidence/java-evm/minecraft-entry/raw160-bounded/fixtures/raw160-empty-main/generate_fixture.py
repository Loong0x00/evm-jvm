#!/usr/bin/env python3
"""Rebuild trusted Java 8 raw-class admission fixtures; no host Java execution."""
import hashlib
import json
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
JDK = pathlib.Path('/usr/lib/jvm/java-8-openjdk')
SRC = ROOT / 'src' / 'Raw160Main.java'
CLASSES = ROOT / 'classes'
SINGLE_SRC = ROOT / 'single-src' / 'Raw160Main.java'
SINGLE_CLASSES = ROOT / 'single-classes'


def emit_source(path, count):
    lines = ['public class Raw160Main { public static void main(String[] args) {} }']
    lines.extend(f'class Raw160Aux{i:03d} {{}}' for i in range(1, count))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n')


def compile_one(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(JDK / 'bin/javac'), '-g:none', '-d', str(destination), str(source)], check=True)


def zip_classes(files, target):
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in files:
            archive.write(path, path.name)


emit_source(SRC, 160)
compile_one(SRC, CLASSES)
all_classes = sorted(CLASSES.glob('*.class'), key=lambda p: p.name)
assert len(all_classes) == 160
zip_classes(all_classes, ROOT / 'raw160-classes.zip')
manifest = []
for path in all_classes:
    data = path.read_bytes()
    assert data[6:8] == b'\x00\x34', f'{path.name}: not Java 8 classfile'
    manifest.append({'name': path.stem, 'path': path.name, 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()})
archive = ROOT / 'raw160-classes.zip'
(ROOT / 'fixture-manifest.json').write_text(json.dumps({
    'kind': 'trusted generated Java8 fixture; test-only',
    'compiler': subprocess.check_output([str(JDK / 'bin/javac'), '-version'], stderr=subprocess.STDOUT, text=True).strip(),
    'flags': ['-g:none'], 'classes': manifest, 'zipBytes': archive.stat().st_size,
    'zipSHA256': hashlib.sha256(archive.read_bytes()).hexdigest(),
}, indent=2) + '\n')
(ROOT / 'bindings.csv').write_text(','.join(['Raw160Main.class'] + [f'Raw160Aux{i:03d}.class' for i in range(1, 160)]) + '\n')
for count in (150, 151):
    (ROOT / f'bindings-{count}.csv').write_text(
        ','.join(['Raw160Main.class'] + [f'Raw160Aux{i:03d}.class' for i in range(1, count)]) + '\n')
emit_source(SINGLE_SRC, 1)
compile_one(SINGLE_SRC, SINGLE_CLASSES)
single = SINGLE_CLASSES / 'Raw160Main.class'
zip_classes([single], ROOT / 'single.zip')
(ROOT / 'single-bindings.csv').write_text('Raw160Main.class\n')
print(f'generated {len(all_classes)} Java8 classes; raw bytes={sum(p.stat().st_size for p in all_classes)}')
