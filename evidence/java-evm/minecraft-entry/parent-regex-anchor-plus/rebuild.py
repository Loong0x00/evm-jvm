#!/usr/bin/env python3
"""Independent P42 Java/image/Solidity/root/ABI proof from accepted P41; no originals."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'regex-anchor-plus-bounded';S=H.parent/'regex-anchor-plus-source-base-p41';P=H.parent/'parent-max-arrays-8192';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-regex-build-parent-') and not O.exists();O.mkdir();(O/'tmp').mkdir()
env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
m=json.load(open(S/'source-manifest.json'))
for n,pin in m['files'].items():
 b=(S/n).read_bytes();assert len(b)==pin['bytes']and sha(b)==pin['sha256'],n
base=(S/'engine/MCEntryInterpreter.sol').read_text();candidate=(C/'engine/MCEntryInterpreter.sol').read_text()
def strip(s):
 for name in('Pattern','Matcher'):
  s,n=re.subn(r'(function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})',r'\g<1>IMAGE\g<2>',s);assert n==1
 return s
assert strip(candidate)==strip(base)
# Independently compile BOTH baseline and corrected source classes, preserve outputs.
for label,src in [('baseline',S/'bootstrap/java'),('candidate',C/'bootstrap/java')]:
 d=O/(label+'-classes');d.mkdir();files=[src/'util/regex'/n for n in('Pattern.java','Matcher.java','PatternSyntaxException.java')]+[src/'lang/String.java'];run(label+'-javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',d,*files],600)
for name,path in [('Pattern','java/util/regex/Pattern.class'),('Matcher','java/util/regex/Matcher.class'),('PatternSyntaxException','java/util/regex/PatternSyntaxException.class'),('String','java/lang/String.class')]:
 old=(O/'baseline-classes'/path).read_bytes();expect=bytes.fromhex(re.search(r'function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";',base)[1]);assert old==expect,name
 new=(O/'candidate-classes'/path).read_bytes()
 if name not in('Pattern','Matcher'):assert new==old,name
 else:
  candidate,n=re.subn(r'(function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})',r'\g<1>'+new.hex()+r'\g<2>',candidate);assert n==1
assert strip(candidate)==strip(base)
from root_helper import root_record
domain='JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1';a=root_record(base,domain,ROOT,env);b=root_record(candidate,domain,ROOT,env);assert len(a['leaves'])==len(b['leaves'])==105 and [i for i in range(105)if a['leaves'][i]!=b['leaves'][i]]==[101,103]
roles={};E=O/'engine';E.mkdir();(E/'MCEntryInterpreter.sol').write_text(candidate);shutil.copy2(P/'artifacts/engine/build.js',E/'build.js');run('engine-build',['node',E/'build.js']);ea=json.load(open(E/'MCEntryInterpreter.json'));old=json.load(open(S/'engine/MCEntryInterpreter.json'));assert ea['abi']==old['abi']and ea['storageLayout']==old['storageLayout'];roles['engine']={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert roles['engine']['bytes']<=1048576
CO=O/'coordinator';CO.mkdir();cs=(S/'coordinator/MCEntryCoordinator.sol').read_text();prior=json.load(open(P/'artifacts/parent-build-pins.json'));cs=cs.replace(prior['engine']['runtimeKeccak256'],roles['engine']['runtimeKeccak256']);(CO/'MCEntryCoordinator.sol').write_text(cs);shutil.copy2(P/'artifacts/coordinator/build.js',CO/'build.js');run('coordinator-build',['node',CO/'build.js']);ca=json.load(open(CO/'MCEntryCoordinator.json'));old=json.load(open(S/'coordinator/MCEntryCoordinator.json'));assert ca['abi']==old['abi']and ca['storageLayout']==old['storageLayout'];roles['coordinator']={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']};assert roles['coordinator']['bytes']<=24576
# Protocol domain deliberately remains P41; codehash+changed bootstrap root distinguish P42.
actualDomain=prior['domain'];driver=(P/'canonical-driver.go.txt').read_text()
for name,v in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:
 driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',r'\g<1>'+v+r'\g<2>',driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes']),('run',roles['engine']['bytes'])]:
 driver,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),driver);assert n==1
assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**prior,'profile':'MC-REGEX-ANCHOR-PLUS-P42-PARENT-FIX','domain':actualDomain,'basis':'accepted P41 source-only snapshot; Pattern/Matcher only + parent fixed-width guard correction','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapRoot':b['root'],'expectedBootstrapRoot':b['root'],'orderedBootstrapLeaves':b['leaves'],'externalLocalGas':1000000000,'generatedRegexTestBudgetMax':8000000000,'sourceInvariants':{'changedImageSlots':[101,103],'other103ImagesUnchanged':True,'ABIStorageAndAllQuotasUnchanged':True,'native21String12Unchanged':True,'protocolDomainRetainedCodehashAndRootUpdated':True,'noCheckpointSchemaChange':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');proof={'baseRoot':a['root'],'root':b['root'],'leaves':b['leaves'],'changedSlots':[101,103],'count':105,'other103LeavesUnchanged':True,'StringAndPSEUnchanged':True,'freshJavaImagesMatchP41Baseline':True,'sourceOutsideTwoMaterializersUnchanged':True,'ABIStorageExact':True,'allQuotasAndNativeBindingsFixed':True,'protocolDomain':actualDomain,'profileLabel':pins['profile'],'correctedPatternSourceSHA256':sha((C/'bootstrap/java/util/regex/Pattern.java').read_bytes()),'engineSourceSHA256':sha(candidate.encode()),'coordinatorSourceSHA256':sha(cs.encode())};(O/'root-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':'fresh parent P42 build passed','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapRoot':b['root']},indent=2))
