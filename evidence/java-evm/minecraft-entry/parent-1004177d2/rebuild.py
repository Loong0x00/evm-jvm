#!/usr/bin/env python3
from pathlib import Path
import json,os,re,shutil,subprocess,sys
h=Path(__file__).resolve().parent;r=h.parents[3];s=h.parent/'classcount51-byte328000-preflight';o=Path(sys.argv[1]).resolve();assert o.parent==r/'build' and o.name.startswith('java-diff-mc-raw51-parent-') and not o.exists();o.mkdir();(o/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(o/'tmp'),NODE_PATH=str(r/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(n,a):
 with (o/(n+'.log')).open('w') as f:subprocess.run(list(map(str,a)),cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run('source-verification',[sys.executable,s/'tools/verify_source.py','--built',s/'build-pins.json']);cp=json.loads((s/'build-pins.json').read_text())
e=o/'engine';shutil.copytree(s/'engine',e);p=e/'MCEntryInterpreter.sol';x=p.read_text();assert x.count('MC-SUBSTRING-INT-00002')==9;x=x.replace('MC-SUBSTRING-INT-00002','MC-SUBSTRING-INT-00003');p.write_text(x);run('engine-build',['node',e/'build.js']);ea=json.loads((e/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=393216 and ea['compiler']['optimizer']=={'enabled':True,'runs':200}
c=o/'coordinator';shutil.copytree(s/'coordinator',c);p=c/'MCEntryCoordinator.sol';x=p.read_text();assert x.count('MC-SUBSTRING-INT-00002')==4;x=x.replace('MC-SUBSTRING-INT-00002','MC-SUBSTRING-INT-00003');x,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d535542535452494e472d494e542d303035"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',c/'build.js']);ca=json.loads((c/'MCEntryCoordinator.json').read_text());cs=len(ca['deployedBytecode'])//2
d=(s/'tools/Go.txt').read_text()
for a,z in [('MC-SUBSTRING-INT-00002','MC-SUBSTRING-INT-00003'),(cp['address'],'0x4d432d535542535452494e472d494e542d303035'),(cp['owner'],'0x4d432d535542535452494e472d494e542d303036')]:assert a in d,a;d=d.replace(a,z)
for name,value in [('immutableEngineSHA256',ea['codeHashes']['runtimeSHA256']),('immutableEngineKeccak','0x'+ea['codeHashes']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+ca['codeHashes']['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1,name
for name,value in [('engineRun',size),('coordRun',cs),('run',size)]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),d);assert n==1,name
(o/'main.go').write_text(d)
for n,a in [('gofmt',['gofmt','-w',o/'main.go']),('go-build',['go','build','-trimpath','-o',o/'driver',o/'main.go']),('go-vet',['go','vet',o/'main.go'])]:run(n,a)
res={**cp,'basis':'3903f8da1','worker':'1004177d2','domain':'MC-SUBSTRING-INT-00003','address':'0x4d432d535542535452494e472d494e542d303035','owner':'0x4d432d535542535452494e472d494e542d303036','engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':cs,**ca['codeHashes']}};(o/'pins.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
