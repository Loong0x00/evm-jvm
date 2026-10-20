#!/usr/bin/env python3
"""Independent LOCAL1M/P29 build: frozen measured ArrayList append, stock EVM unchanged."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];STAGE=H.parent/'array-list-local1m';BASE=H.parent/'parent-raw75-byte531965'
out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-array-list-local1m-build-parent-') and not out.exists()
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
source=(STAGE/'engine/MCEntryInterpreter.sol').read_text();assert hashlib.sha256(source.encode()).hexdigest()=='9ab9d8ce8403ab1a66d897a91cae34c9da62f3d5595508cde814bab1c0c742c3'
subprocess.run([sys.executable,H/'verify_source.py',STAGE/'engine/MCEntryInterpreter.sol'],cwd=ROOT,check=True)
old_builder=(BASE/'artifacts/engine/build.js').read_text();expected=old_builder.replace('runtime.length/2>384*1024','runtime.length/2>1024*1024').replace("'runtime >384KiB'","'runtime >LOCAL1M 1048576 bytes'");assert (STAGE/'engine/build.js').read_text()==expected
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(out/'tmp'),GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
from root_helper import root_record
prior=json.load(open(BASE/'artifacts/parent-build-pins.json'));base=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text();old='MC-RANDOM-CLASS-P28';new='MC-ARRAY-LIST-LOCAL1M-P29';addr='0x4d432d52414e444f4d2d434c4153532d50310062';owner='0x4d432d52414e444f4d2d434c4153532d50310063'
a=root_record(base,'JVMEVM:'+old+':BOOTSTRAP:1',ROOT,env);b=root_record(source,'JVMEVM:'+old+':BOOTSTRAP:1',ROOT,env);assert len(a['leaves'])==97 and len(b['leaves'])==99 and b['leaves'][:97]==a['leaves'] and a['root']==prior['bootstrapRoot'];assert source.count(old)==9;source=source.replace(old,new);root=root_record(source,'JVMEVM:'+new+':BOOTSTRAP:1',ROOT,env)
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
e=out/'engine';e.mkdir();(e/'MCEntryInterpreter.sol').write_text(source);shutil.copy2(STAGE/'engine/build.js',e/'build.js');run('engine-build',['node',e/'build.js']);ea=json.load(open(e/'MCEntryInterpreter.json'));er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']<=1048576;old_art=json.load(open(BASE/'artifacts/engine/MCEntryInterpreter.json'));assert ea['abi']==old_art['abi'] and ea['storageLayout']==old_art['storageLayout']
c=out/'coordinator';shutil.copytree(BASE/'artifacts/coordinator',c);p=c/'MCEntryCoordinator.sol';s=p.read_text();assert s.count(old)==4;s=s.replace(old,new);s,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',s);assert n==1;s,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{er["runtimeKeccak256"]}";',s);assert n==1;p.write_text(s);run('coordinator-build',['node',c/'build.js']);ca=json.load(open(c/'MCEntryCoordinator.json'));cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}
d=(BASE/'canonical-driver.go.txt').read_text();assert d.count(old)==6;d=d.replace(old,new).replace(prior['address'],addr).replace(prior['owner'],owner)
for name,val in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+val+r'\g<2>',d);assert n==1
for name,size in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
assert 'return 30 * time.Second' in d and 'const ordinaryGas = uint64(1_000_000_000)' in d
(out/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])]:run(label,args)
(out/'product-driver.go.txt').write_bytes((out/'main.go').read_bytes())
pins={**prior,'profile':new,'domain':new,'address':addr,'owner':owner,'bootstrapCount':99,'baseBootstrapCount':97,'bootstrapRoot':root['root'],'expectedBootstrapRoot':root['root'],'orderedBootstrapLeaves':root['leaves'],'diagnosticClassBound':174,'runtimeCap':1048576,'runtimeCapBytes':1048576,'maxCheckpointBytes':1048576,'rawLimits':[75,531965],'engine':er,'coordinator':cr,'globalNativeBindings':21,'stringLocalBinding':12,'newBootstrapImages':['java/util/AbstractList','java/util/ArrayList'],'quotaPolicy':'project budgets double when measured insufficient, not VM rule changes'}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'root-audit.json').write_text(json.dumps({'base97RootP28':a['root'],'candidate99RootP28':b['root'],'actual99RootP29':root['root'],'old97LeavesUnchanged':True,'new99Leaves':root['leaves'],'sourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'underlyingPathsMatchGetHBase95665d570':['core/vm','core/state','params'],'localPreinstalledCodeNotStandardCREATE':True},indent=2)+'\n');print(json.dumps({'profile':new,'engine':er,'coordinator':cr,'bootstrapCount':99,'bootstrapRoot':root['root'],'runtimeCeiling':1048576,'checkpointCeilingUnchanged':1048576},indent=2))
