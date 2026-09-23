#!/usr/bin/env python3
"""Reproducibly build the bounded generated-only Math.asin candidate."""
from pathlib import Path
import json, os, re, shutil, subprocess, sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
previous=stage.parent/'math-sin-bounded-preparation'; out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-math-asin-build-') and not out.exists()
current=json.loads((previous/'results/generated-gate-v2/build-pins.json').read_text())
# The checked-in coordinator and Go driver retain the historical P1 artifact pins.
source_base=json.loads((previous/'baseline-pins.json').read_text())
node=root/'jvmevm/runtime/node_modules'; assert node.is_dir()
out.mkdir(); (out/'tmp').mkdir()
env={**os.environ,'TMPDIR':str(out/'tmp'),'NODE_PATH':str(node),'PYTHONDONTWRITEBYTECODE':'1'}
def run(label,command):
 with (out/(label+'.log')).open('w') as stream:
  subprocess.run(list(map(str,command)),cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
run('source-invariants',[sys.executable,here/'verify_source.py'])
source_report=json.loads((stage/'results/source-invariants.json').read_text())
q120=subprocess.run([sys.executable,here/'verify_q120.py'],cwd=root,text=True,capture_output=True,check=True,timeout=120)
q120_report=json.loads(q120.stdout)
assert q120_report['supportedRows']==17066 and q120_report['maxBinary64ULPDistanceFromJava8']==1 and q120_report['floatCastBitMismatchCount']==0
engine_dir=out/'engine'; shutil.copytree(stage/'engine',engine_dir); run('engine-build',['node',engine_dir/'build.js'])
engine_artifact=json.loads((engine_dir/'MCEntryInterpreter.json').read_text())
engine_code=bytes.fromhex(engine_artifact['deployedBytecode']); engine={'bytes':len(engine_code),**engine_artifact['codeHashes']}
assert engine['bytes']<=393216
coord_dir=out/'coordinator'; shutil.copytree(stage/'coordinator',coord_dir)
coord_source=coord_dir/'MCEntryCoordinator.sol'; text=coord_source.read_text()
old=source_base['engine']['runtimeKeccak256']; assert text.count(old)==1
coord_source.write_text(text.replace(old,engine['runtimeKeccak256']))
run('coordinator-build',['node',coord_dir/'build.js'])
coord_artifact=json.loads((coord_dir/'MCEntryCoordinator.json').read_text())
coord={'bytes':len(bytes.fromhex(coord_artifact['deployedBytecode'])),**coord_artifact['codeHashes']}
assert coord['bytes']==source_base['coordinator']['bytes']
main=(stage/'tools/Go.txt').read_text()
for old,new in ((source_base['engine']['runtimeSHA256'],engine['runtimeSHA256']),('0x'+source_base['engine']['runtimeKeccak256'],'0x'+engine['runtimeKeccak256']),('0x'+source_base['coordinator']['runtimeKeccak256'],'0x'+coord['runtimeKeccak256'])):
 assert main.count(old)==1,(old,main.count(old)); main=main.replace(old,new)
for pattern in (r'len\(engineRun\) != 383245',r'len\(run\) != 383245'):
 main,count=re.subn(pattern,lambda m:m.group(0).replace('383245',str(engine['bytes'])),main); assert count==1
main_path=out/'main.go'; main_path.write_text(main)
for label,cmd in (('gofmt',['gofmt','-w',main_path]),('go-build',['go','build','-trimpath','-o',out/'driver',main_path]),('go-vet',['go','vet',main_path])):run(label,cmd)
pins=dict(current); pins.update({'phase':'built-math-asin-bounded-profile','baselineStage':'math-sin-bounded-preparation','bootstrapRoot':source_report['bootstrapRoot'],'globalNativeBindings':20,'bootstrapSHA256':dict(current['bootstrapSHA256']),'engine':engine,'coordinator':coord,'math':{'slot':89,'bytes':source_report['mathImageBytes'],'sha256':source_report['mathImageSHA256'],'keccak256':source_report['mathImageKeccak256'],'surface':'prior min/max, native sqrt(D)D + bounded integer sin(D)D + Q120 integer asin(D)D','java8':'javac -source 8 -target 8 -g:none'}})
pins['bootstrapSHA256']['Math']=source_report['mathImageSHA256']
pins.update({'sourceInvariants':source_report,'q120TestOnlyModel':q120_report})
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'build':str(out),'engine':engine,'coordinator':coord,'bootstrapRoot':pins['bootstrapRoot'],'math':pins['math'],'globalNativeBindings':20,'runtimeCap':393216,'oracle':{'supportedRows':q120_report['supportedRows'],'maxULP':q120_report['maxBinary64ULPDistanceFromJava8']}},indent=2))
