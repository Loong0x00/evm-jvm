#!/usr/bin/env python3
"""Independent P27 build of the exact raw74/518516/q65536 local profile."""
from pathlib import Path
import ast,hashlib,json,os,re,shutil,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];BASE=H.parent/'parent-raw73-byte516040';STAGE=H.parent/'raw74-byte518516'
out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-raw74-byte518516-build-parent-') and not out.exists()
base=(BASE/'artifacts/engine/MCEntryInterpreter.sol').read_text();source=(STAGE/'engine/MCEntryInterpreter.sol').read_text();expected=base
for a,b in [('uint256 private constant MAX_RAW_CLASSES = 73;','uint256 private constant MAX_RAW_CLASSES = 74;'),('uint256 private constant MAX_RAW_BYTES = 516040;','uint256 private constant MAX_RAW_BYTES = 518516;'),('uint32(73), uint32(516040), uint32(64), uint32(32), uint32(65536),','uint32(74), uint32(518516), uint32(64), uint32(32), uint32(65536),')]:
 assert expected.count(a)==1;expected=expected.replace(a,b,1)
assert source==expected,'engine delta outside explicit profile edits'
cb=(BASE/'artifacts/coordinator/MCEntryCoordinator.sol').read_text();cs=(STAGE/'coordinator/MCEntryCoordinator.sol').read_text();strip_hash=lambda s:re.sub(r'(bytes32 private constant ENGINE_CODEHASH = hex")[0-9a-f]{64}(";)',r'\g<1>HASH\g<2>',s)
expected=strip_hash(cb)
for a,b in [('[73] private','[74] private'),('n == 0 || n > 73 ||','n == 0 || n > 74 ||'),('if (size == 0 || size > 516040) revert MR0Error(11);','if (size == 0 || size > 518516) revert MR0Error(11);'),('uint256(total) + size > 516040','uint256(total) + size > 518516')]:
 assert expected.count(a)==(4 if a=='[73] private' else 1);expected=expected.replace(a,b)
assert strip_hash(cs)==expected,'coordinator delta outside explicit resource envelope edits'
for n in ('engine','coordinator'):assert (STAGE/n/'build.js').read_bytes()==(BASE/'artifacts'/n/'build.js').read_bytes()
prior=json.load(open(BASE/'artifacts/parent-build-pins.json'));worker=json.load(open(STAGE/'results/generated-gate-p26-v1/build-pins.json'))
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'),GOPROXY='off',GOSUMDB='off',PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
# Load only the hash helper with its environment explicitly fixed to this repository.
ns={'ROOT':ROOT,'env':env};exec((H/'root_helper.py').read_text(),ns);hashroot=ns['root_from_source']
old='MC-RANDOM-CLASS-P26';new='MC-RANDOM-CLASS-P27';addr='0x4d432d52414e444f4d2d434c4153532d50310058';owner='0x4d432d52414e444f4d2d434c4153532d50310059'
assert hashroot(base,'JVMEVM:'+old+':BOOTSTRAP:1')==hashroot(source,'JVMEVM:'+old+':BOOTSTRAP:1')==prior['bootstrapRoot']==worker['bootstrapRoot']
assert source.count(old)==9;source=source.replace(old,new);root=hashroot(source,'JVMEVM:'+new+':BOOTSTRAP:1');assert root!=prior['bootstrapRoot']
e=out/'engine';e.mkdir();(e/'MCEntryInterpreter.sol').write_text(source);shutil.copy2(STAGE/'engine/build.js',e/'build.js');run('engine-build',['node',e/'build.js']);ea=json.load(open(e/'MCEntryInterpreter.json'));er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']<=393216;assert ea['abi']==json.load(open(BASE/'artifacts/engine/MCEntryInterpreter.json'))['abi'];assert ea['storageLayout']==json.load(open(BASE/'artifacts/engine/MCEntryInterpreter.json'))['storageLayout']
c=out/'coordinator';c.mkdir();assert cs.count(old)==4;cs=cs.replace(old,new);cs,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',cs);assert n==1;cs,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{er["runtimeKeccak256"]}";',cs);assert n==1;(c/'MCEntryCoordinator.sol').write_text(cs);shutil.copy2(STAGE/'coordinator/build.js',c/'build.js');run('coordinator-build',['node',c/'build.js']);ca=json.load(open(c/'MCEntryCoordinator.json'));cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}
def pins_for_driver(d):
 assert d.count(old)==6;d=d.replace(old,new).replace(prior['address'],addr).replace(prior['owner'],owner)
 for name,val in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:
  d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+val+r'\g<2>',d);assert n==1
 for name,size in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:
  d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(size),d);assert n==1
 return d
# Generated-only extended CLI contains raw fixture probes; original replay uses a minimal template.
if (STAGE/'driver.go').exists():
 d=pins_for_driver((STAGE/'driver.go').read_text())
else:
 # This stage generates its test observer from an immutable accepted-parent template.
 tree=ast.parse((STAGE/'tools/build.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='driver_source')
 template=(BASE/'generated-probe-driver.go.txt').read_text()
 expected_template=next(x.value.value for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TEMPLATE_SHA256' for t in x.targets))
 assert hashlib.sha256(template.encode()).hexdigest()==expected_template
 def replace_once(text,old,new):
  assert text.count(old)==1;return text.replace(old,new,1)
 scope={'template':template,'engine_run':bytes.fromhex(ea['deployedBytecode']),'coord_run':bytes.fromhex(ca['deployedBytecode']),'replace_once':replace_once}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(STAGE/'tools/build.py'),'exec'),scope)
 d=pins_for_driver(scope['driver_source'](ea,ca))
(out/'main.go').write_text(d)
for label,args in [('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])]:run(label,args)
product=(BASE/'canonical-driver.go.txt').read_text()
for a,b in [('len(m.Decoders) > 73','len(m.Decoders) > 74'),('len(parts) > 73','len(parts) > 74')]:assert product.count(a)==1;product=product.replace(a,b)
product=pins_for_driver(product);(out/'product-driver.go.txt').write_text(product)
pins={**prior,**worker,'domain':new,'profile':new+'-RAW74-BYTE518516','address':addr,'owner':owner,'bootstrapRoot':root,'expectedBootstrapRoot':root,'engine':er,'coordinator':cr,'rawLimits':[74,518516],'maxJvmSteps':65536,'maxInternalSteps':4096,'diagnosticClassBound':171,'maxCheckpointBytes':1048576,'runtimeCap':393216}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'root-audit.json').write_text(json.dumps({'acceptedP26Root':prior['bootstrapRoot'],'actualIndependentP27Root':root,'orderedLeaves':97,'onlyEngineChanges':['rawClasses73->74','rawBytes516040->518516','two raw config leaves'],'sourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'originalDriverTemplate':'accepted P24 canonical transport + raw name/count guards and domain/artifact pins only; no new host class probe path'},indent=2)+'\n');print(json.dumps({'engine':er,'coordinator':cr,'bootstrapRoot':root,'rawLimits':[74,518516],'maxJvmSteps':65536},indent=2))
