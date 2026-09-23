#!/usr/bin/env python3
"""Independent parent-domain compile of the measured sparse checkpoint candidate."""
from pathlib import Path
import json,os,re,shutil,subprocess,sys
h=Path(__file__).resolve().parent;r=h.parents[3];s=h.parent/'sparse-primitive-array-checkpoint-preparation';o=Path(sys.argv[1]).resolve();assert o.parent==r/'build' and o.name.startswith('java-diff-mc-sparse-parent-') and not o.exists();o.mkdir();(o/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(o/'tmp'),NODE_PATH=str(r/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(n,a):
 with (o/(n+'.log')).open('w') as f:subprocess.run(list(map(str,a)),cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run('source-verification',[sys.executable,s/'tools/verify_source.py']);cp=json.loads((s/'build-pins.json').read_text());baseline=json.loads((s/'baseline-pins.json').read_text());old='MC-RANDOM-CLASS-P2';new='MC-RANDOM-CLASS-P3';addr='0x4d432d52414e444f4d2d434c4153532d50310004';owner='0x4d432d52414e444f4d2d434c4153532d50310005';assert cp['engine']['bytes']==385803<=393216
engine=o/'engine';shutil.copytree(s/'engine',engine);p=engine/'MCEntryInterpreter.sol';x=p.read_text();assert x.count(old)==9;x=x.replace(old,new);p.write_text(x);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=393216
coord=o/'coordinator';shutil.copytree(s/'coordinator',coord);p=coord/'MCEntryCoordinator.sol';x=p.read_text();assert x.count(old)==4;x=x.replace(old,new);x,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{ea["codeHashes"]["runtimeKeccak256"]}";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',coord/'build.js']);ca=json.loads((coord/'MCEntryCoordinator.json').read_text());cs=len(ca['deployedBytecode'])//2
d=(s/'tools/Go.txt').read_text()
for a,b in [(old,new),(baseline['address'],addr),(baseline['owner'],owner)]:assert a in d;d=d.replace(a,b)
for name,value in [('immutableEngineSHA256',ea['codeHashes']['runtimeSHA256']),('immutableEngineKeccak','0x'+ea['codeHashes']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+ca['codeHashes']['runtimeKeccak256'])]:d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,value in [('engineRun',size),('coordRun',cs),('run',size)]:d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),d);assert n==1
(o/'main.go').write_text(d)
for n,a in [('gofmt',['gofmt','-w',o/'main.go']),('go-build',['go','build','-trimpath','-o',o/'driver',o/'main.go']),('go-vet',['go','vet',o/'main.go'])]:run(n,a)
res={**cp,'basis':'23f706fbc','worker':'parent','domain':new,'address':addr,'owner':owner,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':cs,**ca['codeHashes']}};(o/'pins.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'engine':res['engine'],'coordinator':res['coordinator'],'bootstrapCount':res['bootstrapCount'],'bootstrapRoot':res['bootstrapRoot']},indent=2))
