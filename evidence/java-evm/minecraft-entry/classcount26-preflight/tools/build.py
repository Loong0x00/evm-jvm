#!/usr/bin/env python3
"""Reproducible LOCAL384 build; output is ignored and contains no original input."""
from pathlib import Path
import json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-classcount26-') and not out.exists()
out.mkdir();(out/'tmp').mkdir()
node='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules'; assert Path(node).is_dir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=node,PYTHONDONTWRITEBYTECODE='1')
for kind,name in (('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')):
 d=out/kind;shutil.copytree(stage/kind,d)
 with (out/(kind+'-build.log')).open('w') as f: subprocess.run(['node',str(d/'build.js')],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
# Pins are source/artifact commitments, never substituted from an old engine.
pins=json.loads((stage/'pins.json').read_text())
for kind,name,key in (('engine','MCEntryInterpreter','engine'),('coordinator','MCEntryCoordinator','coordinator')):
 a=json.loads((out/kind/(name+'.json')).read_text()); got={'bytes':len(a['deployedBytecode'])//2,**a['codeHashes']};assert got==pins[key],(key,got,pins[key])
main=out/'main.go';shutil.copy2(stage/'tools/Go.txt',main)
for cmd in (['gofmt','-w',str(main)],['go','build','-trimpath','-o',str(out/'driver'),str(main)],['go','vet',str(main)]): subprocess.run(cmd,cwd=root,env=env,check=True)
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'build':str(out),'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
