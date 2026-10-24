#!/usr/bin/env python3
"""Independent Supplier Java8 SAM, exact127-prefix and protocol-only P61 integration build."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'supplier-link-bounded';S=H.parent/'supplier-link-source-base-p60';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-supplier-link-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 mask=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',lambda m:' '*(m.end()-m.start()),s,flags=re.S);out={};ns={}
 for m in re.finditer(r'\bfunction\s+(\w+)\s*\(',mask):
  i=mask.index('{',m.end());d=1;j=i+1
  while d:d+=(mask[j]=='{')-(mask[j]=='}');j+=1
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():j]
 return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);base=json.load(open(S/'pins.json'));worker=json.load(open(C/'pins.json'))
for name,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 b=(S/name).read_bytes();assert len(b)==pin['bytes']and sha(b)==pin['sha256'],name
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a if a[k]!=b[k]);assert changed==['_appendTailBootstraps#0','_bootstrapRoot#0','_prepare#0']and sorted(b.keys()-a.keys())==['_bootstrapSupplier#0']and not a.keys()-b.keys(),changed
oldDomain='MC-ARRAY-LIST-ADD-BOUNDED-1';domain='MC-SUPPLIER-LINK-BOUNDED-1';assert new.count(domain)==9 and new[:new.index('    function ')]==old[:old.index('    function ')].replace(oldDomain,domain)
for offset,name in[(23,'Function'),(22,'NavigableMap'),(21,'Comparator'),(20,'SortedSet'),(19,'NavigableSet'),(12,'ReflectArray'),(11,'Collections'),(10,'SingletonList'),(9,'SingletonIterator'),(8,'Arrays'),(7,'ArraysArrayList'),(6,'ArraysArrayIterator')]:assert f'p.classes[count - {offset}] = _parseBundleClass(_bootstrap{name}());'in b['_prepare#0']
for slot,name in[(84,'EnumMap'),(85,'LinkedHashMapEntry'),(86,'LinkedHashMapEntrySet'),(87,'LinkedHashMapEntryIterator'),(88,'Supplier')]:assert f'p.classes[classSlot + {slot}].data = _bootstrap{name}();'in b['_appendTailBootstraps#0']
assert 'bytes("java/util/function/Supplier")'in b['_prepare#0'];J=O/'java-classes';J.mkdir();run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,C/'java/bootstrap/java/util/function/Supplier.java'],600);data=(J/'java/util/function/Supplier.class').read_bytes();embed=bytes.fromhex(re.search(r'function _bootstrapSupplier\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',new)[1]);assert data==embed
run('javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-v','-s',J/'java/util/function/Supplier.class']);jp=(O/'javap.log').read_text();assert 'ACC_PUBLIC, ACC_INTERFACE, ACC_ABSTRACT'in jp and 'public abstract T get();'in jp and jp.count('descriptor:')==1 and 'descriptor: ()Ljava/lang/Object;'in jp and 'ACC_PUBLIC, ACC_ABSTRACT'in jp and 'Code:'not in jp and 'ACC_NATIVE'not in jp
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==127 and len(rb['leaves'])==128 and ra['root']==base['bootstrapRoot']and ra['leaves']==rb['leaves'][:127]and rb['root']==worker['bootstrap']['newRoot'];images=[{'index':127,'name':'java/util/function/Supplier','bytes':len(data),'sha256':sha(data),'keccak256':rb['leaves'][127]}];roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':
  text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1;prior=(S/role/(cn+'.sol')).read_text().replace(oldDomain,domain);prior=re.sub(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],prior);assert text==prior
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']};assert roles[role]['runtimeSHA256']==worker[role]['runtimeSHA256']
assert roles['engine']['bytes']<=1048576 and 5000<=roles['coordinator']['bytes']<=6000;cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**base,'profile':'MC-SUPPLIER-LINK-P61-PARENT','domain':domain,'basis':'accepted P60; genuine Java8 Supplier<T> interface SAM only','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':128,'baseBootstrapCount':127,'diagnosticClassBound':278,'maxClassIndexAtRaw150':277,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':images,'changedImages':[],'sourceInvariants':{'all127OldImagesExact':True,'old105Through126ActualSlotsPreserved':True,'noSupplierGetResultNativeOrDispatchShortcut':True,'baselineColdArrayFixStartResumeCommitEnvelopeConfigRootUnchanged':True,'native22String12AbiStorageCodecQuotasUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old127Leaves':ra['leaves'],'new128Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[],'changedSourceFunctions':changed,'newImages':images,'ABIStorageExact':True,'native22String12ResourceQuotasUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent independent P61 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
