#!/usr/bin/env python3
"""Independent P52 source/Java/root/layout/authentication build; no original inputs."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'array-list-iterator-bounded';S=H.parent/'array-list-iterator-source-base-p51';P=H.parent/'parent-list-iterator-link';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-arraylist-iterator-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));out={};ns={}
 for i,m in enumerate(ms):
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);basepins=json.load(open(S/'pins.json'))
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);added=sorted(b.keys()-a.keys());assert changed==['_appendTailBootstraps#0','_bootstrapArrayList#0','_bootstrapRoot#0','_prepare#0']and added==['_bootstrapArrayListItr#0']and not a.keys()-b.keys(),(changed,added)
assert new.count('MC-ARRAYLIST-ITERATOR-BOUNDED-1')==9 and 'bytes("java/util/ArrayList$Itr")'in b['_prepare#0']and 'p.classes[classSlot + 76].data = _bootstrapArrayListItr();'in b['_appendTailBootstraps#0']
for offset,name in[(11,'Function'),(10,'NavigableMap'),(9,'Comparator'),(8,'SortedSet'),(7,'NavigableSet')]:assert f'p.classes[count - {offset}] = _parseBundleClass(_bootstrap{name}());'in b['_prepare#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
oldjava=(S/'bootstrap/java/util/ArrayList.java').read_text();newjava=(C/'bootstrap/java/util/ArrayList.java').read_text()
for pattern in(r'    public ArrayList\(\) \{.*?\n    \}',r'    public ArrayList\(int initialCapacity\) \{.*?\n    \}'):
 assert re.search(pattern,oldjava,re.S)[0]==re.search(pattern,newjava,re.S)[0]
assert 'private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = new Object[0];'in newjava and 'public native boolean add(Object value);'in newjava
support=sorted((S/'compiler-support/java/util').glob('*.java'));baseJ=O/'base-java-classes';baseJ.mkdir();J=O/'java-classes';J.mkdir()
for label,out,source in [('base-javac',baseJ,S),('candidate-javac',J,C)]:run(label,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',out,*support,source/'bootstrap/java/util/Iterator.java',source/'bootstrap/java/util/AbstractCollection.java',source/'bootstrap/java/util/AbstractList.java',source/'bootstrap/java/util/ArrayList.java'],600)
material=lambda s,name:bytes.fromhex(re.search(r'function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',s)[1]);assert (baseJ/'java/util/ArrayList.class').read_bytes()==material(old,'ArrayList');images=[]
for index,name,binary in[(98,'ArrayList','ArrayList'),(115,'ArrayListItr','ArrayList$Itr')]:
 data=(J/('java/util/'+binary+'.class')).read_bytes();assert data==material(new,name);images.append({'index':index,'name':'java/util/'+binary,'bytes':len(data),'sha256':sha(data)})
assert not(J/'java/util/ArrayList$1.class').exists()
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==115 and len(rb['leaves'])==116 and [i for i in range(115)if ra['leaves'][i]!=rb['leaves'][i]]==[98]and ra['root']==basepins['bootstrapRoot']and rb['root']=='c1b50cfbeb974b541531c6f931ddc5ebc42b6047779525bfb99a72618848e97b'
for row in images:row['keccak256']=rb['leaves'][row['index']]
roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();shutil.copy2(C/role/(cn+'.sol'),q/(cn+'.sol'));shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']==431490 and roles['engine']['runtimeSHA256']=='4a25323e450c256efeee6a41519166a06c908beb8812dceca2c1e6c44238866a'and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and cs.count('MC-ARRAYLIST-ITERATOR-BOUNDED-1')==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
previous=json.load(open(P/'artifacts/parent-build-pins.json'));domain=re.search(r'PACKAGE_DOMAIN = keccak256\("([^\"]+)/package/v1"\)',cs)[1];driver=(P/'canonical-driver.go.txt').read_text();assert driver.count(previous['domain'])==6;driver=driver.replace(previous['domain'],domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={'profile':'MC-ARRAYLIST-ITERATOR-P52-PARENT','domain':domain,'basis':'accepted P51; ordinary private owner/cursor ArrayList iterator, no mutations','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':116,'baseBootstrapCount':115,'diagnosticClassBound':266,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':images,'globalNativeBindings':21,'stringLocalBinding':12,'rawLimits':[150,1063930],'checkpointCap':2097152,'maxCheckpointBytes':2097152,'address':basepins['address'],'owner':basepins['owner'],'reserve':25000000,'externalLocalGas':1000000000,'runtimeCap':1048576,'maxFrames':128,'sourceInvariants':{'onlyOldLeaf98Changed':True,'allOther114ImagesByteExact':True,'defaultIntConstructorJavaUnchanged':True,'ordinaryPrivateSizeAndBackingNotVirtualSize':True,'old105Through109ProgramSlotsPreserved':True,'noMutationGrowthNonemptyFailfastClaim':True,'ABIStorageCodecAndQuotasUnchanged':True,'native21String12Fixed':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old115Leaves':ra['leaves'],'new116Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[98],'changedSourceFunctions':changed,'addedSourceFunctions':added,'images':images,'baseArrayListSourceReproducesExactOldImage':True,'ABIStorageExact':True,'allQuotasAndNativeBindingsUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh P52 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
