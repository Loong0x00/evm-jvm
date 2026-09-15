#!/usr/bin/env python3
from pathlib import Path
import json,os,subprocess,sys
h=Path(__file__).resolve().parent;r=h.parents[3];s=h.parent/'system-err-preflight';o=Path(sys.argv[1]).resolve();assert o.parent==r/'build' and (o/'engine/MCEntryInterpreter.json').is_file() and (o/'coordinator/MCEntryCoordinator.json').is_file();env=dict(os.environ,TMPDIR=str(o/'tmp'),NODE_PATH=str(r/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(n,a):
 with (o/(n+'.log')).open('w') as f:subprocess.run(list(map(str,a)),cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
ea=json.loads((o/'engine/MCEntryInterpreter.json').read_text());ca=json.loads((o/'coordinator/MCEntryCoordinator.json').read_text());size=len(ea['deployedBytecode'])//2;wp=json.loads((r/'build/java-diff-mc-system-err-build-parent1-196d83482/pins.json').read_text());pp=json.loads((h.parent/'parent-de60a3245/pins.json').read_text());d=(s/'tools/Go.txt').read_text()
for a,z in [('MC-SYSTEM-ERR-PRNT1','MC-SYSTEM-ERR-PRNT2'),(pp['engine']['runtimeSHA256'],ea['codeHashes']['runtimeSHA256']),('0x'+pp['engine']['runtimeKeccak256'],'0x'+ea['codeHashes']['runtimeKeccak256']),('0x'+pp['coordinator']['runtimeKeccak256'],'0x'+ca['codeHashes']['runtimeKeccak256']),(str(pp['engine']['bytes']),str(size)),(wp['address'],'0x4d432d53595354454d2d4552522d50524e543200'),(wp['owner'],'0x4d432d53595354454d2d4552522d4f574e523200')]:assert a in d,a;d=d.replace(a,z)
(o/'main.go').write_text(d)
for n,a in [('gofmt',['gofmt','-w',o/'main.go']),('go-build',['go','build','-trimpath','-o',o/'driver',o/'main.go']),('go-vet',['go','vet',o/'main.go'])]:run(n,a)
res={**wp,'basis':'0f01f1ff9','worker':'89928ece8','domain':'MC-SYSTEM-ERR-PRNT2','address':'0x4d432d53595354454d2d4552522d50524e543200','owner':'0x4d432d53595354454d2d4552522d4f574e523200','engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}};(o/'pins.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
