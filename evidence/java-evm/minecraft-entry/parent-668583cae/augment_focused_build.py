#!/usr/bin/env python3
"""Add an independently compiled same-P18 accepted-P17 baseline to the P18 candidate build."""
from pathlib import Path
import json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];build=Path(sys.argv[1]).resolve();assert build.parent==root/'build' and build.name.startswith('java-diff-mc-packed-float-grouped-scan-build-parent-')
accepted=here.parent/'parent-e23eea569';pins=json.loads((accepted/'artifacts/parent-build-pins.json').read_text());candidate=json.loads((build/'pins.json').read_text());env=dict(os.environ,NODE_PATH=str(root/'jvmevm/runtime/node_modules'),TMPDIR=str(build/'tmp'),PYTHONDONTWRITEBYTECODE='1')
def run(n,args):
 with (build/(n+'.log')).open('w') as f:subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def patch_domain(text):
 assert text.count('MC-RANDOM-CLASS-P18') in (4,6,9);text=text.replace('MC-RANDOM-CLASS-P18','MC-RANDOM-CLASS-P19')
 return text.replace('0x4d432d52414e444f4d2d434c4153532d50310038','0x4d432d52414e444f4d2d434c4153532d50310040').replace('0x4d432d52414e444f4d2d434c4153532d50310039','0x4d432d52414e444f4d2d434c4153532d50310041').replace('4d432d52414e444f4d2d434c4153532d50310038','4d432d52414e444f4d2d434c4153532d50310040').replace('4d432d52414e444f4d2d434c4153532d50310039','4d432d52414e444f4d2d434c4153532d50310041')
# Preserve compatibility candidate paths and names expected by the focused gate.
assert not (build/'candidate').exists();(build/'candidate').mkdir();shutil.copytree(build/'engine',build/'candidate/engine');shutil.copytree(build/'coordinator',build/'candidate/coordinator');shutil.copy2(build/'driver',build/'candidate-driver');shutil.copy2(build/'main.go',build/'candidate-driver.go')
# Compile the accepted P17 semantics in the same P18 domain.
p17e=build/'p17/engine';p17e.mkdir(parents=True);src=patch_domain((accepted/'artifacts/engine/MCEntryInterpreter.sol').read_text());(p17e/'MCEntryInterpreter.sol').write_text(src);shutil.copy2(accepted/'artifacts/engine/build.js',p17e/'build.js');run('p18-baseline-engine-build',['node',p17e/'build.js']);ea=json.loads((p17e/'MCEntryInterpreter.json').read_text());er={'bytes':len(ea['deployedBytecode'])//2,**ea['codeHashes']};assert er['bytes']==392268
p17c=build/'p17/coordinator';p17c.mkdir(parents=True);src=patch_domain((accepted/'artifacts/coordinator/MCEntryCoordinator.sol').read_text());src,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{ea["codeHashes"]["runtimeKeccak256"]}";',src);assert n==1;(p17c/'MCEntryCoordinator.sol').write_text(src);shutil.copy2(accepted/'artifacts/coordinator/build.js',p17c/'build.js');run('p18-baseline-coordinator-build',['node',p17c/'build.js']);ca=json.loads((p17c/'MCEntryCoordinator.json').read_text());cr={'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']}
# Compile an authenticated driver pinned to baseline P18 artifacts.
d=patch_domain((accepted/'canonical-driver.go.txt').read_text())
for name,value in [('immutableEngineSHA256',er['runtimeSHA256']),('immutableEngineKeccak','0x'+er['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+cr['runtimeKeccak256'])]:d,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',d);assert n==1
for name,value in [('engineRun',er['bytes']),('coordRun',cr['bytes']),('run',er['bytes'])]:d,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),d);assert n==1
(build/'p17-driver.go').write_text(d);run('p18-baseline-driver-gofmt',['gofmt','-w',build/'p17-driver.go']);run('p18-baseline-driver-build',['go','build','-trimpath','-o',build/'p17-driver',build/'p17-driver.go']);run('p18-baseline-driver-vet',['go','vet',build/'p17-driver.go'])
candidate['baselineEngine']=er;candidate['baselineCoordinator']=cr;candidate['profile']='MC-RANDOM-CLASS-P19-PACKED-FLOAT-GROUPED-SCAN';candidate['bootstrapRoot']='f4cf01e4356d76476b5ccd0949152c0422010df332d20bb1c84855793921dc81';candidate['expectedBootstrapRoot']=candidate['bootstrapRoot'];candidate['address']='0x4d432d52414e444f4d2d434c4153532d50310040';candidate['owner']='0x4d432d52414e444f4d2d434c4153532d50310041';candidate['runtimeCap']=393216
(build/'pins.json').write_text(json.dumps(candidate,indent=2)+'\n');print(json.dumps({'baselineEngine':er,'baselineCoordinator':cr,'candidateEngine':candidate['engine'],'bootstrapRoot':candidate['bootstrapRoot']},indent=2))
