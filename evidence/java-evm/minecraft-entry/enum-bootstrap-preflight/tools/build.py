#!/usr/bin/env python3
"""Reproducible LOCAL384 build for Enum bootstrap82; generated fixtures only."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
out=Path(sys.argv[1]).resolve(); assert out.parent==root/'build' and out.name.startswith('java-diff-mc-enum-bootstrap-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir(); env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
pins=json.loads((stage/'pins.json').read_text()); assert pins['phase']=='source-staged'
run('source-verification',[sys.executable,here/'verify_source.py'])
# Independently rebuild Enum against the exact stripped Java8 platform and compare the embedded input.
api=out/'rt-without-enum.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api); run('strip-enum',['zip','-q','-d',api,'java/lang/Enum.class'])
classes=out/'bootstrap-classes'; classes.mkdir(); run('java8-enum-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath',api,'-d',classes,stage/'bootstrap/java/lang/Enum.java'])
enum=(classes/'java/lang/Enum.class').read_bytes(); assert hashlib.sha256(enum).hexdigest()==pins['bootstrapSHA256']['Enum'] and enum.hex()==(stage/'bootstrap/java/lang/Enum.class.hex').read_text().strip()
run('javap-enum',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-s','-c',classes/'java/lang/Enum.class'])
engine=out/'engine'; shutil.copytree(stage/'engine',engine); run('engine-build',['node',engine/'build.js']); ea=json.loads((engine/'MCEntryInterpreter.json').read_text()); assert len(ea['deployedBytecode'])//2<=pins['runtimeCap']
# A copied coordinator receives exactly the freshly built engine code pin. The staged
# source intentionally retains its accepted-parent placeholder until evidence pins it.
coord=out/'coordinator'; shutil.copytree(stage/'coordinator',coord); cp=coord/'MCEntryCoordinator.sol'; cs=cp.read_text(); cs,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',cs); assert n==1; cp.write_text(cs); run('coordinator-build',['node',coord/'build.js']); ca=json.loads((coord/'MCEntryCoordinator.json').read_text())
# The generated driver is pinned to exactly these two artifacts; the source evidence is
# updated after this monitored build with the same substitutions.
d=(stage/'tools/Go.txt').read_text(); d,n=re.subn(r'const immutableEngineSHA256 = "[0-9a-f]{64}"', 'const immutableEngineSHA256 = "'+ea['codeHashes']['runtimeSHA256']+'"',d); assert n==1
d,n=re.subn(r'const immutableEngineKeccak = "0x[0-9a-f]{64}"', 'const immutableEngineKeccak = "0x'+ea['codeHashes']['runtimeKeccak256']+'"',d); assert n==1
d,n=re.subn(r'const immutableCoordinatorKeccak = "0x[0-9a-f]{64}"', 'const immutableCoordinatorKeccak = "0x'+ca['codeHashes']['runtimeKeccak256']+'"',d); assert n==1
d,n=re.subn(r'len\(engineRun\) != \d+', 'len(engineRun) != '+str(len(ea['deployedBytecode'])//2),d); assert n==2
(out/'main.go').write_text(d)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])): run(label,args)
result={**pins,'phase':'built','engine':{'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}}
(out/'pins.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({'build':str(out),'engine':result['engine'],'coordinator':result['coordinator'],'enumSHA256':pins['bootstrapSHA256']['Enum']},indent=2))
