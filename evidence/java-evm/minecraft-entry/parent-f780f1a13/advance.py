#!/usr/bin/env python3
"""Bounded additional observations using only same-code successful checkpoints."""
import json,os,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[3];worlds=Path(sys.argv[1]).resolve();build=Path(sys.argv[2]).resolve();jar=Path(sys.argv[3]).resolve()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
for n in range(2,10):
 out=worlds/('continuation-'+str(n));assert not out.exists()
 subprocess.run([sys.executable,str(here/'continue.py'),str(worlds),'official',str(out),str(jar),str(build)],env=env,check=True)
 m=json.loads((worlds/'official/durable-head.json').read_text())
 if (out/'refusal.json').exists() or m['lifecycle']!=1:break
else:raise AssertionError('4096 additional observation bound reached; inspect before extending')
subprocess.run(['node',str(here/'verify_original.js'),str(worlds),'official',str(build)],env=env,check=True)
