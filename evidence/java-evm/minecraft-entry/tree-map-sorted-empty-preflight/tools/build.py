#!/usr/bin/env python3
"""Rebuild the pinned generated TreeMap SortedMap empty evidence."""
from pathlib import Path
import json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;stage=here.parent;root=here.parents[4];out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-tree-map-sorted-empty-build-') and not out.exists()
pins=json.loads((stage/'build-pins.json').read_text());node=root/'jvmevm/runtime/node_modules';assert node.is_dir()
out.mkdir();(out/'tmp').mkdir();env={**os.environ,'TMPDIR':str(out/'tmp'),'NODE_PATH':str(node),'PYTHONDONTWRITEBYTECODE':'1'}
def run(label,cmd):
 with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,cmd)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run('source-verification',[sys.executable,here/'verify_source.py','--built',stage/'build-pins.json'])
for name,contract in (('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')):
 target=out/name;shutil.copytree(stage/name,target)
 for suffix in ('.abi.json','.init.hex','.runtime.hex','.json'):
  (target/(contract+suffix)).unlink(missing_ok=True)
 run(name+'-build',['node',target/'build.js'])
 artifact=json.loads((target/(contract+'.json')).read_text());actual={'bytes':len(artifact['deployedBytecode'])//2,**artifact['codeHashes']}
 assert actual==pins[name],(name,actual,pins[name])
main=out/'main.go';shutil.copy2(stage/'tools/Go.txt',main)
for label,cmd in (('gofmt',['gofmt','-w',main]),('go-build',['go','build','-trimpath','-o',out/'driver',main]),('go-vet',['go','vet',main])):run(label,cmd)
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'build':str(out),'engine':pins['engine'],'coordinator':pins['coordinator']},indent=2))
