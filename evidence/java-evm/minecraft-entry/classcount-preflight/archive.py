#!/usr/bin/env python3
"""Allowlist archival of generated-only receipts; rejects LevelDB/pages/binaries."""
from pathlib import Path
import hashlib,shutil,sys
here=Path(__file__).resolve().parent
build,fixtures,gate=map(lambda x:Path(x).resolve(),sys.argv[1:4])
dst=here/'actual-gate-20260913'; assert not dst.exists(); dst.mkdir()
def cp(src,rel):
    target=dst/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,target)
# Reproducible compiler artifacts/pins and generated fixture package artifacts only.
for kind,name in (('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')):
    for suffix in ('.abi.json','.init.hex','.runtime.hex','.json'):
        cp(build/kind/(name+suffix),Path('artifacts')/kind/(name+suffix))
cp(build/'pins.json','pins.json')
for n in (17,18,24,25):
    cp(fixtures/(str(n)+'.zip'),Path('fixtures')/(str(n)+'.zip'))
    cp(fixtures/(str(n)+'.json'),Path('fixtures')/(str(n)+'.json'))
    for source in sorted((fixtures/'src'/str(n)).glob('*.java')): cp(source,Path('fixtures')/'src'/str(n)/source.name)
# The gate's external process receipts, EVM reports, durable Heads and EVM-issued checkpoints.
cp(gate/'summary.json','summary.json')
for source in sorted((gate/'logs').iterdir()): cp(source,Path('logs')/source.name)
for report in sorted((gate/'reports').rglob('*')):
    if report.is_file(): cp(report,Path('reports')/report.relative_to(gate/'reports'))
for world in sorted(gate.glob('world-*')):
    cp(world/'durable-head.json',Path('worlds')/world.name/'durable-head.json')
    for checkpoint in sorted((world/'checkpoints').glob('*.bin')): cp(checkpoint,Path('worlds')/world.name/'checkpoints'/checkpoint.name)
# Boundary world deliberately has no coordinator/head checkpoint after constructor refusal.
cp(gate/'reports'/'boundary-25'/'boundary25-refusal.json','boundary25-refusal.json')
for bad in dst.rglob('*'):
    assert not any(x in bad.name.lower() for x in ('leveldb','current','manifest','driver')) or bad.suffix in ('.json','.log'),bad
sums=[]
for f in sorted(x for x in dst.rglob('*') if x.is_file()): sums.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(dst)))
(dst/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
print(dst)
