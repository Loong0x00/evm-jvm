#!/usr/bin/env python3
"""TEST-only reproducible Java 8 platform-map bootstrap pin assertion."""
import hashlib, pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]) if len(sys.argv)==2 else root/'generated-platform-map'
if out.exists(): raise SystemExit('refuse existing output')
classes=out/'classes'; classes.mkdir(parents=True)
sources=[root/'java/lang/Object.java',root/'java/util/Map.java',
 root/'java/util/concurrent/ConcurrentMap.java',root/'java/util/AbstractMap.java',
 root/'java/util/concurrent/ConcurrentHashMap.java']
subprocess.run(['javac','--release','8','-g:none','-d',str(classes),*map(str,sources)],check=True)
for rel in ('java/lang/Object.class','java/util/Map.class','java/util/concurrent/ConcurrentMap.class',
            'java/util/AbstractMap.class','java/util/concurrent/ConcurrentHashMap.class'):
    got=(classes/rel).read_bytes(); want=(root/rel).read_bytes()
    if got != want: raise SystemExit(rel+' differs from pinned bootstrap image')
    print(rel, hashlib.sha256(got).hexdigest())
