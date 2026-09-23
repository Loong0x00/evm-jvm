#!/usr/bin/env python3
"""Independent P4-domain Math.sin(±0) compile, including actual Solidity bootstrap root.

Never treats an inherited metadata pin from a prior domain as the compiled root.
"""
from pathlib import Path
import json,os,re,shutil,subprocess,sys
h=Path(__file__).resolve().parent;r=h.parents[3];s=h.parent/'math-sin-signed-zero-preparation';o=Path(sys.argv[1]).resolve();assert o.parent==r/'build' and o.name.startswith('java-diff-mc-math-sin-build-parent-') and not o.exists();o.mkdir();(o/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(o/'tmp'),NODE_PATH=str(r/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
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
run('source-verification',[sys.executable,s/'tools/verify_source.py']);base=json.loads((s/'baseline-pins.json').read_text());cp=json.loads((s/'results/generated-gate-v1/build-pins.json').read_text());old='MC-RANDOM-CLASS-P2';new='MC-RANDOM-CLASS-P4';addr='0x4d432d52414e444f4d2d434c4153532d5031000a';owner='0x4d432d52414e444f4d2d434c4153532d5031000b';assert cp['engine']['bytes']<=393216
prior=(s.parent/'sparse-primitive-array-checkpoint-preparation'/'engine/MCEntryInterpreter.sol').read_text();assert root_from_source(prior,'JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1')=='7d5bb2f602b85d8a6268549876df5b3811406bd54fd31429bea3d1ea11a19616';assert root_from_source(prior,'JVMEVM:MC-RANDOM-CLASS-P1:BOOTSTRAP:1')==base['bootstrapRoot']=='7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887'
original=(s/'engine/MCEntryInterpreter.sol').read_text();assert root_from_source(original,'JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1')==cp['bootstrapRoot']=='e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac'
e=o/'engine';shutil.copytree(s/'engine',e);p=e/'MCEntryInterpreter.sol';x=p.read_text();assert x.count(old)==9;x=x.replace(old,new);p.write_text(x);actual=root_from_source(x,'JVMEVM:MC-RANDOM-CLASS-P4:BOOTSTRAP:1');assert actual!=cp['bootstrapRoot'];run('engine-build',['node',e/'build.js']);ea=json.loads((e/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=393216
c=o/'coordinator';shutil.copytree(s/'coordinator',c);p=c/'MCEntryCoordinator.sol';x=p.read_text();assert x.count(old)==4;x=x.replace(old,new);x,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{ea["codeHashes"]["runtimeKeccak256"]}";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',c/'build.js']);ca=json.loads((c/'MCEntryCoordinator.json').read_text());cs=len(ca['deployedBytecode'])//2
d=(s/'tools/Go.txt').read_text()
for a,b in [(old,new),(base['address'],addr),(base['owner'],owner)]:assert a in d;d=d.replace(a,b)
for name,value in [('immutableEngineSHA256',ea['codeHashes']['runtimeSHA256']),('immutableEngineKeccak','0x'+ea['codeHashes']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+ca['codeHashes']['runtimeKeccak256'])]:d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,value in [('engineRun',size),('coordRun',cs),('run',size)]:d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),d);assert n==1
(o/'main.go').write_text(d)
for n,a in [('gofmt',['gofmt','-w',o/'main.go']),('go-build',['go','build','-trimpath','-o',o/'driver',o/'main.go']),('go-vet',['go','vet',o/'main.go'])]:run(n,a)
pins={**cp,'basis':'c1953cc63','worker':'parent','domain':new,'address':addr,'owner':owner,'bootstrapRoot':actual,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':cs,**ca['codeHashes']}};(o/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(o/'root-audit.json').write_text(json.dumps({'declaredInheritedP1Pin':base['bootstrapRoot'],'actualPriorP2Root':root_from_source(prior,'JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1'),'actualCandidateP2Root':cp['bootstrapRoot'],'actualIndependentParentP4Root':actual,'orderedLeaves':97},indent=2)+'\n');print(json.dumps({'engine':pins['engine'],'coordinator':pins['coordinator'],'bootstrapCount':pins['bootstrapCount'],'bootstrapRoot':actual,'priorPinMatchesP2':False},indent=2))
