#!/usr/bin/env python3
"""Reconstruct a fresh isolated COPY, apply only selected-table.patch, and compile it."""
from pathlib import Path
import os, subprocess, sys
root=Path(__file__).resolve().parents[4]
out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-owncapacity-selected-') and not out.exists(), out
subprocess.run([sys.executable, str(Path(__file__).with_name('reconstruct_selected_copy.py')), str(out)], cwd=root, check=True)
source=out/'selectedvfsassets'/'VFS0aInterpreter.sol'
subprocess.run(['patch','--batch','--forward',str(source),str(Path(__file__).with_name('selected-table.patch'))], cwd=root, check=True)
env=dict(os.environ, TMPDIR=str(out/'tmp'))
with (out/'selected-vfs-build.log').open('w') as log:
    subprocess.run(['node',str(out/'selectedvfsassets'/'build.js')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
