#!/usr/bin/env python3
"""Fresh P39 parent build; exact scoped source, ordered images and ABI/storage proof."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];CAND=H.parent/'hash-map-put-bounded';BASE=H.parent/'parent-string-replaceall'
I=json.load(open(H/'acceptance-input.json'));O=Path(sys.argv[1]).resolve();assert O.parent==ROOT/'build' and O.name.startswith('java-diff-mc-hash-map-put-build-parent-') and not O.exists()
subprocess.run(['git','diff','--exit-code','95665d570','HEAD','--','core/vm','core/state','params'],cwd=ROOT,check=True)
O.mkdir();(O/'tmp').mkdir();env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),TMPDIR=str(O/'tmp'),GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',PYTHONDONTWRITEBYTECODE='1')
def sha(b):return hashlib.sha256(b).hexdigest()
def run(label,args,timeout=1200):
 with (O/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
def funcs(s):
 matches=list(re.finditer(r'^    function ([A-Za-z0-9_]+)\(',s,re.M));result={};counts={}
 for j,m in enumerate(matches):
  name=m[1];n=counts.get(name,0);counts[name]=n+1;result[f'{name}#{n}']=s[m.start():matches[j+1].start() if j+1<len(matches) else len(s)].strip()
 return result
def layout(x):
 def typ(k,seen=()):
  t=x['types'][k];o={z:t[z] for z in ('encoding','label','numberOfBytes') if z in t}
  if k in seen:return o
  for z in ('key','value','base'):
   if z in t:o[z]=typ(t[z],seen+(k,))
  if 'members'in t:o['members']=[{**{z:r[z] for z in ('label','offset','slot')},'type':typ(r['type'],seen+(k,))} for r in t['members']]
  return o
 return [{**{z:r[z] for z in ('contract','label','offset','slot')},'type':typ(r['type'])} for r in x['storage']]
old=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text();source=(CAND/'engine/MCEntryInterpreter.sol').read_text();assert sha(source.encode())==I['engineSourceSHA256']
a,b=funcs(old),funcs(source);changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]);added=sorted(b.keys()-a.keys());removed=sorted(a.keys()-b.keys());assert not removed
assert changed==I['changedEngineFunctions'] and added==I['newEngineFunctions'],(changed,added)
for name in ('_execute','_resolveVirtual','_nativeBinding','_stringNativeBinding','_vfsNativeBinding'):assert all(a[k]==b[k] for k in a if k.split('#')[0]==name)
from root_helper import root_record
getdom=lambda s:re.search(r'bytes32 private constant DBOOT\s*=\s*keccak256\("([^\"]+)"\)',s)[1]
ra=root_record(old,getdom(old),ROOT,env);rb=root_record(source,getdom(source),ROOT,env)
prior=json.load(open(BASE/'artifacts/parent-build-pins.json'));assert ra['root']==prior['bootstrapRoot'] and len(ra['leaves'])==104 and len(rb['leaves'])==105
assert [i for i in range(104) if ra['leaves'][i]!=rb['leaves'][i]]==[100];assert rb['root']==I['bootstrapRoot']
roles={}
for role,contract in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 d=O/role;d.mkdir();src=CAND/role/(contract+'.sol');assert sha(src.read_bytes())==I[role+'SourceSHA256'];shutil.copy2(src,d/src.name);shutil.copy2(BASE/'artifacts'/role/'build.js',d/'build.js');run(role+'-build',['node',d/'build.js'])
 art=json.load(open(d/(contract+'.json')));oldart=json.load(open(BASE/'artifacts'/role/(contract+'.json')));runtime=bytes.fromhex(art['deployedBytecode'].removeprefix('0x'))
 assert art['abi']==oldart['abi'] and layout(art['storageLayout'])==layout(oldart['storageLayout'])
 assert sha(runtime)==I[role+'RuntimeSHA256'] and len(runtime)==I[role+'RuntimeBytes'];roles[role]={'bytes':len(runtime),**art['codeHashes']}
 assert len(runtime)<=(1048576 if role=='engine' else 24576)
co=(O/'coordinator/MCEntryCoordinator.sol').read_text();assert roles['engine']['runtimeKeccak256'] in co
profile='MC-HASH-MAP-PUT-BOUNDED-P39';d=(BASE/'canonical-driver.go.txt').read_text();assert d.count(prior['domain'])==6;d=d.replace(prior['domain'],profile)
for name,value in [('immutableEngineSHA256',roles['engine']['runtimeSHA256']),('immutableEngineKeccak','0x'+roles['engine']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+roles['coordinator']['runtimeKeccak256'])]:
 d,n=re.subn(r'(const '+name+r' = ")[^\"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,size in [('engineRun',roles['engine']['bytes']),('coordRun',roles['coordinator']['bytes']),('run',roles['engine']['bytes'])]:
 d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
assert 'decoder.UseNumber()' in d and 'return 30 * time.Second' in d and 'const ordinaryGas = uint64(1_000_000_000)' in d
(O/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',O/'main.go']),('go-build',['go','build','-trimpath','-o',O/'driver',O/'main.go']),('go-vet',['go','vet',O/'main.go'])]:run(label,args,900)
shutil.copy2(O/'main.go',O/'product-driver.go.txt')
pins={**prior,'profile':profile,'domain':profile,'basis':'accepted P38 parent-string-replaceall artifacts','engine':roles['engine'],'coordinator':roles['coordinator'],'bootstrapRoot':rb['root'],'expectedBootstrapRoot':rb['root'],'orderedBootstrapLeaves':rb['leaves'],'bootstrapCount':105,'baseBootstrapCount':104,'diagnosticClassBound':255,'newBootstrapImages':['java/util/HashMap$Node'],'changedBootstrapImages':['java/util/HashMap'],'guestCapability':'bounded guest HashMap.put with real nodes/resize; tree bins and other unsupported APIs refuse','sourceInvariants':{'allOther103PriorLeavesUnchanged':True,'changedPriorSlots':[100],'appendedNodeSlot':104,'engineABIAndStorageUnchanged':True,'coordinatorABIAndStorageUnchanged':True,'noNewOperationalNativeBinding':True,'heapRawRuntimeAndCheckpointCapsUnchanged':True,'underlyingEVMUnchanged':True}}
(O/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');proof={'changedEngineFunctions':changed,'newEngineFunctions':added,'allOther103PriorLeavesUnchanged':True,'changedLeafIndices':[100],'appendedNodeSlot':104,'bootstrapCount':105,'root':rb['root'],'leaves':rb['leaves'],'engineABIAndStorageUnchanged':True,'coordinatorABIAndStorageUnchanged':True,'storageComparison':'full slots/offsets/labels and recursive type shape; source-only AST IDs not protocol','noNewOperationalNativeBinding':True,'underlyingEVMUnchanged':True,'localPreinstalledNotStandardCREATE':True}
(O/'root-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'profile':profile,**roles,'bootstrapCount':105,'bootstrapRoot':rb['root'],'changedFunctions':changed,'newFunctions':added},indent=2))
