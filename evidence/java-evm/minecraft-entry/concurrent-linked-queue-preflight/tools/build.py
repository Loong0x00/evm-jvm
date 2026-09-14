#!/usr/bin/env python3
"""Reproducible LOCAL384 build for the bounded queue bootstrap append."""
from pathlib import Path
import json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-concurrent-linked-queue-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules',PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
    with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run('source-verification',[sys.executable,here/'verify_source.py'])
for part in ('engine','coordinator'):
    shutil.copytree(stage/part,out/part)
    run(part+'-build',['node',out/part/'build.js'])
pins=json.loads((stage/'pins.json').read_text())
for part,name,key in (('engine','MCEntryInterpreter','engine'),('coordinator','MCEntryCoordinator','coordinator')):
    art=json.loads((out/part/(name+'.json')).read_text()); got={'bytes':len(art['deployedBytecode'])//2,**art['codeHashes']}
    assert got==pins[key],(key,got,pins[key])
shutil.copy2(stage/'tools/Go.txt',out/'main.go'); run('gofmt',['gofmt','-w',out/'main.go']); run('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']); run('go-vet',['go','vet',out/'main.go'])
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'build':str(out),'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
