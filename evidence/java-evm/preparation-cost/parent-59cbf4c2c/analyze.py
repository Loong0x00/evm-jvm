#!/usr/bin/env python3
"""Independent byte/PC/frame/memory reconciliation; no EVM input interpretation."""
from pathlib import Path
import collections,hashlib,json,sys
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();rows=json.loads((out/'raw-summary.json').read_text())
vfs='0x4a564d45564d564653304152554e5449ca000001'
parents={
 'padded262144':'matrix/aggregate262144/java-1.json','bigMethodRich':'matrix/big/java-1.json','density181969':'density/ordinary.json',
 'density181969-boundary':'density/boundary-1B.json','density-q1-first':'density/q1-1.json','density-q1-refusal':'density/q1-2.json','density-q1-boundary-resume':'density/q1-boundary-resume-1B.json'}
base=root/'evidence/java-evm/capacity-baseline/parent-97a926123/final'
def disassemble(b):
 r={};p=0
 while p<len(b):r[p]=b[p];p+=1+(b[p]-0x5f if 0x60<=b[p]<=0x7f else 0)
 return r

def debug(name,want):
 j=json.loads((out/'debug'/(name+'-solc.json')).read_text());d=j['contract']['evm']['deployedBytecode'];b=bytes.fromhex(d['object'])
 assert hashlib.sha256(b).hexdigest()==want
 assert j['compiler']=='0.8.30+commit.73712a01.Emscripten.clang'
 for k,v in {'optimizer':{'enabled':True,'runs':200},'viaIR':True,'evmVersion':'cancun','metadata':{'appendCBOR':False,'bytecodeHash':'none'}}.items():assert j['settings'][k]==v
 ops=disassemble(b);last=['-1','-1','-1','',''];maps=[]
 for text in d['sourceMap'].split(';'):
  f=text.split(':');assert len(f)<=5
  for n,s in enumerate(f):
   if s:last[n]=s
  maps.append(tuple(map(int,last[:3])))
 assert len(maps)<=len(ops)
 sourceid=int(j['ast']['src'].split(':')[2]);funcs=[];structs={}
 def walk(x):
  if isinstance(x,dict):
   if x.get('nodeType')=='FunctionDefinition':
    a,n,i=map(int,x['src'].split(':'));assert i==sourceid;funcs.append((a,n,x.get('name') or '<constructor>'))
   if x.get('nodeType')=='StructDefinition':structs[x['name']]=x['members']
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(j['ast']);m=dict(zip(ops,maps))
 def at(pc):
  z=m.get(pc)
  if not z or z[0]<0 or z[2]<0:return '<unmapped>'
  if z[2]!=sourceid:return '<other-source-id>'
  candidates=[f for f in funcs if f[0]<=z[0] and z[0]+z[1]<=f[0]+f[1]]
  return min(candidates,key=lambda f:f[1])[2] if candidates else '<ambiguous>'
 return j,d,ops,at,structs
vj,vd,vops,vat,structs=debug('vfs','4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f')
cj,cd,cops,cat,_=debug('coordinator','1fc9cc6be252cc9256e280fb2a5669fbdd6a92a03955639d83ddc5173f365363')
fd=vd['functionDebugData'];alloc='allocate_and_zero_memory_struct_struct_Selected';arr='allocate_and_zero_memory_array_array_struct_Selected_dyn'
start,stop=fd[alloc]['entryPoint'],fd[arr]['entryPoint'];assert (start,stop)==(146431,146622) and vops[start]==0x5b and vops[max(p for p in vops if p<stop)]==0x56
assert len(structs['Selected'])==23
ir=vj['contract']['irOptimized'];at=ir.index('function '+alloc+'(');snippet=ir[at:ir.index('\n            function ',at+1)];assert '736' in snippet and 'mstore' in snippet
(out/'selected-allocator.ir.txt').write_text(snippet+'\n')
reports={}
for name,row in rows.items():
 c=row['ordinary'];reference=json.loads((base/parents[name]).read_text())
 for k in ('gas','error','beforeRoot','afterRoot','rawRevert','receiptRoot','logs','checkpointBytes','checkpointSHA256','head','slice','budget','quantum'):
  assert c.get(k)==reference.get(k),(name,k)
 assert c['budget']==(1000000000 if 'boundary' in name else 100000000)
 assert 0<c['gas']<=c['budget'] and c['wallSeconds']<=(120 if c['budget']==1000000000 else 30)
 tr=c['trace'];pcs=list(tr['pcs'].values());frames=tr['frames'];coord=c['head']['Coordinator']['Address'].lower();groups=collections.Counter();byaddr=collections.Counter();forwarded=0
 for p in pcs:
  a=p['address'].lower();assert p['count']>0 and 0<=p['forwarded']<=p['cost'];exclusive=p['cost']-p['forwarded'];byaddr[a]+=exclusive;forwarded+=p['forwarded']
  if p['forwarded']:assert p['opcode'] in (0xf0,0xf1,0xf2,0xf4,0xf5,0xfa)
  if a==vfs:assert vops[p['pc']]==p['opcode'];groups[vat(p['pc'])]+=exclusive
  elif a==coord:assert cops[p['pc']]==p['opcode']
 assert frames[0]['depth']==0 and frames[0]['used']==c['gas'] and frames[0]['to'].lower()==coord
 assert sum(byaddr.values())==c['gas']
 frameexclusive=collections.Counter();stack=[];childentergas=0
 for f in frames:
  depth=f['depth'];assert depth<=len(stack) and f['value']=='0'
  stack=stack[:depth]
  if depth:frameexclusive[stack[-1]['to'].lower()]-=f['used'];childentergas+=f['enterGas']
  frameexclusive[f['to'].lower()]+=f['used'];stack.append(f)
 assert dict(byaddr)==dict(frameexclusive),(name,'per-address reconciliation')
 assert forwarded==childentergas
 vp=[p for p in pcs if p['address'].lower()==vfs];assert not any(p['forwarded'] for p in vp)
 peak=max(p['memoryBeforeMax'] for p in vp);words=(peak+31)//32;growth=sum(p['memoryGrowthGas'] for p in vp)
 assert growth==3*words+words*words//512,(name,'complete VFS memory expansion reconciliation')
 assert not any(p['freePointerRewinds'] for p in vp)
 entries={p['pc']:p['count'] for p in vp};allocated=sum(p['freePointerIncrease'] for p in vp if start<=p['pc']<stop)
 alloccount=entries.get(start,0);assert allocated==736*alloccount
 hist=tr['allocationSizes'];assert hist.get(next((k for k in hist if k.lower()==vfs+'/736'),''),0)==alloccount
 region=[p for p in vp if start<=p['pc']<stop]
 reports[name]={'gas':c['gas'],'budget':c['budget'],'error':c.get('error'),'exclusivePCSum':sum(byaddr.values()),'forwardedCallGasExcluded':forwarded,'addresses':dict(byaddr),'VFSmaxMemoryBytes':peak,'VFSexpansionGas':growth,'VFSexpansionShare':growth/c['gas'],'SelectedAllocatorEntryCount':alloccount,'SelectedArrayAllocatorEntryCount':entries.get(fd[arr]['entryPoint'],0),'SelectedRegionPCGas':sum(p['cost'] for p in region),'SelectedRegionExpansionGas':sum(p['memoryGrowthGas'] for p in region),'SelectedAllocatedBytes':allocated,'VFSNamedSourceGroups':dict(groups.most_common()),'debugEntryHits':{fn:entries.get(info['entryPoint'],0) for fn,info in fd.items() if info.get('entryPoint') is not None and ('restoreSelection' in fn or 'validateRestoredReferences' in fn)},'tracedWallSeconds':c['wallSeconds']}
print(json.dumps({'scope':'exact bytecode read-only attribution, not optimization or profile acceptance','compilerRuntimePinsMatched':True,'sourceMapFileIDChecked':True,'SelectedStructFields':23,'SelectedAllocationBytes':736,'emittedAllocatorRegion':[start,stop],'cases':reports,'interpretation':'named-source zero bucket is NOT proof a semantic phase did not execute; allocation region and free-memory-pointer measurements are separate compiler-level observations'},indent=2))
