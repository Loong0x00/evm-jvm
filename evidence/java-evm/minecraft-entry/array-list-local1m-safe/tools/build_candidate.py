#!/usr/bin/env python3
"""Fresh LOCAL1M build of the frozen minimal ArrayList append, no optimizer/cap tricks."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;STAGE=HERE.parent;ROOT=STAGE.parents[3]
out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-array-list-local1m-') and not out.exists()
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(out/'tmp'),GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
run('source-verification',[sys.executable,HERE/'verify_source.py']);shutil.copytree(STAGE/'engine',out/'engine');run('engine-build',['node',out/'engine/build.js']);a=json.load(open(out/'engine/MCEntryInterpreter.json'));size=len(a['deployedBytecode'])//2;assert size<=1048576
p=json.load(open(STAGE/'pins.json'));assert a['sourceHashes']['MCEntryInterpreter.sol']==p['engineSourceSHA256'];p.update(engine={'bytes':size,**a['codeHashes']},runtimeCap=1048576,runtimeCapBytes=1048576,bootstrapCount=99,status='LOCAL1M compiled; behavioral gates pending');(out/'pins.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'profile':'LOCAL1M','runtimeBytes':size,'runtimeCapBytes':1048576,'engineRuntimeSHA256':a['codeHashes']['runtimeSHA256'],'old97ImagesPreserved':True},indent=2))
