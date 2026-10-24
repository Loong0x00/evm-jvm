#!/usr/bin/env python3
"""Independent P57 build with exact old-image/old-Code audit and isolated protocol domains."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'string-valueof-char-bounded';S=H.parent/'string-valueof-char-source-base-p56';O=Path(sys.argv[1]).resolve()
assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-string-valueof-char-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir()
env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 ms=list(re.finditer(r'^    function (\w+)\(',s,re.M));out={};ns={}
 for i,m in enumerate(ms):
  n=ns.get(m[1],0);ns[m[1]]=n+1;out[m[1]+'#'+str(n)]=s[m.start():ms[i+1].start()if i+1<len(ms)else len(s)].strip()
 key=ms[-1][1]+'#'+str(ns[ms[-1][1]]-1);out[key]=out[key][:-1].rstrip();return out
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);basepins=json.load(open(S/'pins.json'))
for n,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 data=(S/n).read_bytes();assert len(data)==pin['bytes']and sha(data)==pin['sha256'],n
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();a,b=funcs(old),funcs(new);changed=sorted(k for k in a.keys()&b.keys()if a[k]!=b[k]);assert changed==['_bootstrapString#0','_resolveCall#0']and a.keys()==b.keys(),changed
oldDomain='MC-ARRAYS-AS-LIST-BOUNDED-1';domain='MC-STRING-VALUEOF-CHAR-BOUNDED-1';assert new.count(domain)==9;assert new[:new.index('    function ')]==old[:old.index('    function ')].replace(oldDomain,domain)
guard=b['_resolveCall#0'];assert 'bool p57StringValueOfChar = !interfaceReference' in guard and 'bytes("java/lang/String")'in guard and 'bytes("valueOf")'in guard and 'bytes("(C)Ljava/lang/String;")'in guard and 'if (!p57StringValueOfChar)'in guard
# This replacement must be the only resolver semantic change.
prior='''        // LB0 exposes no static API on any of its three reserved String-profile types.
        if (_isStringProfileSymbolic(classes[owner])) {
            _rejectStringProfileCall(caller.data, descriptorOffset, descriptorLength, pc);
        }'''
start=guard.index('        // P57 exposes only');end=guard.index('\n\n        if (interfaceReference)',start);assert guard[:start]+prior+guard[end:]==a['_resolveCall#0']
for key,n in [('MAX_RAW_CLASSES',150),('MAX_RAW_BYTES',1063930),('MAX_ARRAYS',8192),('MAX_OBJECTS',4096),('MAX_ARRAY_ELEMENTS',262144),('MAX_ARRAY_LENGTH',65536),('MAX_FRAMES',128)]:assert re.search(r'constant '+key+r'\s*=\s*'+str(n)+r';',new),key
for label,src in [('old',S/'bootstrap/java/lang/String.java'),('new',C/'bootstrap/java/lang/String.java')]:
 J=O/('java-'+label);J.mkdir();run('javac-'+label,['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',J,src],600);data=(J/'java/lang/String.class').read_bytes();embedded=bytes.fromhex(re.search(r'function _bootstrapString\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',old if label=='old'else new)[1]);assert data==embedded
run('old-code-audit',[sys.executable,'-B',C/'audit_class.py',O/'java-old/java/lang/String.class',O/'java-new/java/lang/String.class'],600)
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==len(rb['leaves'])==123 and ra['root']==basepins['bootstrapRoot'];assert [i for i in range(123)if ra['leaves'][i]!=rb['leaves'][i]]==[26]
image=(O/'java-new/java/lang/String.class').read_bytes();images=[{'index':26,'name':'java/lang/String','bytes':len(image),'sha256':sha(image),'keccak256':rb['leaves'][26]}];roles={}
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi']and j['storageLayout']==prior['storageLayout'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']}
assert roles['engine']['bytes']<=1048576 and roles['coordinator']['bytes']==5411
cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert 'ENGINE_CODEHASH = hex"'+roles['engine']['runtimeKeccak256']+'"'in cs and cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 150'in cs
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**basepins,'profile':'MC-STRING-VALUEOF-CHAR-P57-PARENT','domain':domain,'basis':'accepted P56; only ordinary one-UTF16-unit String.valueOf(char) and exact symbolic-call permission','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':123,'baseBootstrapCount':123,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'newImages':[],'changedImages':images,'sourceInvariants':{'exactlyLeaf26Changed':True,'all122OtherImagesExact':True,'oldStringMethodCodeFieldsAndBridgesPreserved':True,'ordinaryValueOfCharOnly':True,'baselineStartResumeCommitEnvelopeConfigRootUnchanged':True,'actualProgramAssemblyUnchanged':True,'native22String12AbiStorageCodecQuotasUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old123Leaves':ra['leaves'],'new123Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[26],'changedSourceFunctions':changed,'changedImages':images,'ABIStorageExact':True,'native22String12ResourceQuotasUnchanged':True},indent=2)+'\n');print(json.dumps({'status':'parent fresh isolated P57 build passed',**roles,'bootstrapRoot':rb['root'],'actualProtocolDomain':domain},indent=2))
