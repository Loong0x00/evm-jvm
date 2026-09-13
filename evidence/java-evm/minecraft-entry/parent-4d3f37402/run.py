#!/usr/bin/env python3
"""Parent exact metadata rebuild, generated controls, original q1 ON/OFF diagnostic.
No limits or runtime bytecode changes. No failed state is used as execution input.
"""
from pathlib import Path
import gzip,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'properties-cost-preflight';basis=here.parent/'parent-c24d374bc'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-properties-cost-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();(out/'metadata').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as log:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=log,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
s=(src/'metadata/build_debug_metadata.js').read_text();a="path.resolve(here, '../../parent-c24d374bc/engine')";assert s.count(a)==1;s=s.replace(a,json.dumps(str(basis/'engine')));(out/'metadata/build_debug_metadata.js').write_text(s)
call('source-only-metadata',['node',out/'metadata/build_debug_metadata.js'])
actual=json.loads(gzip.open(out/'metadata/MCEntryInterpreter.debug.json.gz','rt').read());expected=json.loads(gzip.open(src/'metadata/MCEntryInterpreter.debug.json.gz','rt').read());assert actual==expected
# Fresh generated ON/OFF controls, with output path isolated from worker captures.
s=(src/'run_generated_controls.py').read_text();s=s.replace('ROOT=Path(__file__).resolve().parents[4]','ROOT=Path('+repr(str(root))+')').replace('HERE=Path(__file__).resolve().parent','HERE=Path('+repr(str(src))+')')
a="OUT=ROOT/'build'/f'java-diff-mc-properties-cost-{STAMP}'";assert s.count(a)==1;controls=root/'build/java-diff-mc-properties-cost-parent-controls-4d3f37402';s=s.replace(a,'OUT=Path('+repr(str(controls))+')')
a="(HERE/'runs/generated-controls-summary.json')";assert s.count(a)==1;s=s.replace(a,"(OUT/'summary.json')");(out/'run_generated_controls.py').write_text(s)
call('generated-on-off',[sys.executable,out/'run_generated_controls.py'])
# Map with independently rebuilt metadata and fixed unchanged source paths.
s=(src/'metadata/map_observation.py').read_text().replace('ROOT=HERE.parents[4]','ROOT=Path('+repr(str(root))+')');(out/'metadata/map_observation.py').write_text(s)
original=root/'build/java-diff-mc-properties-parent-official20-c24d374bc';world=original/'official';reports=original/'reports/official';driver=controls/'properties-cost-observer'
assert world.is_dir() and reports.is_dir();oldhead=(world/'durable-head.json').read_bytes();h=json.loads(oldhead);assert h['epoch']==249 and h['jvmSteps']==1683 and h['checkpointSHA256']=='affcf10ae1a90714a60255dc1b13475e62026d412dd38b1993e802b36528d2fe'
cp=world/'checkpoints'/(h['checkpointSHA256']+'.bin');oldcp=cp.read_bytes();(out/'prior-head.json').write_bytes(oldhead);(out/'prior.checkpoint').write_bytes(oldcp)
shutil.copy2(reports/'resume-refusal.json',out/'prior-q1-refusal.json')
args=[world,basis/'coordinator/MCEntryCoordinator.json',basis/'engine/MCEntryInterpreter.json','unused',1]
observed=[]
for enabled in (False,True):
 e=dict(env);e['MC_PROPERTIES_COST_OBSERVER']='1' if enabled else '0'
 label='original-on' if enabled else 'original-off';call(label,[driver,'resume-one-q1',*args],e)
 assert (world/'durable-head.json').read_bytes()==oldhead and cp.read_bytes()==oldcp
 r=json.loads((reports/'resume-refusal.json').read_text());assert r['selector']=='0xf15d7343' and r['uint256Words']==['7'] and r['rootBefore']==r['rootAfter']==h['trieRoot'];shutil.copy2(reports/'resume-refusal.json',out/(label+'-refusal.json'))
 observed.append({k:r.get(k) for k in ('gas','selector','revertHex','rootBefore','rootAfter')})
assert observed[0]==observed[1] and observed[0]['gas']==73494750
obs=reports/'observer-resumeMain-epoch-249.json';assert obs.is_file();shutil.copy2(obs,out/'original-observation.json')
call('map-original',[sys.executable,out/'metadata/map_observation.py',out/'original-observation.json',out/'original-source-map.json'])
(out/'verified.json').write_text(json.dumps({'exactMetadataRebuild':True,'sameOriginalHeadAndCheckpoint':True,'originalOnOff':observed,'gasLimitUnchanged':100000000,'reserveUnchanged':25000000,'runtimeUnchanged':actual['runtimeKeccak256']},indent=2)+'\n')
print('PASS exact metadata/generated controls/original q1 read-only ON/OFF')
print((out/'verified.json').read_text())
