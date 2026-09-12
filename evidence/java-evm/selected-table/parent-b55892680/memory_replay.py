#!/usr/bin/env python3
"""Actual selected allocator entry/free-pointer/memory observations on fresh EVM worlds."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];proto=Path(sys.argv[1]).resolve();fixtures=Path(sys.argv[2]).resolve();density=Path(sys.argv[3]).resolve();out=Path(sys.argv[4]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
inputs={'padded':(fixtures/'zips/aggregate262144.zip','BoundaryEntry,BoundaryPad',17),'big':(fixtures/'zips/big-method-rich.zip','BigCaller,BigEntry',15),'density':(density/'density.zip','BigPair,BigEntry,BigTwin',23)}
reports={}
for label,(zipfile,names,want) in inputs.items():
 world=out/label;exe=proto/'optimized/memory-driver'
 for cmd,args in [('setup',['-zip',zipfile,'-names',names]),('slice',['-length',zipfile.stat().st_size,'-mode',7])]:
  p=out/(label+'-'+cmd+'.json')
  with p.open('w') as f,p.with_suffix('.stderr').open('w') as e:subprocess.run([str(exe),'-command',cmd,'-dir',str(world)]+list(map(str,args)),env=env,stdout=f,stderr=e,check=True,timeout=120 if cmd=='setup' else 32)
 j=json.loads(p.read_text());assert 'error' not in j and j['slice']['Lifecycle']==2 and j['slice']['Result']==want and j['gas']<=100000000
 t=j['trace'];m=t['memory'];w=(m['MemoryBeforeMax']+31)//32;assert m['MemoryGrowthGas']==3*w+w*w//512 and m['FreePointerRewinds']==0
 a=sum(n for k,n in t['allocationSizes'].items() if k.endswith('/736'));assert a==t['selectedAllocations']
 assert t['putSelections']>0 and t['selectedAllocations']>=t['putSelections']
 cp=(world/'checkpoints'/(j['slice']['CheckpointRoot'][2:]+'.checkpoint')).read_bytes();assert hashlib.sha256(cp).hexdigest()==j['checkpointSHA256']
 reports[label]={'gas':j['gas'],'result':want,'SelectedAllocations':a,'loadedSlotWrites':t['putSelections'],'peakEVMMemory':m['MemoryBeforeMax'],'EVMExpansionGas':m['MemoryGrowthGas'],'payloadSHA256':hashlib.sha256(cp[280:]).hexdigest(),'readFragments':len(t['reads'])}
# Compare final opaque machine payload to the old successful reference without
# pretending different code-bound config/package/envelope roots are equal.
refbase=root/'evidence/java-evm/capacity-baseline/parent-97a926123/final'
for label,record in [('big',refbase/'matrix/big/terminal.json'),('padded',refbase/'matrix/aggregate262144/terminal.json')]:
 j=json.loads(record.read_text());cp=record.with_name('terminal.checkpoint').read_bytes();assert hashlib.sha256(cp[280:]).hexdigest()==reports[label]['payloadSHA256']
j=json.loads((refbase/'density/boundary-1B.json').read_text());cp=(refbase/'density/world/checkpoints'/(j['slice']['CheckpointRoot'][2:]+'.checkpoint')).read_bytes();assert hashlib.sha256(cp[280:]).hexdigest()==reports['density']['payloadSHA256']
old={'big':(48451006,2557,3137568,19070722),'padded':(7879725,6,863648,1503635),'density':(124505990,5111,5957824,68261157)}
for k,v in reports.items():v['oldReferenceGas'],v['oldSelectedAllocations'],v['oldPeakEVMMemory'],v['oldExpansionGas']=old[k]
(out/'report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
