#!/usr/bin/env python3
"""Independent P37 compile and full103-leaf/ABI/storage/authentication audit."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];STAGE=H.parent/'pattern-compile-bootstrap';CAND=STAGE/'bootstrap/array-clone-intrinsic';BASE=H.parent/'parent-pattern-compile'
out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-array-clone-build-parent-') and not out.exists()
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
source=(CAND/'MCEntryInterpreter.sol').read_text();assert hashlib.sha256(source.encode()).hexdigest()=='e6775dc4bf560cbfda57a77b8347515c54d9d10651182f6eb40ef000805047bb'
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(out/'tmp'),GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
from root_helper import root_record
prior=json.load(open(BASE/'artifacts/parent-build-pins.json'));oldsource=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text();bootdomain='JVMEVM:MC-PATTERN-COMPILE-P36-PARENT:BOOTSTRAP:1';a=root_record(oldsource,bootdomain,ROOT,env);b=root_record(source,bootdomain,ROOT,env);assert len(a['leaves'])==len(b['leaves'])==103 and a==b and a['root']==prior['bootstrapRoot']
profile='MC-ARRAY-CLONE-INTRINSIC-P37';addr=prior['address'];owner=prior['owner']
e=out/'engine';e.mkdir();(e/'MCEntryInterpreter.sol').write_text(source);shutil.copyfile(BASE/'artifacts/engine/build.js',e/'build.js');run('engine-build',['node',e/'build.js']);ea=json.load(open(e/'MCEntryInterpreter.json'));er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']==410780 and er['runtimeSHA256']=='9145fbb48f5dae753d77c2591e7aa3f6b0e6f6f3c1e0ffdf1f5545626d08aa96';old=json.load(open(BASE/'artifacts/engine/MCEntryInterpreter.json'));assert ea['abi']==old['abi'] and ea['storageLayout']==old['storageLayout']
c=out/'coordinator';c.mkdir();shutil.copyfile(CAND/'MCEntryCoordinator.sol',c/'MCEntryCoordinator.sol');shutil.copyfile(BASE/'artifacts/coordinator/build.js',c/'build.js');run('coordinator-build',['node',c/'build.js']);ca=json.load(open(c/'MCEntryCoordinator.json'));cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']};assert cr['runtimeKeccak256']=='083a87b4073ca9cd1fe3ca76c744e6d7b1bce5092f3108b4415be72ff8c2499d';oldc=json.load(open(BASE/'artifacts/coordinator/MCEntryCoordinator.json'));assert ca['abi']==oldc['abi'] and ca['storageLayout']==oldc['storageLayout']
proofenv=dict(env,ARRAY_CLONE_ENGINE_ARTIFACT_DIR=str(e),ARRAY_CLONE_COORDINATOR_ARTIFACT_DIR=str(c),ARRAY_CLONE_SOURCE_PROOF_OUTPUT=str(out/'source-proof.json'))
with (out/'source-proof.log').open('w') as f:subprocess.run([sys.executable,STAGE/'reference/array-clone-intrinsic/verify_source.py'],cwd=ROOT,env=proofenv,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
d=(BASE/'canonical-driver.go.txt').read_text();assert d.count(prior['domain'])==6;d=d.replace(prior['domain'],profile)
for name,value in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,size in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
assert 'decoder.UseNumber()' in d and 'return 30 * time.Second' in d and 'const ordinaryGas = uint64(1_000_000_000)' in d
(out/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])]:run(label,args)
shutil.copyfile(out/'main.go',out/'product-driver.go.txt');pins={**prior,'profile':profile,'domain':profile,'engine':er,'coordinator':cr,'bootstrapRoot':b['root'],'expectedBootstrapRoot':b['root'],'orderedBootstrapLeaves':b['leaves'],'bootstrapCount':103,'newBootstrapImages':[],'changedBootstrapImages':[],'guestCapability':'generic public array clone intrinsic; Object.clone unsupported'};(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'root-audit.json').write_text(json.dumps({'all103BootstrapImagesAndRootUnchanged':True,'root':b['root'],'leaves':b['leaves'],'engineABIAndStorageUnchanged':True,'coordinatorABIAndStorageUnchanged':True,'noNewNativeBinding':True,'underlyingEVMUnchanged':True,'localPreinstalledNotStandardCREATE':True},indent=2)+'\n');print(json.dumps({'profile':profile,'runtimeBytes':er['bytes'],'runtimeSHA256':er['runtimeSHA256'],'bootstrapCount':103,'bootstrapRoot':b['root'],'checkpointCap':2097152},indent=2))
