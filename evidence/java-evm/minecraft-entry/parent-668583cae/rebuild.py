#!/usr/bin/env python3
"""Independent P19-domain grouped float scan on accepted P18 exact checkpoint semantics, including actual Solidity bootstrap root.

Never treats an inherited metadata pin from a prior domain as the compiled root.
"""
from pathlib import Path
import json,os,re,shutil,subprocess,sys
h=Path(__file__).resolve().parent;r=h.parents[3];s=h.parent/'packed-float-grouped-scan';o=Path(sys.argv[1]).resolve();assert o.parent==r/'build' and o.name.startswith('java-diff-mc-packed-float-grouped-scan-build-parent-') and not o.exists();o.mkdir();(o/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(o/'tmp'),NODE_PATH=str(r/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(n,a):
 with (o/(n+'.log')).open('w') as f:subprocess.run(list(map(str,a)),cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def root_from_source(src,domain):
 """Hash the exact Solidity h[0..96] RHS, not a stale pin or a guessed image list."""
 body=src[src.index('    function _bootstrapRoot('):];body=body[:body.index('\n    function ',1)];assignments={int(i):rhs.strip() for i,rhs in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',body)};assert set(assignments)==set(range(97));pairs=[]
 for i in range(97):
  rhs=assignments[i];f=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',rhs)
  if f:
   p=src.index('    function '+f.group(1)+'(');b=src[p:];b=b[:b.index('\n    function ',1)];hexes=re.findall(r'hex"([0-9a-f]+)"',b);assert len(hexes)==1,(i,len(hexes));pairs.append(['image',hexes[0]]);continue
  assert re.fullmatch(r'DBOOT_[A-Z_]+',rhs),(i,rhs)
  expr=re.search(r'bytes32 private constant '+rhs+r'\s*=\s*([^;]+);',src).group(1).strip();assert expr.startswith('hex"') or expr.startswith('keccak256(hex"'),(i,rhs)
  hexes=re.findall(r'hex"([0-9a-f]+)"',expr);assert len(hexes)==1
  pairs.append(['hexhash' if expr.startswith('hex"') else 'image',hexes[0]])
 node='''const fs=require('fs'),{keccak256}=require('js-sha3');const a=JSON.parse(fs.readFileSync(0,'utf8'));const k=s=>keccak256(Buffer.from(s,'hex'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');const hs=a.pairs.map(([t,v])=>t==='image'?k(v):v);const x=Buffer.concat([Buffer.from(keccak256(a.domain),'hex'),w(64),w(hs.length),...hs.map(v=>Buffer.from(v,'hex'))]);console.log(keccak256(x));'''
 x=subprocess.run(['node','-e',node],input=json.dumps({'pairs':pairs,'domain':domain}),text=True,capture_output=True,cwd=r,env=env,check=True).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',x);return x
audit=json.loads((s/'results/01-local-b/source-audit.json').read_text());assert audit['changedFunctions']==['_checkpointArrayNonzeroCount'] and audit['bootstrapRoot']=='828af33f62f6e92513d9605bf832437e1330b4d325bb04f913b97fd6f20596bd';base=json.loads((s.parent/'parent-e23eea569'/'artifacts/parent-build-pins.json').read_text());cp=json.loads((s/'results/01-local-b/pins.json').read_text());old='MC-RANDOM-CLASS-P18';new='MC-RANDOM-CLASS-P19';addr='0x4d432d52414e444f4d2d434c4153532d50310040';owner='0x4d432d52414e444f4d2d434c4153532d50310041';assert cp['engine']['bytes']<=393216
prior=(s.parent/'parent-e23eea569'/'artifacts/engine/MCEntryInterpreter.sol').read_text();assert root_from_source(prior,'JVMEVM:MC-RANDOM-CLASS-P18:BOOTSTRAP:1')==base['bootstrapRoot']==cp['bootstrapRoot']=='828af33f62f6e92513d9605bf832437e1330b4d325bb04f913b97fd6f20596bd'
original=(s/'engine/MCEntryInterpreter.sol').read_text();assert root_from_source(original,'JVMEVM:MC-RANDOM-CLASS-P18:BOOTSTRAP:1')==cp['bootstrapRoot']
e=o/'engine';shutil.copytree(s/'engine',e);p=e/'MCEntryInterpreter.sol';x=p.read_text();assert x.count(old)==9;x=x.replace(old,new);p.write_text(x);actual=root_from_source(x,'JVMEVM:MC-RANDOM-CLASS-P19:BOOTSTRAP:1');assert actual!=cp['bootstrapRoot'];run('engine-build',['node',e/'build.js']);ea=json.loads((e/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=393216
c=o/'coordinator';shutil.copytree(s.parent/'parent-e23eea569'/'artifacts/coordinator',c);p=c/'MCEntryCoordinator.sol';x=p.read_text();assert x.count(old)==4;x=x.replace(old,new);x,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{ea["codeHashes"]["runtimeKeccak256"]}";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',c/'build.js']);ca=json.loads((c/'MCEntryCoordinator.json').read_text());cs=len(ca['deployedBytecode'])//2
d=(s.parent/'parent-e23eea569'/'canonical-driver.go.txt').read_text()
for a,b in [(old,new),(cp['address'],addr),(cp['owner'],owner)]:assert a in d;d=d.replace(a,b)
for name,value in [('immutableEngineSHA256',ea['codeHashes']['runtimeSHA256']),('immutableEngineKeccak','0x'+ea['codeHashes']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+ca['codeHashes']['runtimeKeccak256'])]:d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,value in [('engineRun',size),('coordRun',cs),('run',size)]:d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),d);assert n==1
(o/'main.go').write_text(d)
for n,a in [('gofmt',['gofmt','-w',o/'main.go']),('go-build',['go','build','-trimpath','-o',o/'driver',o/'main.go']),('go-vet',['go','vet',o/'main.go'])]:run(n,a)
pins={**cp,'basis':'668583cae','worker':'parent','domain':new,'address':addr,'owner':owner,'bootstrapRoot':actual,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':cs,**ca['codeHashes']}};(o/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(o/'root-audit.json').write_text(json.dumps({'acceptedP18Root':base['bootstrapRoot'],'candidateP18Root':cp['bootstrapRoot'],'actualIndependentParentP19Root':actual,'orderedLeaves':97},indent=2)+'\n');print(json.dumps({'engine':pins['engine'],'coordinator':pins['coordinator'],'bootstrapCount':pins['bootstrapCount'],'bootstrapRoot':actual,'acceptedP18RootMatchesSource':True},indent=2))
