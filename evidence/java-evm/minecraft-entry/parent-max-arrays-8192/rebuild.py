#!/usr/bin/env python3
"""Independent P41 compile/root/ABI/storage proof; product1B and test32B kept separate."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'max-arrays-8192';B=H.parent/'parent-hash-map-put';S=H.parent/'max-arrays-8192-source-base-p39';O=Path(sys.argv[1]).resolve()
assert O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-max-arrays-8192-build-') and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1')
def sha(b):return hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with (O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
manifest=json.load(open(C/'source-base-manifest.json'))
for n,pin in manifest['files'].items():
 b=(S/n).read_bytes();assert len(b)==pin['bytes'] and sha(b)==pin['sha256'],n
base=(B/'artifacts/engine/MCEntryInterpreter.sol').read_text();source=(C/'engine/MCEntryInterpreter.sol').read_text();oldProfile='MC-HASH-MAP-PUT-BOUNDED-P39';profile='MC-HASH-MAP-PUT-BOUNDED-P41-ARRAY-8192'
assert base.count('uint256 private constant MAX_ARRAYS = 4096;')==1
assert source==base.replace('uint256 private constant MAX_ARRAYS = 4096;','uint256 private constant MAX_ARRAYS = 8192;',1).replace(oldProfile,profile)
for key,value in [('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(value)+r';',source),key
from root_helper import root_record
domain='JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1';a=root_record(base,domain,ROOT,env);b=root_record(source,domain,ROOT,env);assert a==b and len(b['leaves'])==105 and b['root']=='ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd'
roles={}
for role,contract in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();shutil.copy2(C/role/(contract+'.sol'),q/(contract+'.sol'));shutil.copy2(B/'artifacts'/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);art=json.load(open(q/(contract+'.json')));prev=json.load(open(B/'artifacts'/role/(contract+'.json')));worker=json.load(open(C/role/(contract+'.json')));assert art['abi']==prev['abi'] and art['storageLayout']==prev['storageLayout'];assert art['codeHashes']==worker['codeHashes'];roles[role]={'bytes':len(art['deployedBytecode'])//2,**art['codeHashes']}
assert roles['engine']['bytes']==418986 and roles['engine']['runtimeSHA256']=='32a16b78a9cec4b72835eaab094c715e3a5f310ed9f2b211d49e29237c5b5f02';assert roles['coordinator']['runtimeSHA256']=='a89f68c52a8fa4b49f103add3ece3f48619432628641a49a13babea10835d695'
cb=(B/'artifacts/coordinator/MCEntryCoordinator.sol').read_text();cc=(C/'coordinator/MCEntryCoordinator.sol').read_text();prev=json.load(open(B/'artifacts/parent-build-pins.json'));assert cc==cb.replace(oldProfile,profile).replace(prev['engine']['runtimeKeccak256'],roles['engine']['runtimeKeccak256'])
d=(B/'canonical-driver.go.txt').read_text();assert d.count(oldProfile)==6;d=d.replace(oldProfile,profile)
for name,v in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',r'\g<1>'+v+r'\g<2>',d);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in d and 'decoder.UseNumber()'in d
(O/'main.go').write_text(d);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
test=d.replace('const ordinaryGas = uint64(1_000_000_000)','const ordinaryGas = uint64(32_000_000_000)').replace('LOCAL1B-USER-AUTHORIZED','LOCAL32B-ARRAY-8192-MEASURED-USER-BUDGET');(O/'test32B.go.txt').write_text(test);T=O/'test32B';T.mkdir();(T/'main.go').write_text(test);run('test32B-build',['go','build','-trimpath','-o',O/'test32B-driver',T/'main.go'],900)
pins={**prev,'profile':profile,'domain':profile,'basis':'accepted P39 parent-hash-map-put source; array count only','engine':roles['engine'],'coordinator':roles['coordinator'],'maxArrays':8192,'maxObjects':4096,'maxArrayElements':262144,'maxHandles':12545,'externalLocalGas':1000000000,'generatedCapacityTestGas':32000000000,'bootstrapCount':105,'bootstrapRoot':b['root'],'expectedBootstrapRoot':b['root'],'sourceInvariants':{'all105ImagesAndRootUnchanged':True,'arrayCountOnly4096To8192':True,'derivedMaxHandles12545':True,'allOtherQuotasUnchanged':True,'ABIStorageCodecUnchanged':True,'noNewOperationalNative':True,'noUnderlyingEvmChange':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');proof={'all105OrderedLeavesAndRootUnchanged':True,**b,'MAX_ARRAYS':8192,'MAX_HANDLES':12545,'uint16CountFits':True,'sourceDeltaOnlyArrayCountAndExplicitDomains':True,'ABIStorageExactMatch':True,'nativeGlobal21String12Fixed':True,'canonicalProductGas1B':True,'separateGeneratedTestGas32B':True,'noSchemaChange':True};(O/'root-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':'parent fresh build/root proof passed','profile':profile,'engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapRoot':b['root']},indent=2))
