#!/usr/bin/env python3
"""Independent P21 compile; verify the one-constant capacity delta and all97 source leaves."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
STAGE=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else HERE.parent/'max-objects-2048'; BASE=HERE.parent/'parent-max-arrays-2048'
out=Path(sys.argv[1]).resolve()
assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-max-objects-2048-build-parent-') and not out.exists()
base=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text(); source=(STAGE/'engine/MCEntryInterpreter.sol').read_text()
a='uint256 private constant MAX_OBJECTS = 1024;';b='uint256 private constant MAX_OBJECTS = 2048;'
assert base.count(a)==1 and source==base.replace(a,b,1), 'candidate delta exceeds the measured object quota'
assert (STAGE/'engine/build.js').read_bytes()==(BASE/'artifacts/engine/build.js').read_bytes()
out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1',GOPROXY='off',GOSUMDB='off')
def run(label,args):
 with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
def root_from_source(text,domain):
 body=text[text.index('    function _bootstrapRoot('):];body=body[:body.index('\n    function ',1)]
 rhs={int(i):v.strip() for i,v in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',body)};assert set(rhs)==set(range(97));pairs=[]
 for i in range(97):
  expr=rhs[i];m=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',expr)
  if m:
   f=text[text.index('    function '+m.group(1)+'('):];f=f[:f.index('\n    function ',1)];v=re.findall(r'hex"([0-9a-f]+)"',f);assert len(v)==1;pairs.append(['image',v[0]])
  else:
   assert re.fullmatch(r'DBOOT_[A-Z_]+',expr);v=re.search(r'bytes32 private constant '+expr+r'\s*=\s*([^;]+);',text).group(1).strip();h=re.findall(r'hex"([0-9a-f]+)"',v);assert len(h)==1;pairs.append(['image' if v.startswith('keccak256(') else 'hexhash',h[0]])
 node="""const fs=require('fs'),{keccak256:k}=require('js-sha3');const x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');let hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(97),...hs.map(v=>Buffer.from(v,'hex'))])));"""
 p=subprocess.run(['node','-e',node],cwd=ROOT,env=env,input=json.dumps({'domain':domain,'pairs':pairs}),text=True,capture_output=True,check=True);value=p.stdout.strip();assert re.fullmatch('[0-9a-f]{64}',value);return value
prior=json.loads((BASE/'artifacts/parent-build-pins.json').read_text())
old='MC-RANDOM-CLASS-P20';new='MC-RANDOM-CLASS-P21';addr='0x4d432d52414e444f4d2d434c4153532d50310044';owner='0x4d432d52414e444f4d2d434c4153532d50310045'
assert root_from_source(base,'JVMEVM:'+old+':BOOTSTRAP:1')==prior['bootstrapRoot']=='845e0c87e52b163b246228ebf4400237953dfac4aa70d5b3fd4217c1dca7dee4'
assert root_from_source(source,'JVMEVM:'+old+':BOOTSTRAP:1')==prior['bootstrapRoot']
assert source.count(old)==9;source=source.replace(old,new);actual=root_from_source(source,'JVMEVM:'+new+':BOOTSTRAP:1');assert actual!=prior['bootstrapRoot']
e=out/'engine';e.mkdir();(e/'MCEntryInterpreter.sol').write_text(source);shutil.copy2(STAGE/'engine/build.js',e/'build.js');run('engine-build',['node',e/'build.js']);ea=json.loads((e/'MCEntryInterpreter.json').read_text());er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']<=393216
c=out/'coordinator';shutil.copytree(BASE/'artifacts/coordinator',c);p=c/'MCEntryCoordinator.sol';text=p.read_text();assert text.count(old)==4;text=text.replace(old,new);text,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',text);assert n==1;text,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{er["runtimeKeccak256"]}";',text);assert n==1;p.write_text(text);run('coordinator-build',['node',c/'build.js']);ca=json.loads((c/'MCEntryCoordinator.json').read_text());cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}
# Keep canonical generated calls at1B; the separately built original driver is gas-only.
d=(BASE/'canonical-driver.go.txt').read_text();assert d.count(old)==6;d=d.replace(old,new).replace(prior['address'],addr).replace(prior['owner'],owner)
for name,val in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+val+r'\g<2>',d);assert n==1
for name,size in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)' in d
(out/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])]:run(label,args)
pins={**prior,'profile':new+'-MAX-OBJECTS-2048','domain':new,'address':addr,'owner':owner,'bootstrapRoot':actual,'expectedBootstrapRoot':actual,'engine':er,'coordinator':cr,'maxArrays':2048,'maxObjects':2048,'maxHandles':4353,'sourceInvariants':{'normalizedDelta':'MAX_OBJECTS1024->2048 only','candidateSameP20Root':prior['bootstrapRoot'],'orderedLeaves':97}}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(out/'root-audit.json').write_text(json.dumps({'acceptedP20Root':prior['bootstrapRoot'],'actualIndependentP21Root':actual,'orderedLeaves':97,'sourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'onlySemanticChange':'MAX_OBJECTS1024->2048, derived MAX_HANDLES'},indent=2)+'\n')
print(json.dumps({'engine':er,'coordinator':cr,'bootstrapRoot':actual,'maxArrays':2048},indent=2))
