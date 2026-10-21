#!/usr/bin/env python3
"""Independent P36 build: guest Pattern compile append, stock geth EVM unchanged."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];STAGE=H.parent/'pattern-compile-bootstrap';BASE=H.parent/'parent-hash-map-default'
out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-pattern-compile-build-parent-') and not out.exists()
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
source=(STAGE/'engine/MCEntryInterpreter.sol').read_text();assert hashlib.sha256(source.encode()).hexdigest()=='8aff3c4b1ae209a59ced3a5440de7566748dbe6a71c07b07e827de3fac3f512a'
subprocess.run([sys.executable,STAGE/'tools/verify_source.py'],cwd=ROOT,check=True)
assert (STAGE/'engine/build.js').read_bytes()==(BASE/'artifacts/engine/build.js').read_bytes()
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(out/'tmp'),GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
from root_helper import root_record
prior=json.load(open(BASE/'artifacts/parent-build-pins.json'));base=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text();old='MC-PATTERN-COMPILE-P36';new='MC-PATTERN-COMPILE-P36-PARENT';addr='0x4d432d52414e444f4d2d434c4153532d50310070';owner='0x4d432d52414e444f4d2d434c4153532d50310071'
a=root_record(base,'JVMEVM:'+prior['domain']+':BOOTSTRAP:1',ROOT,env);b=root_record(source,'JVMEVM:'+old+':BOOTSTRAP:1',ROOT,env);assert len(a['leaves'])==101 and len(b['leaves'])==103 and b['leaves'][:101]==a['leaves'];assert a['root']==prior['bootstrapRoot'];assert b['leaves'][101]=='c00433f134a87e9466c2affacba5f176b869a14142edb59435d6e12f8164046b' and b['leaves'][102]=='486cb333853155ebd6334af067b8479764389718e9de547114e987e677058ab5';assert b['leaves'][89]=='ce47f22975cb30c8cec530657ebcaa855cc62fcc3dc62f4fa2f464dc2555cff7'
assert source.count(old)==9;source=source.replace(old,new);root=root_record(source,'JVMEVM:'+new+':BOOTSTRAP:1',ROOT,env)
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
e=out/'engine';e.mkdir();(e/'MCEntryInterpreter.sol').write_text(source);shutil.copy2(STAGE/'engine/build.js',e/'build.js');run('engine-build',['node',e/'build.js']);ea=json.load(open(e/'MCEntryInterpreter.json'));er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']<=1048576;old_art=json.load(open(BASE/'artifacts/engine/MCEntryInterpreter.json'));assert ea['abi']==old_art['abi']
# Solidity's private constant append shifts source AST IDs, not storage slots/types.
def storage_without_source_ids(value):
 if isinstance(value,dict):return {k:storage_without_source_ids(v) for k,v in value.items() if k!='astId'}
 if isinstance(value,list):return [storage_without_source_ids(v) for v in value]
 return value
assert storage_without_source_ids(ea['storageLayout'])==storage_without_source_ids(old_art['storageLayout'])
(out/'storage-layout-audit.json').write_text(json.dumps({'sourceASTIDsMayShift':True,'onlyASTIDRemovedForComparison':True,'allSlotsOffsetsTypesMembersAndLabelsIdentical':True,'oldLayout':old_art['storageLayout'],'newLayout':ea['storageLayout']},indent=2)+'\n')
c=out/'coordinator';shutil.copytree(STAGE/'coordinator',c);p=c/'MCEntryCoordinator.sol';s=p.read_text();assert s.count(old)==4;s=s.replace(old,new);s,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',s);assert n==1;s,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{er["runtimeKeccak256"]}";',s);assert n==1;p.write_text(s);run('coordinator-build',['node',c/'build.js']);ca=json.load(open(c/'MCEntryCoordinator.json'));cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}
d=(BASE/'canonical-driver.go.txt').read_text();assert d.count(prior['domain'])==6;d=d.replace(prior['domain'],new).replace(prior['address'],addr).replace(prior['owner'],owner)
for name,val in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+val+r'\g<2>',d);assert n==1
for name,size in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
assert 'decoder.UseNumber()' in d # inherited lossless observer metadata, no original source changes
assert 'return 30 * time.Second' in d and 'const ordinaryGas = uint64(1_000_000_000)' in d
(out/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])]:run(label,args)
(out/'product-driver.go.txt').write_bytes((out/'main.go').read_bytes())
pins={**prior,'profile':new,'domain':new,'address':addr,'owner':owner,'bootstrapCount':103,'baseBootstrapCount':101,'bootstrapRoot':root['root'],'expectedBootstrapRoot':root['root'],'orderedBootstrapLeaves':root['leaves'],'diagnosticClassBound':253,'runtimeCap':1048576,'runtimeCapBytes':1048576,'maxCheckpointBytes':2097152,'checkpointCapBytes':2097152,'checkpointCap':2097152,'rawLimits':[150,1063930],'engine':er,'coordinator':cr,'globalNativeBindings':21,'stringLocalBinding':12,'newBootstrapImages':['java/util/regex/Pattern','java/util/regex/PatternSyntaxException'],'changedBootstrapImages':[],'math':{'keccak256':b['leaves'][89]},'expectedMathKeccak256':b['leaves'][89]}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'root-audit.json').write_text(json.dumps({'base101RootP35':a['root'],'candidate103RootP36':b['root'],'actual103RootP36Parent':root['root'],'allPrior101BootstrapLeavesUnchanged':True,'guestPatternCompilerAppended':True,'new103Leaves':root['leaves'],'sourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'underlyingPathsMatchGetHBase95665d570':['core/vm','core/state','params'],'localPreinstalledCodeNotStandardCREATE':True},indent=2)+'\n');print(json.dumps({'profile':new,'engine':er,'coordinator':cr,'bootstrapCount':103,'bootstrapRoot':root['root'],'runtimeCeiling':1048576,'checkpointCeilingUnchanged':2097152},indent=2))
