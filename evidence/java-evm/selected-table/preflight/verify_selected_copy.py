#!/usr/bin/env python3
"""Actual byte-fragment, full refusal, root, quantum and checkpoint checks."""
from pathlib import Path
import base64,hashlib,json,sys
fixtures=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();meta=json.loads((fixtures/'metadata.json').read_text());cases={c['name']:c for c in meta['fixtures']};worlds=json.loads((out/'worlds.json').read_text());pids=set();finals={};rowsummary={};allgas=[];allreads=0;cpchecks=0
for profile,n,args in [('baseline',4,2016),('optimized',8,3680)]:
 j=json.loads((out/(profile+'-maxargs.json')).read_text());assert j['names']==n and j['nameBytes']==256 and j['argumentBytes']==args and j['initBytes']==7626 and j['completeInitBytes']==7626+args<49152

def idcheck(j):
 assert j['pid'] not in pids;pids.add(j['pid'])
def mutations(j,profile):
 for m in j['mutations']:assert 0<m['gas']<=100000000;allgas.append(m['gas']);assert m['root']!='0x'+'0'*64
 t=j['setupTrace'];assert t['enabled']==(profile=='optimized')
 if t['enabled']:assert t['rootCalls']>=len(j['mutations'])-1 and 0<t['maxEvmSeconds']<=30

def trace(j,c,profile):
 global allreads
 t=j['trace'];assert t['enabled']==(profile=='optimized')
 assert 0<j['gas']<=j['budget']==100000000;allgas.append(j['gas']);assert 0<j['wallSeconds']<=30
 if not t['enabled']:return
 assert t['rootCalls']==1 and 0<t['evmSeconds']<=j['wallSeconds'] and 0<t['maxEvmSeconds']<=30
 expected=[]
 for i,cl in enumerate(c['classes']):
  for off in range(0,cl['bytes'],4096):expected.append((i,off,min(4096,cl['bytes']-off)))
 reads=t['reads'];assert [(r['slot'],r['offset'],r['requested']) for r in reads]==expected
 assert all(r['returned']==r['requested'] and 0<r['requested']<=4096 and r['success'] and r['gas']>0 for r in reads)
 assert sum(r['returned'] for r in reads)==c['selectedRawBytes'];allreads+=len(reads)

for w in worlds:
 label=w['label'];d=out/label;c=cases[w['fixture']];profile=w['profile'];s=json.loads((d/'setup.json').read_text());idcheck(s);mutations(s,profile)
 refused=w['expectedSetupRefusal']
 if refused:
  assert s['command']=='setup-refusal' and s['beforeRoot']==s['afterRoot']
  if refused.startswith('decoderCount'):
   count=int(refused.removeprefix('decoderCount'));assert s['stage']=='createDecoder' and s['registeredDecoders']==count and s['gas']==0 and s['rawRevert']=='0x'
  else:
   code=int(refused.removeprefix('coordinator'));raw=bytes.fromhex(s['rawRevert'][2:]);assert len(raw)==36 and raw[:4].hex()=='27cad659' and int.from_bytes(raw[4:],'big')==code and s['stage']=='createCoordinator' and 0<s['gas']<=100000000
  continue
 rows=[s] if w['warm'] else [json.loads(p.read_text()) for p in sorted(d.glob('java-*.json'),key=lambda p:int(p.stem.split('-')[1]))]
 before=rows[0]['beforeRoot'] if w['warm'] else s['head']['StateRoot'];previousJ=previousI=0
 for n,r in enumerate(rows,1):
  if not w['warm']:idcheck(r);init=r['initialization'];assert not init['EngineInstalled'] and not init['AS0Creation']['Performed'] and init['AS0Creation']['GasUsed']==0
  assert 'error' not in r and r['beforeRoot']==before and r['afterRoot']!=before and r['receiptRoot']==r['afterRoot']==r['head']['StateRoot'];before=r['afterRoot']
  sl=r['slice'];h=r['head'];assert sl['Epoch']==n and sl['Schema']==1 and r['beforeEpoch']==n-1 and r['logs']==1 and r['rawRevert']=='0x'
  assert 0<sl['TotalJvmSteps']-previousJ<=w['quantum'] and 0<=sl['TotalInternalSteps']-previousI<=4096
  previousJ,previousI=sl['TotalJvmSteps'],sl['TotalInternalSteps'];assert sl['Lifecycle']==(1 if n<len(rows) else 2)
  assert sl['CheckpointRoot']==h['Java']['CheckpointRoot'] and sl['MachineStateRoot']==h['Java']['MachineStateRoot'] and sl['VFSStateRoot']==h['Java']['VFSStateRoot']
  assert h['Coordinator']['ClassCount']==len(c['knownNames']) and h['Coordinator']['TotalClassBytes']==c['selectedRawBytes']
  assert [base64.b64decode(x['RawName']).decode() for x in h['Coordinator']['Classes']]==[x+'.class' for x in c['knownNames']]
  assert 0<r['checkpointBytes']<=1048576
  if not w['memory']:
   cp=(d/'world/checkpoints'/(sl['CheckpointRoot'][2:]+'.checkpoint')).read_bytes();assert len(cp)==r['checkpointBytes'] and hashlib.sha256(cp).hexdigest()==r['checkpointSHA256'];cpchecks+=1
  trace(r,c,profile)
 last=rows[-1];want=next(x['result'] for x in c['oracle'] if x['argument']==w['mode']);assert last['slice']['Result']==want and last['slice']['JavaKind']==0
 assert len(rows)==(previousJ+w['quantum']-1)//w['quantum']
 if not w['memory']:
  t=json.loads((d/'terminal.json').read_text());idcheck(t);assert t['head']==last['head'] and t['checkpointSHA256']==last['checkpointSHA256'] and t['checkpointBytes']==last['checkpointBytes'];assert not t['initialization']['EngineInstalled'] and not t['initialization']['AS0Creation']['Performed'] and t['initialization']['AS0Creation']['GasUsed']==0
 if w['publicationFault']:
  b=json.loads((d/'publication-failure.json').read_text());idcheck(b);assert b['publicationFaultRequested'] and 'after real trie/code sync' in b['error'] and b['rawRevert']=='0x' and b['logs']==0 and b['checkpointBytes']==0 and b['receiptRoot']=='0x'+'0'*64 and b['slice']['Schema']==0
  assert b['head']==rows[0]['head'] and b['beforeRoot']==b['afterRoot']==rows[0]['afterRoot'];trace(b,c,profile)
 finals[label]=last;rowsummary[label]={'result':want,'jvm':previousJ,'internal':previousI,'slices':len(rows),'maxJavaGas':max(x['gas'] for x in rows),'readsPerCall':len(last['trace']['reads'] or []),'rawClassBytes':c['selectedRawBytes']}
# Identical binding/root comparisons only within same isolated profile; old/new4 semantic comparison.
for a,b in [('new4','warm4'),('new4','memory4'),('chain8','chain8-q7'),('exact8','exact8-q7'),('big','big-q7'),('big-q7','big-publication')]:
 x,y=finals[a],finals[b]
 for field in ('MachineStateRoot','VFSStateRoot','TotalJvmSteps','TotalInternalSteps','Result'):assert x['slice'][field]==y['slice'][field],(a,b,field)
 for field in ('PackageRoot','InstanceID'):assert x['head']['Coordinator'][field]==y['head']['Coordinator'][field]
 assert x['head']['AS0']['ContentCommitment']==y['head']['AS0']['ContentCommitment'] and x['head']['Index']['FinalRoot']==y['head']['Index']['FinalRoot']
 assert [z['FinalRoot'] for z in x['head']['Decoders']]==[z['FinalRoot'] for z in y['head']['Decoders']]
for field in ('Result','TotalJvmSteps','TotalInternalSteps'):assert finals['old4']['slice'][field]==finals['new4']['slice'][field]
assert finals['old4']['slice']['Result']==finals['new4']['slice']['Result']
assert finals['chain8']['slice']['Result']!=finals['chain8-input19']['slice']['Result']
assert (finals['big']['slice']['Result'],finals['big']['slice']['TotalJvmSteps'],finals['big']['slice']['TotalInternalSteps'])==(15,11,2)
print(json.dumps({'worlds':len(worlds),'distinctProcessReceipts':len(pids),'actualCheckpointFilesChecked':cpchecks,'actualDI0ReadFragments':allreads,'maxRecordedOrdinaryGas':max(allgas),'rows':rowsummary,'scope':'DISPOSABLE isolated selected-table COPY, not accepted profile or Minecraft execution'},indent=2))
