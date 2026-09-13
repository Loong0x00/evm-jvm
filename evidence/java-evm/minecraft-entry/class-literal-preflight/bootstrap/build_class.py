#!/usr/bin/env python3
"""TEST-only reproducible Java 8 source -> pinned java/lang/Class bootstrap."""
import hashlib, pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]) if len(sys.argv)==2 else root/'generated-class'
if out.exists(): raise SystemExit('refuse existing output')
classes=out/'classes'; classes.mkdir(parents=True)
subprocess.run(['javac','--release','8','-g:none','-d',str(classes),str(root/'java/lang/Class.java')],check=True)
got=(classes/'java/lang/Class.class').read_bytes(); want=(root/'java/lang/Class.class').read_bytes()
if got != want: raise SystemExit('Class.class differs from pinned bootstrap image')
print(hashlib.sha256(got).hexdigest())
