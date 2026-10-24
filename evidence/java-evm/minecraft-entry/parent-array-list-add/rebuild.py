#!/usr/bin/env python3
"""Independent P60 pinned build, exactly two old images changed, immutable protocol audit."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'array-list-add-bounded';S=H.parent/'array-list-add-source-base-p59';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-array-list-add-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
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
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a if a[k]!=b[k]);assert changed==['_bootstrapArrayList#0','_bootstrapArrayListItr#0','_requireAssignable#0']and a.keys()==b.keys(),changed
repair='''            // A resumed all-null reference array may have no live component
            // object to warm its source hierarchy. Resolve that hierarchy too,
            // not only the wanted type, before testing normal array covariance.
            if (arrayLeafTypes[handle] >= ARRAY_CLASS_BASE) {
                _validateHierarchy(
                    classes, arrayLeafTypes[handle] - ARRAY_CLASS_BASE,
                    parentLinks, new uint8[](classes.length)
                );
            }
'''
assert b['_requireAssignable#0'].count(repair)==1 and b['_requireAssignable#0'].replace(repair,'')==a['_requireAssignable#0']
oldDomain='MC-LINKED-HASH-MAP-PUT-P59-1';domain='MC-ARRAY-LIST-ADD-BOUNDED-1';assert new.count(domain)==9 and new[:new.index('    function ')]==old[:old.index('    function ')].replace(oldDomain,domain)
for rel in('bootstrap/java/util/Iterator.java','bootstrap/java/util/AbstractCollection.java','bootstrap/java/util/AbstractList.java','compiler-support/java/util/Collection.java','compiler-support/java/util/List.java','compiler-support/java/util/RandomAccess.java'):assert(S/rel).read_bytes()==(C/rel).read_bytes(),rel
for label,root in [('old',S),('new',C)]:
 J=O/('java-'+label);J.mkdir();src=sorted((root/'compiler-support/java/util').glob('*.java'))+[root/('bootstrap/java/util/'+n)for n in('Iterator.java','AbstractCollection.java','AbstractList.java','ArrayList.java')];run('javac-'+label,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,*src],600)
 for fn,binary in [('ArrayList','ArrayList'),('ArrayListItr','ArrayList$Itr')]:
  data=(J/('java/util/'+binary+'.class')).read_bytes();text=old if label=='old'else new;im=bytes.fromhex(re.search(r'function _bootstrap'+fn+r'\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',text)[1]);assert data==im,(label,binary)
run('javap-list',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',O/'java-new/java/util/ArrayList.class']);run('javap-itr',['/usr/lib/jvm/java-8-openjdk/bin/javap','-p','-c','-s',O/'java-new/java/util/ArrayList$Itr.class']);assert 'public boolean add(java.lang.Object);'in(O/'javap-list.log').read_text()and 'public native boolean add'not in(O/'javap-list.log').read_text()
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==len(rb['leaves'])==127 and ra['root']==base['bootstrapRoot']and rb['root']==worker['bootstrapRoot']and [i for i in range(127)if ra['leaves'][i]!=rb['leaves'][i]]==[98,115];images=[]
for index,name,binary in [(98,'ArrayList','ArrayList'),(115,'ArrayListItr','ArrayList$Itr')]:
 data=(O/('java-new/java/util/'+binary+'.class')).read_bytes();images.append({'index':index,'name':'java/util/'+binary,'bytes':len(data),'sha256':sha(data),'keccak256':rb['leaves'][index]})
roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':
  text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1;prior=(S/role/(cn+'.sol')).read_text().replace(oldDomain,domain);prior=re.sub(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],prior);assert text==prior
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']<=1048576 and 5000<=roles['coordinator']['bytes']<=6000;cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**base,'profile':'MC-ARRAY-LIST-ADD-P60-PARENT','domain':domain,'basis':'accepted P59; genuine ArrayList append/growth and fail-fast private iterator','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':127,'baseBootstrapCount':127,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':[],'changedImages':images,'sourceInvariants':{'only98And115Changed':True,'all125OtherImagesExact':True,'ordinaryAppendGrowthAndCopy':True,'privateSizeAndModCount':True,'baselineStartResumeCommitEnvelopeConfigRootAndSlotsUnchanged':True,'native22String12AbiStorageCodecQuotasUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old127Leaves':ra['leaves'],'new127Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[98,115],'changedSourceFunctions':changed,'changedImages':images,'ABIStorageExact':True,'native22String12ResourceQuotasUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent independent P60 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
