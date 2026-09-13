#!/usr/bin/env python3
"""Archive allowlisted generated-only Boolean evidence; omit binaries and LevelDB."""
from pathlib import Path
import hashlib, json, shutil, sys, tarfile
here=Path(__file__).resolve().parent
build, smoke, monitor=map(lambda x:Path(x).resolve(),sys.argv[1:4])
assert build.name.startswith('java-diff-mc-boolean-') and smoke.name.startswith('java-diff-mc-boolean-')
stamp=build.name.removeprefix('java-diff-mc-boolean-').removesuffix('-build')
out=here/('run-'+stamp); assert not out.exists(); out.mkdir()
stage=out/'allowlisted'; stage.mkdir()
def copy(src, dst=None):
    src=Path(src); dst=stage/(dst or src.name); dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir(): shutil.copytree(src,dst)
    else: shutil.copy2(src,dst)
# Reproducible source-build products, with Go preserved as source evidence only.
for n in ('engine','coordinator','bootstrap-classes'): copy(build/n,Path('build')/n)
for n in ('strip-platform.log','java8-build.log','javap.log','engine-build.log','coordinator-build.log','gofmt.log','go-build.log','go-vet.log','pins.json'):
    copy(build/n,Path('build')/n)
copy(build/'main.go',Path('build/executed_driver.go.txt'))
# Generated fixture classes/resources, host logs, all receipt JSON/logs, and opaque
# checkpoints/Heads. Deliberately never copy any `state` LevelDB tree or Go binary.
copy(smoke/'classes',Path('smoke/classes'))
for p in smoke.iterdir():
    if p.is_file(): copy(p,Path('smoke')/p.name)
copy(smoke/'reports',Path('smoke/reports'))
for world in [p for p in smoke.iterdir() if p.is_dir() and (p/'checkpoints').is_dir()]:
    copy(world/'checkpoints',Path('smoke/worlds')/world.name/'checkpoints')
    for n in ('durable-head.json','STORE-FORMAT'):
        if (world/n).is_file(): copy(world/n,Path('smoke/worlds')/world.name/n)
copy(monitor,Path('monitor.json'))
# The explicit scan is stricter than the source-independent allowlist above.
for p in stage.rglob('*'):
    assert 'state' not in p.parts and not p.name.endswith(('.ldb','.sst')) and p.name != 'driver',p
entries=[]
for p in sorted(x for x in stage.rglob('*') if x.is_file()): entries.append({'path':str(p.relative_to(stage)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'archive-files.json').write_text(json.dumps(entries,indent=2)+'\n')
with tarfile.open(out/'generated-artifacts-receipts-checkpoints.tar.gz','w:gz') as t: t.add(stage,arcname='allowlisted')
# The compressed, hashed archive is the durable receipt container; do not retain
# an uncompressed duplicate of the full checkpoint/receipt corpus in Git.
shutil.rmtree(stage)
(out/'SHA256SUMS').write_text('\n'.join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in (out/'archive-files.json',out/'generated-artifacts-receipts-checkpoints.tar.gz'))+'\n')
(out/'README.md').write_text('# Boolean generated-only evidence\n\nSource build, generated classes/resources, full EVM receipts and opaque checkpoints only. The archive excludes Go binaries, LevelDB state, original payloads, pages, and original-JAR execution.\n')
print(json.dumps({'archive':str(out),'files':len(entries),'tarBytes':(out/'generated-artifacts-receipts-checkpoints.tar.gz').stat().st_size},indent=2))
