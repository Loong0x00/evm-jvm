#!/usr/bin/env python3
"""Reproducibly build the bounded PrintStream.print(char) stage."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
parent=stage.parent/'print-stream-println-string-preflight'
out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-print-stream-print-char-build-') and not out.exists()
node_modules=root/'jvmevm/runtime/node_modules'; assert node_modules.is_dir()
out.mkdir();(out/'tmp').mkdir(); env={**os.environ,'TMPDIR':str(out/'tmp'),'NODE_PATH':str(node_modules),'PYTHONDONTWRITEBYTECODE':'1'}
def run(label,cmd):
 with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,cmd)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def artifact(d,n): return json.loads((d/(n+'.json')).read_text())
def pin(a): return {'bytes':len(a['deployedBytecode'])//2,**a['codeHashes']}
def image_sha(p): return hashlib.sha256(bytes.fromhex(''.join(p.read_text().split()))).hexdigest()
parent_pins=json.loads((parent/'build-pins.json').read_text()); persisted=stage/'build-pins.json'
run('source-verification-prior' if persisted.exists() else 'source-verification-prebuild', [sys.executable,here/'verify_source.py','--built',persisted] if persisted.exists() else [sys.executable,here/'verify_source.py','--prebuild'])
engine_dir=out/'engine';shutil.copytree(stage/'engine',engine_dir);run('engine-build',['node',engine_dir/'build.js']);engine_pin=pin(artifact(engine_dir,'MCEntryInterpreter'))
assert engine_pin['bytes']<=393216,engine_pin
coordinator_source=stage/'coordinator/MCEntryCoordinator.sol'; text=coordinator_source.read_text(); old=parent_pins['engine']['runtimeKeccak256']
if old in text:
 assert text.count(old)==1;text=text.replace(old,engine_pin['runtimeKeccak256']);coordinator_source.write_text(text)
else: assert text.count(engine_pin['runtimeKeccak256'])==1
coord_dir=out/'coordinator';shutil.copytree(stage/'coordinator',coord_dir);run('coordinator-build',['node',coord_dir/'build.js']);coord_pin=pin(artifact(coord_dir,'MCEntryCoordinator'))
assert coord_pin['bytes']==parent_pins['coordinator']['bytes']==5394
driver=stage/'tools/Go.txt';text=driver.read_text()
for old,new in ((parent_pins['engine']['runtimeSHA256'],engine_pin['runtimeSHA256']),('0x'+parent_pins['engine']['runtimeKeccak256'],'0x'+engine_pin['runtimeKeccak256']),('0x'+parent_pins['coordinator']['runtimeKeccak256'],'0x'+coord_pin['runtimeKeccak256'])):
 if old in text: assert text.count(old)==1;text=text.replace(old,new)
 else: assert text.count(new)==1
for pat,repl in ((r'len\(coordRun\) != \d+','len(coordRun) != %d'%coord_pin['bytes']),(r'len\(engineRun\) != \d+','len(engineRun) != %d'%engine_pin['bytes']),(r'len\(run\) != \d+','len(run) != %d'%engine_pin['bytes'])):
 text,n=re.subn(pat,repl,text);assert n==1,(pat,n)
driver.write_text(text)
boot=dict(parent_pins['bootstrapSHA256']);boot['PrintStream']=image_sha(stage/'bootstrap/java/io/PrintStream.class.hex')
pins={'basis':'3dee801e7','parentEvidence':'print-stream-println-string-preflight','phase':'built','domain':'MC-PRINT-CHAR-SINK-001','runtimeBaseline':393206,'runtimeCap':393216,'bootstrapCount':91,'bootstrapSHA256':boot,'globalNativeBindings':13,'stringLocalBinding':10,'exceptionKinds':14,'maxFrames':128,'externalLocalGas':1000000000,'reserve':25000000,'rawLimits':[38,285489],'checkpointCap':1048576,'headCap':32768,'diagnosticClassBound':129,'address':'0x4d432d5052494e542d434841522d53494e4b2d33','owner':'0x4d432d5052494e542d434841522d53494e4b2d34','limitsCommitment':parent_pins['limitsCommitment'],'compiler':parent_pins['compiler'],'engine':engine_pin,'coordinator':coord_pin}
if persisted.exists(): assert json.loads(persisted.read_text())==pins
else: persisted.write_text(json.dumps(pins,indent=2)+'\n')
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
run('source-verification-final',[sys.executable,here/'verify_source.py','--built',out/'pins.json'])
main=out/'main.go';shutil.copy2(driver,main)
for label,cmd in (('gofmt',['gofmt','-w',main]),('go-build',['go','build','-trimpath','-o',out/'driver',main]),('go-vet',['go','vet',main])):run(label,cmd)
print(json.dumps({'build':str(out),'engine':engine_pin,'coordinator':coord_pin},indent=2))
