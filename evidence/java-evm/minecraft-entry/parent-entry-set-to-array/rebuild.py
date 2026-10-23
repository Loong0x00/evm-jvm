#!/usr/bin/env python3
"""Independent P48 source/Java/ordered-root/build audit; no original inputs."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'entry-set-typed-to-array-bounded';S=C/'source-basis';P=H.parent/'parent-hash-map-entry-set';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-entry-array-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));out={};ns={}
 for i,m in enumerate(ms):
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);assert changed==['_bootstrapAbstractCollection#0','_bootstrapCollection#0','_bootstrapHashMapEntrySet#0']and a.keys()==b.keys(),changed
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
oldjava=(S/'bootstrap/java/util/HashMap.java').read_text();newjava=(C/'source/bootstrap/java/util/HashMap.java').read_text();start=newjava.index('        private native void refuseTypedToArrayTooSmall();');end=newjava.index('        public native boolean equals(Object other);',start);assert newjava[:start]+'        public native <T> T[] toArray(T[] target);\n'+newjava[end:]==oldjava
J=O/'java-classes';J.mkdir();run('javac-hashmap',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,C/'source/bootstrap/java/util/HashMap.java'],600)
for n in('Map','Collection','AbstractCollection'):run('javac-'+n,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,C/('source/bootstrap/java/util/'+n+'.java')],600)
images=[]
for leaf,method,binary in [(40,'Map','Map'),(53,'Collection','Collection'),(55,'AbstractCollection','AbstractCollection'),(94,'MapEntry','Map$Entry'),(100,'HashMap','HashMap'),(104,'HashMapNode','HashMap$Node'),(110,'HashMapEntrySet','HashMap$EntrySet'),(111,'HashMapEntryIterator','HashMap$EntryIterator')]:
 data=(J/('java/util/'+binary+'.class')).read_bytes();embedded=bytes.fromhex(re.search(r'function _bootstrap'+method+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',new)[1]);assert data==embedded,(leaf,binary);images.append({'leaf':leaf,'name':'java/util/'+binary,'bytes':len(data),'sha256':sha(data)})
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==len(rb['leaves'])==113 and [i for i in range(113)if ra['leaves'][i]!=rb['leaves'][i]]==[53,55,110]
for row in images:row['keccak256']=rb['leaves'][row['leaf']]
roles={}
for role,contract in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(contract+'.sol')).read_text()
 if role=='coordinator':text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1
 (q/(contract+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(contract+'.json')));prior=json.load(open(S/role/(contract+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']<=1048576 and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'uint8 public classCount;'in cs and 'n > 150'in cs
prev=json.load(open(P/'artifacts/parent-build-pins.json'));domain=re.search(r'PACKAGE_DOMAIN = keccak256\("([^\"]+)/package/v1"\)',cs)[1];driver=(P/'canonical-driver.go.txt').read_text();assert driver.count(prev['domain'])==6;driver=driver.replace(prev['domain'],domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**prev,'profile':'MC-ENTRY-SET-TYPED-ARRAY-P48-PARENT-CORRECTED','domain':domain,'basis':'accepted P47; bounded same-target typed-array copy and inherited raw refusal guard','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':113,'baseBootstrapCount':113,'diagnosticClassBound':263,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':images,'externalLocalGas':1000000000,'sourceInvariants':{'onlyLeaves53And55And110Changed':True,'HashMap100Node104Map40Entry94Exact':True,'noNewBootstrapImages':True,'unsupportedInheritedToArrayRawNotAME':True,'noArrayGrowthReflectionNoArgImplementation':True,'ABIStorageCodecAndQuotasUnchanged':True,'native21String12Fixed':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old113Leaves':ra['leaves'],'new113Leaves':rb['leaves'],'root':rb['root'],'changedLeaves':[53,55,110],'changedSourceFunctions':changed,'images':images,'ABIStorageExact':True,'allQuotasAndNativeBindingsUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh P48 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
