#!/usr/bin/env python3
"""Build deterministic trusted fixture ZIPs; never reads an external archive."""
import sys, zipfile
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
def emit(name, payload):
    zi=zipfile.ZipInfo(name, (1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED
    zi.external_attr=0o100644 << 16; zi.create_system=3
    with zipfile.ZipFile(out/(name.replace('.class','')+'.zip'),'w') as z: z.writestr(zi,payload)
for n in ('BridgeAlpha','BridgeBeta'):
    emit(n+'.class',(root/(n+'.class')).read_bytes())
# Correct archive binding but mismatched declared this_class.
emit('BridgeAlias.class',(root/'BridgeAlpha.class').read_bytes())
# Deterministic malformed class: corrupt CAFEBABE while preserving ZIP CRC metadata.
b=bytearray((root/'BridgeAlpha.class').read_bytes()); b[0]^=0xff
emit('BridgeMalformed.class',bytes(b))
