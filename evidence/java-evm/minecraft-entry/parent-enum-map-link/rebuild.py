#!/usr/bin/env python3
"""Independent P58 exact123-prefix, real marker, old-slot and immutable-domain build."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'enum-map-link-bounded';S=H.parent/'enum-map-link-source-base-p57';O=Path(sys.argv[1]).resolve()
assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-enum-map-link-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));out={};ns={}
 for i,m in enumerate(ms):
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 key=ms[-1][1]+'#'+str(ns[ms[-1][1]]-1);out[key]=out[key][:-1].rstrip();return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);basepins=json.load(open(S/'pins.json'));workerpins=json.load(open(C/'pins.json'))
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);added=sorted(b.keys()-a.keys());assert changed==['_appendTailBootstraps#0','_bootstrapRoot#0','_isReservedEnumClass#0','_prepare#0']and added==['_bootstrapEnumMap#0']and not a.keys()-b.keys(),(changed,added)
oldDomain='MC-STRING-VALUEOF-CHAR-BOUNDED-1';domain='MC-ENUM-MAP-LINK-BOUNDED-1';assert new.count(domain)==9 and new[:new.index('    function ')]==old[:old.index('    function ')].replace(oldDomain,domain)
for offset,name in[(19,'Function'),(18,'NavigableMap'),(17,'Comparator'),(16,'SortedSet'),(15,'NavigableSet'),(8,'ReflectArray'),(7,'Collections'),(6,'SingletonList'),(5,'SingletonIterator'),(4,'Arrays'),(3,'ArraysArrayList'),(2,'ArraysArrayIterator')]:assert f'p.classes[count - {offset}] = _parseBundleClass(_bootstrap{name}());'in b['_prepare#0']
assert 'p.classes[classSlot + 84].data = _bootstrapEnumMap();'in b['_appendTailBootstraps#0']and 'bytes("java/util/EnumMap")'in b['_isReservedEnumClass#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_ARRAY_LENGTH',65536),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
J=O/'java-classes';J.mkdir();src=sorted((C/'bootstrap/java/util').glob('*.java'));run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-d',J,*src],600);data=(J/'java/util/EnumMap.class').read_bytes();im=bytes.fromhex(re.search(r'function _bootstrapEnumMap\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',new)[1]);assert data==im
run('javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',J/'java/util/EnumMap.class']);jp=(O/'javap.log').read_text();assert 'public class java.util.EnumMap extends java.util.AbstractMap implements java.io.Serializable,java.lang.Cloneable' in jp and 'private java.util.EnumMap();'in jp and jp.count('public native')==7 and jp.count('Code:')==1 and 'java/util/AbstractMap."<init>":()V'in jp and 'Signature:'not in jp
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==123 and len(rb['leaves'])==124 and ra['root']==basepins['bootstrapRoot']and ra['leaves']==rb['leaves'][:123]and rb['root']==workerpins['bootstrapRoot'];images=[{'index':123,'name':'java/util/EnumMap','bytes':len(data),'sha256':sha(data),'keccak256':rb['leaves'][123]}];roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']};assert roles[role]['runtimeSHA256']==workerpins[role]['runtimeSHA256']
assert roles['engine']['bytes']<=1048576 and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**basepins,'profile':'MC-ENUM-MAP-LINK-P58-PARENT','domain':domain,'basis':'accepted P57; one genuine EnumMap type marker only, no EnumMap instances/data','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':124,'baseBootstrapCount':123,'diagnosticClassBound':274,'maxClassIndexAtRaw150':273,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':images,'changedImages':[],'sourceInvariants':{'all123OldImagesExact':True,'old105Through122ActualProgramSlotsPreserved':True,'noEnumMapPublicCtorOrDataBehavior':True,'markerUsesRealHierarchyNotFalseShortcut':True,'baselineStartResumeCommitEnvelopeConfigRootAndStringGuardUnchanged':True,'native22String12AbiStorageCodecQuotasUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old123Leaves':ra['leaves'],'new124Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[],'changedSourceFunctions':changed,'addedSourceFunctions':added,'newImages':images,'ABIStorageExact':True,'native22String12ResourceQuotasUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh P58 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
