#!/usr/bin/env python3
"""Independent LOCAL raw160 admission-only build; engine layout and external ABI unchanged."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];C=H.parent/'raw160-bounded';S=H.parent/'raw160-source-base-p61';O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build'and O.name.startswith('java-diff-mc-raw160-build-parent-')and not O.exists();O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1');sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with(O/(label+'.log')).open('w')as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True);base=json.load(open(S/'pins.json'));worker=json.load(open(C/'pins.json'))
for name,pin in json.load(open(S/'source-manifest.json'))['files'].items():
 b=(S/name).read_bytes();assert len(b)==pin['bytes']and sha(b)==pin['sha256'],name
old=(S/'engine/MCEntryInterpreter.sol').read_text();new=(C/'engine/MCEntryInterpreter.sol').read_text();oldDomain='MC-SUPPLIER-LINK-BOUNDED-1';domain='MC-RAW160-BOUNDED-1';expected=old.replace(oldDomain,domain);expected,n=re.subn(r'(MAX_RAW_CLASSES = )150;',r'\g<1>160;',expected);assert n==1;expected,n=re.subn(r'uint32\(150\), uint32\(1063930\)',r'uint32(160), uint32(1063930)',expected);assert n==1 and expected==new and new.count(domain)==9
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(new,getdom(new),ROOT,env);assert len(ra['leaves'])==len(rb['leaves'])==128 and ra['root']==base['bootstrapRoot']and ra['leaves']==rb['leaves']and rb['root']==worker['bootstrapRoot'];roles={};layout_notes=[]
for role,cn in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 q=O/role;q.mkdir();text=(C/role/(cn+'.sol')).read_text()
 if role=='coordinator':
  text,n=re.subn(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],text);assert n==1;prior=(S/role/(cn+'.sol')).read_text().replace(oldDomain,domain);prior=re.sub(r'(ENGINE_CODEHASH = hex")[0-9a-f]+(";)',lambda m:m[1]+roles['engine']['runtimeKeccak256']+m[2],prior)
  for typ in('address','bytes32','uint32','bytes'):prior,n=re.subn(re.escape(typ)+r'\[150\]',typ+'[160]',prior);assert n==1
  prior,n=prior.replace('n > 150','n > 160'),prior.count('n > 150');assert n==1 and text==prior
 (q/(cn+'.sol')).write_text(text);shutil.copy2(S/role/'build.js',q/'build.js');run(role+'-build',['node',q/'build.js']);j=json.load(open(q/(cn+'.json')));prior=json.load(open(S/role/(cn+'.json')));assert j['abi']==prior['abi'];roles[role]={'bytes':len(j['deployedBytecode'])//2,**j['codeHashes']};assert roles[role]['runtimeSHA256']==worker[role]['runtimeSHA256']
 if role=='engine':assert j['storageLayout']==prior['storageLayout']
 else:
  a,b=prior['storageLayout'],j['storageLayout'];assert len(a['storage'])==len(b['storage']);shift=0
  for x,y in zip(a['storage'],b['storage']):
   for key in('label','offset','contract'):assert x[key]==y[key]
   label=x['label'];assert int(y['slot'])==int(x['slot'])+shift,(label,x['slot'],y['slot'],shift)
   if label in('decoders','classRoots','classSizes','rawNames'):
    assert y['type']==x['type'].replace(')150_storage',')160_storage');delta=1 if label=='classSizes'else 10;shift+=delta;layout_notes.append({'label':label,'oldSlot':x['slot'],'newSlot':y['slot'],'oldType':x['type'],'newType':y['type'],'extentSlotDelta':delta})
   else:assert x['type']==y['type']
  assert shift==31
assert roles['engine']['bytes']<=1048576 and 5000<=roles['coordinator']['bytes']<=6000;cs=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert cs.count(domain)==4 and 'uint8 public classCount;'in cs and 'n > 160'in cs
# Canonical1B transport changed only domain, actual pins/lengths and host raw-count guard.
driver=(S/'canonical-driver.go.txt').read_text();assert driver.count(oldDomain)==6;driver=driver.replace(oldDomain,domain)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:driver,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',lambda m:m[1]+value+m[2],driver);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('run',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes'])]:driver,n=re.subn(r'(len\('+name+r'\) != )\d+',lambda m:m[1]+str(size),driver);assert n==1
assert driver.count('len(parts) > 150')==1 and driver.count('len(m.Decoders) > 150')==1;driver=driver.replace('len(parts) > 150','len(parts) > 160').replace('len(m.Decoders) > 150','len(m.Decoders) > 160');assert 'const ordinaryGas = uint64(1_000_000_000)'in driver and 'decoder.UseNumber()'in driver;(O/'main.go').write_text(driver);run('gofmt',['gofmt','-w',O/'main.go']);run('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go'],900);run('go-vet',['go','vet',O/'main.go'],900);shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**base,'profile':'MC-RAW160-P62-PARENT','domain':domain,'basis':'accepted P61; measured necessary151-class hierarchy, explicitLOCALraw160 admission only','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapCount':128,'baseBootstrapCount':128,'diagnosticClassBound':288,'maxClassIndexAtRaw160':287,'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'rawLimits':[160,1063930],'newImages':[],'changedImages':[],'sourceInvariants':{'all128BootstrapImagesExact':True,'onlyRawCountLimitValueAndDomainsChangedInVm':True,'engineStorageExternalCoordinatorAbiAndCheckpointCodecUnchanged':True,'newCoordinatorPrivateArrayExtents160AndFollowingSlotsPlus31':True,'noCrossProfileStorageMigration':True,'limitVectorFirst160OtherTenFixedFlat13EncodingUnchanged':True,'native22String12AndAllOtherQuotasGetHRulesUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'root-audit.json').write_text(json.dumps({'status':'PASS','old128Leaves':ra['leaves'],'new128Leaves':rb['leaves'],'root':rb['root'],'changedOldLeaves':[],'vmSourceDelta':'MAX_RAW_CLASSES150->160 and limits vector first150->160; domains only','coordinatorNecessaryPrivateStorageExtentChanges':layout_notes,'followingSlotShift':31,'externalABIAndEngineStorageExact':True,'noJavaOrDispatchChange':True},indent=2)+'\n');print(json.dumps({'status':'parent independent raw160 build passed',**roles,'bootstrapRoot':rb['root'],'privateCoordinatorSlotShift':31,'actualProtocolDomain':domain},indent=2))
