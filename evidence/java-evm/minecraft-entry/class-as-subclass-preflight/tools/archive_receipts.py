#!/usr/bin/env python3
"""Copy only durable receipts/checkpoints; deliberately never copy LevelDB state."""
from pathlib import Path
import shutil,sys
src=Path(sys.argv[1]).resolve();dst=Path(sys.argv[2]).resolve()
labels=sys.argv[3:]
assert not dst.exists(); dst.mkdir(parents=True)
for label in labels:
    world=src/label
    if not world.exists(): world=src/('world-'+label)
    report=src/'reports'/world.name; out=dst/label; out.mkdir()
    for name in ('durable-head.json','STORE-FORMAT'):
        if (world/name).exists(): shutil.copy2(world/name,out/name)
    shutil.copytree(world/'checkpoints',out/'checkpoints')
    shutil.copytree(report,out/'reports')
    assert not (out/'state').exists()
(dst/'README.txt').write_text('Durable checkpoint blobs and public EVM receipt JSON only. No LevelDB/state directory or Go binary.\n')
