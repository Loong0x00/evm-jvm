#!/usr/bin/env python3
"""Independent P59 pinned Java8/solc build with bounded helper scope corrections."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'linked-hash-map-put-bounded';S=H.parent/'linked-hash-map-put-source-base-p58';O=Path(sys.argv[1]).resolve()
assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-linked-map-put-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 # Source-only balanced function spans, excluding trailing structs/contract footer.
 mask=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27',lambda m:' '*(m.end()-m.start()),s,flags=re.S);out={};ns={}
 for m in re.finditer(r'\bfunction\s+(\w+)\s*\(',mask):
  at=mask.index('{',m.end());depth=1;end=at+1
  while depth:
   depth+=(mask[end]=='{')-(mask[end]=='}');end+=1
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():end]
 return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);basepins=json.load(open(S/'pins.json'))
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);expected=['_appendTailBootstraps#0','_bootstrapLinkedHashMap#0','_bootstrapRoot#0','_prepare#0'];assert sorted(k for k in a.keys()&b.keys()if a[k]!=b[k])==expected and sorted(b.keys()-a.keys())==['_bootstrapLinkedHashMapEntry#0','_bootstrapLinkedHashMapEntryIterator#0','_bootstrapLinkedHashMapEntrySet#0'] and not a.keys()-b.keys()
oldDomain='MC-ENUM-MAP-LINK-BOUNDED-1';domain='MC-LINKED-HASH-MAP-PUT-P59-1';assert new.count(domain)==9 and new[:new.index('    function ')]==old[:old.index('    function ')].replace(oldDomain,domain)
for offset,name in[(22,'Function'),(21,'NavigableMap'),(20,'Comparator'),(19,'SortedSet'),(18,'NavigableSet'),(11,'ReflectArray'),(10,'Collections'),(9,'SingletonList'),(8,'SingletonIterator'),(7,'Arrays'),(6,'ArraysArrayList'),(5,'ArraysArrayIterator')]:assert f'p.classes[count - {offset}] = _parseBundleClass(_bootstrap{name}());'in b['_prepare#0']
for slot,name in[(84,'EnumMap'),(85,'LinkedHashMapEntry'),(86,'LinkedHashMapEntrySet'),(87,'LinkedHashMapEntryIterator')]:assert f'p.classes[classSlot + {slot}].data = _bootstrap{name}();'in b['_appendTailBootstraps#0']
for n in('LinkedHashMapEntry','LinkedHashMapEntrySet','LinkedHashMapEntryIterator'):assert 'bytes("java/util/'+n+'")'in b['_prepare#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_ARRAY_LENGTH',65536),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
for name in('HashMap','Map','Collection','AbstractCollection','Iterator','AbstractMap','AbstractSet','Set'):assert(S/'bootstrap/java/util'/(name+'.java')).read_bytes()==(C/'bootstrap/java/util'/(name+'.java')).read_bytes(),name
oldJ=O/'java-old';oldJ.mkdir();run('javac-old',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',oldJ,S/'bootstrap/java/util/LinkedHashMap.java'],600);before=(oldJ/'java/util/LinkedHashMap.class').read_bytes();assert before==bytes.fromhex(re.search(r'function _bootstrapLinkedHashMap\(\).*?return hex"([0-9a-f]+)";',old,re.S)[1])
ctx=O/'context/java/util';ctx.mkdir(parents=True);J=O/'java-new';J.mkdir()
for src in(C/'bootstrap/java/util').glob('*.java'):
 text=src.read_text()
 # Remove compile-only annotations instead of introducing fabricated Map default bodies.
 if src.name=='HashMap.java':text=text.replace('@Override','')
 (ctx/src.name).write_text(text)
run('javac-new',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,*sorted(ctx.glob('*.java'))],600);images=[]
for index,name in[(113,'LinkedHashMap'),(124,'LinkedHashMapEntry'),(125,'LinkedHashMapEntrySet'),(126,'LinkedHashMapEntryIterator')]:
 data=(J/('java/util/'+name+'.class')).read_bytes();pat=r'(function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\)\s*\{\s*return hex")[0-9a-f]+(";)';new,n=re.subn(pat,lambda m:m[1]+data.hex()+m[2],new);assert n==1;images.append({'index':index,'name':'java/util/'+name,'bytes':len(data),'sha256':sha(data)})
run('javap-view',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',J/'java/util/LinkedHashMapEntrySet.class']);jp=(O/'javap-view.log').read_text();assert re.search(r'public native boolean add\(E\);\s*descriptor: \(Ljava/lang/Object;\)Z',jp) and jp.count(' add(')==1 and 'checkcast'not in jp and 'Field java/util/LinkedHashMap.size:I'in jp
run('javap-map',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',J/'java/util/LinkedHashMap.class']);assert 'final java.util.LinkedHashMapEntry<K, V> firstEntry();'in(O/'javap-map.log').read_text()
run('javap-entry',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',J/'java/util/LinkedHashMapEntry.class']);assert 'public native boolean equals(java.lang.Object);'in(O/'javap-entry.log').read_text()
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==124 and len(rb['leaves'])==127 and ra['root']==basepins['bootstrapRoot']and [i for i in range(124)if ra['leaves'][i]!=rb['leaves'][i]]==[113]
for image in images:image['keccak256']=rb['leaves'][image['index']]
roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=new if role=='engine'else(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':
  prior=(S/role/(cn+'.sol')).read_text().replace(oldDomain,domain);text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1;prior=re.sub(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],prior);assert text==prior
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']<=1048576 and 5000<=roles['coordinator']['bytes']<=6000
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**basepins,'profile':'MC-LINKED-HASH-MAP-PUT-P59-PARENT','domain':domain,'basis':'accepted P58; approved real ordered-entry backend; parent fixes erased view guard, private size, final accessor, unadmitted entry equality and pinned Java8','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':127,'baseBootstrapCount':124,'diagnosticClassBound':277,'maxClassIndexAtRaw150':276,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':images[1:],'changedImages':images[:1],'sourceInvariants':{'onlyOld113Changes':True,'all123OtherOldImagesExact':True,'old105Through123ActualProgramSlotsPreserved':True,'realOwnedEntryBackendNotInheritedBuckets':True,'parentSourceCorrections':True,'baselineStartResumeCommitEnvelopeConfigRootAndStringGuardUnchanged':True,'native22String12AbiStorageCodecQuotasUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old124Leaves':ra['leaves'],'new127Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[113],'changedSourceFunctions':expected,'newImages':images,'ABIStorageExact':True,'native22String12ResourceQuotasUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh corrected P59 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
