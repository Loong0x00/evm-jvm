#!/usr/bin/env python3
"""Reproducibly compile only guest platform HashMap/Node, stage, and build P39.
Host ZIP/JDK work is generated platform build-only; no original workload is read.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys
T=Path(__file__).resolve().parent;H=T.parent;ROOT=H.parents[3];BASE=H.parent/'hash-map-put-source-base-p38'
O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-hash-map-put-stage-') and not O.exists();O.mkdir()
env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1')
def sha(b):return hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with (O/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
source=H/'source/bootstrap/java/util/HashMap.java';assert 'throw new Error()' not in source.read_text() and 'newCap > 4096' not in source.read_text() and 'newThr = oldThr << 1' in source.read_text()
rt=O/'platform-build-rt.jar';shutil.copy2('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',rt);run('strip-platform',['zip','-q','-d',rt,'java/util/HashMap.class','java/util/HashMap$*.class'])
classes=O/'classes';classes.mkdir();run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-bootclasspath',rt,'-d',classes,source])
images={'HashMap':(classes/'java/util/HashMap.class').read_bytes(),'HashMapNode':(classes/'java/util/HashMap$Node.class').read_bytes()}
engine=H/'engine/MCEntryInterpreter.sol';s=engine.read_text()
for name,b in images.items():
 s,n=re.subn(r'(function _bootstrap'+name+r'\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})',r'\g<1>'+b.hex()+r'\g<2>',s);assert n==1,name
k=subprocess.check_output(['node','-e','const {keccak256:k}=require("js-sha3");console.log(k(Buffer.from(process.argv[1],"hex")))',images['HashMap'].hex()],cwd=ROOT,env=env,text=True).strip()
s,n=re.subn(r'(bytes32 private constant DBOOT_HASHMAP = hex")[0-9a-f]+(";)',r'\g<1>'+k+r'\g<2>',s);assert n==1;engine.write_text(s)
shutil.copy2(engine,O/'staged-engine.sol');shutil.copy2(source,O/'HashMap.java')
run('engine-build',['node',H/'engine/build.js'])
ea=json.load(open(H/'engine/MCEntryInterpreter.json'));ec=ea['codeHashes'];co=H/'coordinator/MCEntryCoordinator.sol';cs=co.read_text();cs,n=re.subn(r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]+(";)',r'\g<1>'+ec['runtimeKeccak256']+r'\g<2>',cs);assert n==1;co.write_text(cs);run('coordinator-build',['node',H/'coordinator/build.js']);ca=json.load(open(H/'coordinator/MCEntryCoordinator.json'))
spec=importlib.util.spec_from_file_location('p39_root',H/'reference/root_helper.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
dom=re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1];root=module.root_record(s,dom,ROOT,env)
bs=(BASE/'engine/MCEntryInterpreter.sol').read_text();oldDom=re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',bs)[1];old=module.root_record(bs,oldDom,ROOT,env)
assert len(old['leaves'])==104 and len(root['leaves'])==105 and [i for i in range(104) if old['leaves'][i]!=root['leaves'][i]]==[100]
prior=json.load(open(BASE/'pins.json'));pins={**prior,'profile':'MC-HASH-MAP-PUT-BOUNDED-P39','domain':'MC-HASH-MAP-PUT-BOUNDED-P39','basis':'accepted P38 source-only snapshot','bootstrapRoot':root['root'],'expectedBootstrapRoot':root['root'],'bootstrapCount':105,'baseBootstrapCount':104,'diagnosticClassBound':255,'engine':{'bytes':len(ea['deployedBytecode'])//2,**ec},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'sourceInvariants':{'allOther103PriorLeavesUnchanged':True,'changedPriorSlots':[100],'appendedNodeSlot':104,'globalNative21String12Unchanged':True,'onlyUnboundRefusalGuardAdded':True,'heapRawRuntimeAndCheckpointCapsUnchanged':True,'underlyingEVMUnchanged':True}}
(H/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
record={'status':'PASS staging/build; generated EVM/heap tests separate','engineSourceSHA256':sha(engine.read_bytes()),'coordinatorSourceSHA256':sha(co.read_bytes()),'javaSourceSHA256':sha(source.read_bytes()),'engineRuntimeSHA256':ec['runtimeSHA256'],'engineRuntimeBytes':pins['engine']['bytes'],'coordinatorRuntimeSHA256':ca['codeHashes']['runtimeSHA256'],'coordinatorRuntimeBytes':pins['coordinator']['bytes'],'bootstrapRoot':root['root'],'changedEngineFunctions':['_appendTailBootstraps#0','_bootstrapHashMap#0','_bootstrapRoot#0','_isReservedPlatformMapClass#0','_prepare#0'],'newEngineFunctions':['_bootstrapHashMapNode#0'],'bootstrapCount':105,'unchangedPriorLeaves':103,'images':{name:{'bytes':len(b),'sha256':sha(b)} for name,b in images.items()},'newOperationalNatives':0,'originalInputsRead':False,'draftThresholdBugCorrected':True}
(O/'stage-summary.json').write_text(json.dumps(record,indent=2)+'\n');(H/'stage-summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
