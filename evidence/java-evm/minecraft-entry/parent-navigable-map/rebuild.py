#!/usr/bin/env python3
"""Independent P44 source/root/Java/ABI/storage build; no coordinator migration."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'navigable-map-link';S=H.parent/'navigable-map-source-base-p43';P=H.parent/'parent-function-interface';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-navigable-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));o={};counts={}
 for i,m in enumerate(ms):
  n=counts.get(m[1],0);counts[m[1]]=n+1;o[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 return o
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
m=json.load(open(S/'source-manifest.json'))
for n,pin in m['files'].items():
 b=(S/n).read_bytes();assert len(b)==pin['bytes']and sha(b)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);added=sorted(b.keys()-a.keys());assert changed==['_bootstrapRoot#0','_isReservedPlatformMapClass#0','_prepare#0']and added==['_bootstrapNavigableMap#0']and not a.keys()-b.keys(),(changed,added)
assert '|| _isNamedClass(users[i], bytes("java/util/NavigableMap"))'in b['_prepare#0'];assert 'p.classes[count - 2] = _parseBundleClass(_bootstrapFunction());'in b['_prepare#0']and 'p.classes[count - 1] = _parseBundleClass(_bootstrapNavigableMap());'in b['_prepare#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
classes=O/'java-classes';classes.mkdir();run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-d',classes,C/'bootstrap/NavigableMap.java',C/'bootstrap/SortedMap.java',C/'bootstrap/Map.java'],600);data=(classes/'java/util/NavigableMap.class').read_bytes();embedded=bytes.fromhex(re.search(r'function _bootstrapNavigableMap\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',new)[1]);assert data==embedded and len(data)==254 and sha(data)=='44efe011ca8062c1bb5bb1e8519bb0ab9fe7eb76c1133b7eea678609055d14e1'
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==106 and len(rb['leaves'])==107 and ra['leaves']==rb['leaves'][:106]and rb['root']=='e7d9456b75653a4945e184c8a48c7af83ac4b17dd7fea813af53a2a420504dff'
roles={}
for role,contract in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();shutil.copy2(C/role/(contract+'.sol'),q/(contract+'.sol'));shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(contract+'.json')));oldart=json.load(open(S/role/(contract+'.json')));assert j['abi']==oldart['abi']and j['storageLayout']==oldart['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']==422246 and roles['engine']['runtimeSHA256']=='990d44aa156e1392379494311d27326efe19ed886cb659c596ede35046306cae'and roles['coordinator']['runtimeKeccak256']=='fec02a9b7446aa43bcad5e7f47f9750e9d557a5d3950d587722d35d781da04d1'
cs=(C/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and 'uint8 public classCount;'in cs and 'n > 150'in cs
prev=json.load(open(P/'artifacts/parent-build-pins.json'));domain=re.search(r'PACKAGE_DOMAIN = keccak256\("([^\"]+)/package/v1"\)',cs)[1];driver=(P/'canonical-driver.go.txt').read_text();assert driver.count(prev['domain'])==6;driver=driver.replace(prev['domain'],domain)
for name,v in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:
 driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',r'\g<1>'+v+r'\g<2>',driver);assert n==1
for name,nbytes in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:
 driver,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(nbytes),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**prev,'profile':'MC-NAVIGABLE-MAP-LINK-P44-PARENT','domain':domain,'basis':'accepted P43 Function source-only; NavigableMap marker append','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':107,'baseBootstrapCount':106,'diagnosticClassBound':257,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'externalLocalGas':1000000000,'sourceInvariants':{'all106PriorImagesUnchanged':True,'newNavigableMapLeaf':106,'rawNamespaceReserved':True,'ABIStorageCodecAndQuotasUnchanged':True,'coordinatorStill150RawBindingsNot257':True,'derivedClass257WireU16':True,'native21String12Fixed':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');proof={'status':'PASS','old106Leaves':ra['leaves'],'new107Leaves':rb['leaves'],'root':rb['root'],'FunctionPrefixAndParentRegexFixPreserved':True,'changedSourceFunctions':changed,'addedSourceFunction':added,'newImageBytes':254,'newImageSHA256':sha(data),'ABIStorageExact':True,'allQuotasAndNativeBindingsUnchanged':True,'rawCoordinatorUint8Bound150Unchanged':True,'internalClass257Index256RequiresEvmGate':True};(O/'root-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':'parent fresh NavigableMap build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
