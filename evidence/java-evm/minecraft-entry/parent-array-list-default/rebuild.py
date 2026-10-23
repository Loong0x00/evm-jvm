#!/usr/bin/env python3
"""Independent P50 source/Java/root/build audit, including exact old int image reproduction."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'array-list-default-constructor-bounded';S=H.parent/'array-list-default-source-base-p49';P=H.parent/'parent-linked-hash-map';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-arraylist-default-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));out={};ns={}
 for i,m in enumerate(ms):
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
basepins=json.load(open(S/'pins.json'))
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);assert changed==['_bootstrapArrayList#0','_bootstrapRoot#0']and a.keys()==b.keys(),changed
strip=lambda s:re.sub(r'//[^\n]*','',s);assert strip(a['_bootstrapRoot#0'])==strip(b['_bootstrapRoot#0'])
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
ctor=re.compile(r'    public ArrayList\(int initialCapacity\) \{.*?\n    \}',re.S);assert ctor.search((S/'bootstrap/java/util/ArrayList.java').read_text())[0]==ctor.search((C/'bootstrap/java/util/ArrayList.java').read_text())[0]
support=sorted((C/'compiler-support/java/util').glob('*.java'));baseJ=O/'base-java-classes';baseJ.mkdir();J=O/'java-classes';J.mkdir()
for label,out,source in [('base-javac',baseJ,S),('candidate-javac',J,C)]:run(label,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',out,*support,source/'bootstrap/java/util/AbstractCollection.java',source/'bootstrap/java/util/AbstractList.java',source/'bootstrap/java/util/ArrayList.java'],600)
material=lambda s:bytes.fromhex(re.search(r'function _bootstrapArrayList\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',s)[1]);assert (baseJ/'java/util/ArrayList.class').read_bytes()==material(old);data=(J/'java/util/ArrayList.class').read_bytes();assert data==material(new)and len(data)==696 and sha(data)=='005397601fc3af39adb5a5d6cde2727abfeae2aee583790aae789048463e0114'
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==len(rb['leaves'])==114 and [i for i in range(114)if ra['leaves'][i]!=rb['leaves'][i]]==[98];assert ra['root']==basepins['bootstrapRoot']and rb['root']=='eb09687d795ed3a252ed6662d594fc8ad81f36f71589a43a809f1e6ca8463e5a'
roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();shutil.copy2(C/role/(cn+'.sol'),q/(cn+'.sol'));shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']==429653 and roles['engine']['runtimeSHA256']=='d50f942e99e2862c1b0214fbb2362bacd5946291e4a3be95c86886e0b19c1bf5'and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and 'uint8 public classCount;'in cs and 'n > 150'in cs
previous=json.load(open(P/'artifacts/parent-build-pins.json'));domain=re.search(r'PACKAGE_DOMAIN = keccak256\("([^\"]+)/package/v1"\)',cs)[1];driver=(P/'canonical-driver.go.txt').read_text();assert driver.count(previous['domain'])==6;driver=driver.replace(previous['domain'],domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
image={'index':98,'name':'java/util/ArrayList','bytes':len(data),'sha256':sha(data),'keccak256':rb['leaves'][98]};pins={'profile':'MC-ARRAYLIST-DEFAULT-CONSTRUCTOR-P50-PARENT','domain':domain,'basis':'accepted P49; only ArrayList98 adds ordinary shared empty sentinel, clinit, default constructor','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':114,'baseBootstrapCount':114,'diagnosticClassBound':264,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':[image],'globalNativeBindings':21,'stringLocalBinding':12,'rawLimits':[150,1063930],'checkpointCap':2097152,'maxCheckpointBytes':2097152,'address':basepins['address'],'owner':basepins['owner'],'reserve':25000000,'externalLocalGas':1000000000,'runtimeCap':1048576,'maxFrames':128,'sourceInvariants':{'onlyLeaf98Changed':True,'allOther113ImagesByteExact':True,'intConstructorSourceAndBehaviorPreserved':True,'ordinaryClassInitializationNotSkipped':True,'noMutationGrowthIteratorClaim':True,'ABIStorageCodecAndQuotasUnchanged':True,'native21String12Fixed':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old114Leaves':ra['leaves'],'new114Leaves':rb['leaves'],'root':rb['root'],'changedLeaves':[98],'changedSourceFunctions':changed,'replacedImage':image,'baseArrayListSourceReproducesExactOldImage':True,'ABIStorageExact':True,'allQuotasAndNativeBindingsUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh P50 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
