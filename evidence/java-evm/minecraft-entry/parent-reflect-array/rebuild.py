#!/usr/bin/env python3
"""Independent P53 binding22 source/Java/root/ABI/storage/pinned build audit."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'reflect-array-newinstance-bounded';S=H.parent/'reflect-array-source-base-p52';P=H.parent/'parent-array-list-iterator';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-reflect-array-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
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
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);added=sorted(b.keys()-a.keys());assert changed==['_bootstrapRoot#0','_execute#0','_loadNativeCallee#0','_nativeBinding#0','_prepare#0','_validateNativeBinding#0']and added==['_bootstrapReflectArray#0']and not a.keys()-b.keys(),(changed,added)
# Removing exactly the added binding22 block restores the old entire executor.
s=b['_execute#0'];begin=s.index('                    if (nativeBinding == 22) {');brace=s.index('{',begin);balance=1;at=brace+1
while balance:
 balance+=(s[at]=='{')-(s[at]=='}');at+=1
norm=lambda s:'\n'.join(x.rstrip()for x in s.splitlines()if x.strip());assert norm(s[:begin]+s[at:])==norm(a['_execute#0'])
assert new.count('MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1')==9 and 'bytes("java/lang/reflect/Array")'in b['_prepare#0']
for offset,name in[(12,'Function'),(11,'NavigableMap'),(10,'Comparator'),(9,'SortedSet'),(8,'NavigableSet')]:assert f'p.classes[count - {offset}] = _parseBundleClass(_bootstrap{name}());'in b['_prepare#0']
assert 'p.classes[count - 1] = _parseBundleClass(_bootstrapReflectArray());'in b['_prepare#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_ARRAY_LENGTH',65536),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
assert 'binding == 12 || binding == 22'in b['_validateNativeBinding#0']and 'access != 0x010a'in b['_validateNativeBinding#0'];assert 's.argumentKinds.length != 2'in b['_loadNativeCallee#0']and 's.argumentKinds[1] != KIND_INT'in b['_loadNativeCallee#0']
J=O/'java-classes';J.mkdir();run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-d',J,C/'java/lang/reflect/Array.java'],600);data=(J/'java/lang/reflect/Array.class').read_bytes();embedded=bytes.fromhex(re.search(r'function _bootstrapReflectArray\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',new)[1]);assert data==embedded and len(data)==477 and sha(data)=='be9db74abc11c9fb3ffc60a1f69191332df180fc0cdff73ddef720ad493713b9'
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==116 and len(rb['leaves'])==117 and ra['leaves']==rb['leaves'][:116]and ra['root']==basepins['bootstrapRoot']
roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']<=1048576 and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and cs.count('MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1')==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
previous=json.load(open(P/'artifacts/parent-build-pins.json'));domain=re.search(r'PACKAGE_DOMAIN = keccak256\("([^\"]+)/package/v1"\)',cs)[1];driver=(P/'canonical-driver.go.txt').read_text();assert driver.count(previous['domain'])==6;driver=driver.replace(previous['domain'],domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
image={'index':116,'name':'java/lang/reflect/Array','bytes':len(data),'sha256':sha(data),'keccak256':rb['leaves'][116]};pins={'profile':'MC-REFLECT-ARRAY-NEWINSTANCE-P53-PARENT-ISOLATED','domain':domain,'basis':'accepted P52; only additional owned binding22 performs rank1 reference-array allocation','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':117,'baseBootstrapCount':116,'diagnosticClassBound':267,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':[image],'globalNativeBindings':22,'stringLocalBinding':12,'rawLimits':[150,1063930],'checkpointCap':2097152,'maxCheckpointBytes':2097152,'address':basepins['address'],'owner':basepins['owner'],'reserve':25000000,'externalLocalGas':1000000000,'runtimeCap':1048576,'maxFrames':128,'sourceInvariants':{'all116OldImagesByteExact':True,'oldExecutorExactAfterRemovingOnlyBinding22Block':True,'oneExactPrivateStaticNative22Added':True,'noComponentInitializationOrConstructors':True,'sameExistingArrayQuotaAndArenaPath':True,'old105Through109ProgramSlotsPreserved':True,'ABIStorageCodecAndResourceQuotasUnchanged':True,'oldGlobal1Through21AndString12BehaviorPreserved':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old116Leaves':ra['leaves'],'new117Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[],'changedSourceFunctions':changed,'addedSourceFunctions':added,'newImage':image,'ABIStorageExact':True,'resourceQuotasAndOldNativeBehaviorUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh isolated P53 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
