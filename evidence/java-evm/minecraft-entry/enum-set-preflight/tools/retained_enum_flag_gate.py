#!/usr/bin/env python3
"""Generated-only ACC_ENUM admission gate; no original JAR/class/world input."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
here=Path(__file__).resolve().parent; root=here.parents[4]
build=Path(sys.argv[1]).resolve(); fixtures=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
assert build.parent==root/'build' and fixtures.parent==root/'build' and out.parent==root/'build' and out.name.startswith('java-diff-mc-enum-bootstrap-') and not out.exists()
out.mkdir();(out/'logs').mkdir();(out/'tmp').mkdir(); rows={};commands=[];start=time.monotonic()
driver=build/'driver';coord=build/'coordinator/MCEntryCoordinator.json';engine=build/'engine/MCEntryInterpreter.json'
def names(label):return ','.join(json.loads((fixtures/(label+'.json')).read_text())['entries'])
def report(w):return w.parent/'reports'/w.name
def run(label,args,binding):
 env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',MC_ENTRY_BINDINGS=names(binding)); log=out/'logs'/(label+'.log');t=time.monotonic()
 with log.open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 row={'label':label,'exit':p.returncode,'elapsedSeconds':time.monotonic()-t,'command':list(map(str,args))};commands.append(row);(out/'logs'/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');assert p.returncode==0,(label,p.returncode,log)
def failed(label,selector,words):
 baseline=None
 for tag,q in (('q1',1),('q7',7),('direct',4096)):
  w=out/('world-%s-%s'%(label,tag));run('%s-%s-start'%(label,tag),[driver,'setup-chain',w,coord,engine,fixtures/(label+'.zip'),str(q)],label)
  f=json.loads((report(w)/'start-refusal.json').read_text());assert f['selector']==selector and list(map(str,f['uint256Words']))==words and f['rootUnchanged'],(label,tag,f)
  terminal={'selector':f['selector'],'words':f['uint256Words'],'revertHex':f['revertHex'],'rootUnchanged':f['rootUnchanged']}
  if baseline is None:baseline=terminal
  else:assert terminal==baseline,(label,tag,terminal,baseline)
 rows[label]=baseline
def success(label):
 baseline=None
 for tag,q in (('q1',1),('q7',7),('direct',4096)):
  w=out/('world-%s-%s'%(label,tag));run('%s-%s-start'%(label,tag),[driver,'setup-chain',w,coord,engine,fixtures/(label+'.zip'),str(q)],label);run('%s-%s-finish'%(label,tag),[driver,'finish',w,coord,engine,fixtures/(label+'.zip'),str(q)],label);run('%s-%s-reopen'%(label,tag),[driver,'verify',w,coord,engine,fixtures/(label+'.zip'),str(q)],label)
  h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2 and h['result']==0 and len(h['decoders'])==2 and h['totalClassBytes']<=262144
  cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();assert hashlib.sha256(cp).hexdigest()==h['checkpointSHA256']
  terminal={'machineRoot':h['machineRoot'],'opaquePayloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'checkpointSHA256':h['checkpointSHA256'],'epoch':h['epoch']}
  if baseline is None:baseline=terminal
  else:
   for k in ('machineRoot','opaquePayloadSHA256'):assert terminal[k]==baseline[k],(label,tag,k,terminal,baseline)
 rows[label]=baseline
# Ordinary and marker-only E bundles execute identically. This is the positive 0x4000
# proof and provides q1/q7/direct/reopen/canonical terminal equivalence.
success('ordinary');success('enum-marker')
# All rejected non-interface combinations remain LinkError(5, patched binding index 1).
for label in ('annotation','module','annotation-enum','module-enum'):failed(label,'0x427cfac5',['5','1'])
# Interface validation remains independent of the changed non-interface parser mask.
success('interface-ordinary')
for label in ('interface-enum','interface-annotation','java8-annotation'):failed(label,'0x069163bc',['1','1'])
# The genuine enum now resolves its Enum superclass. Its compiler-generated values()
# still honestly reaches the unimplemented array clone call; do not retain the old
# missing-superclass selector. q1/q7 resume from durable checkpoints, while direct
# exposes the same immutable call refusal in startMain.
def enum_after_bootstrap():
 baseline=None
 for tag,q in (('q1',1),('q7',7),('direct',4096)):
  w=out/('world-java8-enum-'+tag); run('java8-enum-'+tag+'-start',[driver,'setup-chain',w,coord,engine,fixtures/'java8-enum.zip',str(q)],'java8-enum')
  p=report(w)/'start-refusal.json'
  if p.exists(): f=json.loads(p.read_text())
  else:
   run('java8-enum-'+tag+'-finish',[driver,'finish',w,coord,engine,fixtures/'java8-enum.zip',str(q)],'java8-enum')
   f=json.loads((report(w)/'resume-refusal.json').read_text())
  assert f['selector']=='0xd631c3a4' and list(map(str,f['uint256Words']))==['1','3'] and f['rootUnchanged'],(tag,f)
  x={'selector':f['selector'],'words':f['uint256Words'],'revertHex':f['revertHex'],'rootUnchanged':f['rootUnchanged']}
  if baseline is None: baseline=x
  else: assert x==baseline,(tag,x,baseline)
 rows['java8-enum']=baseline
enum_after_bootstrap()
assert rows['java8-enum']['selector']!='0xa52e829f' and rows['java8-enum']['selector']!='0x427cfac5'
summary={'profile':'MC-ENUM-BOOTSTRAP-PREFLIGHT1','generatedOnly':True,'results':rows,'commands':commands,'wholeGateSeconds':time.monotonic()-start}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
