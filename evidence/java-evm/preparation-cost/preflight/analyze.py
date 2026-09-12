#!/usr/bin/env python3
"""Decode aggregate EVM PCs with solc source maps; no execution or source mutation."""
from pathlib import Path
import gzip,hashlib,json,sys
src=Path(sys.argv[1]).resolve();dst=Path(sys.argv[2]).resolve();assert src.name.startswith('java-diff-mc-capacity-cost-') and not dst.exists()
dst.mkdir(parents=True)
def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pcs(hexcode):
 b=bytes.fromhex(hexcode);r=[];i=0
 while i<len(b):
  r.append(i);op=b[i];i+=1+(op-0x5f if 0x60<=op<=0x7f else 0)
 return r
def smap(s):
 # Solidity fields inherit individually; jump/modifier fields are retained but not interpreted.
 last=[-1,-1,-1,'',''];out=[]
 for x in s.split(';'):
  v=x.split(':')
  for i,z in enumerate(v):
   if z!='': last[i]=int(z) if i<3 else z
  out.append(tuple(last))
 return out
def functions(ast):
 r=[]
 def walk(x):
  if isinstance(x,dict):
   if x.get('nodeType')=='FunctionDefinition':
    a=x.get('src','-1:-1:-1').split(':');r.append((int(a[0]),int(a[1]),x.get('name') or '<fallback/constructor>'))
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(ast);return r
def decoder(debug):
 x=load(debug);c=x['contract'];m={pc:span for pc,span in zip(pcs(c['evm']['deployedBytecode']['object']),smap(c['evm']['deployedBytecode']['sourceMap']))};fs=functions(x['ast'])
 def at(pc):
  z=m.get(pc)
  if not z or z[0]<0 or z[2]<0:return ('unmapped',None)
  cand=[q for q in fs if q[0]<=z[0] and z[0]+max(z[1],0)<=q[0]+q[1]]
  return ((min(cand,key=lambda q:q[1])[2] if cand else '<contract/ambiguous>'),{'start':z[0],'length':z[1],'source':z[2]})
 return at,{'compiler':x['compiler'],'settings':x['settings'],'sourceSHA256':x['sourceSHA256'],'runtimeBytes':len(c['evm']['deployedBytecode']['object'])//2,'runtimeSHA256':hashlib.sha256(bytes.fromhex(c['evm']['deployedBytecode']['object'])).hexdigest(),'instructionCount':len(m)}
vfs_at,vfs_receipt=decoder(src/'debug/vfs-solc.json');coord_at,coord_receipt=decoder(src/'debug/coordinator-solc.json')
raw=load(src/'raw-summary.json');out={'schema':1,'inputDirectory':src.name,'rawSummarySHA256':sha(src/'raw-summary.json'),'compiler':{'vfs':vfs_receipt,'coordinator':coord_receipt},'cases':{}}
vfs='0x4a564d45564d564653304152554e5449ca000001'
for name,row in raw.items():
 call=row['ordinary'];tr=call['trace'];coord=call['head']['Coordinator']['Address'].lower();groups={};allpc=[]
 for q in tr['pcs'].values():
  q=dict(q);q['exclusiveCost']=q['cost']-q.get('forwarded',0);a=q['address'].lower()
  if a==vfs: contract,fn,span='VFS0aInterpreter',*vfs_at(q['pc'])
  elif a==coord: contract,fn,span='CB0ClassCoordinator',*coord_at(q['pc'])
  else: contract,fn,span='dependency/other','<no requested source map>',None
  q.update(contract=contract,function=fn,sourceSpan=span)
  key=contract+'::'+fn;g=groups.setdefault(key,{'contract':contract,'function':fn,'exclusiveCost':0,'costWithForwarded':0,'forwarded':0,'count':0,'pcEntries':0})
  g['exclusiveCost']+=q['exclusiveCost'];g['costWithForwarded']+=q['cost'];g['forwarded']+=q.get('forwarded',0);g['count']+=q['count'];g['pcEntries']+=1;allpc.append(q)
 total=sum(q['exclusiveCost'] for q in allpc);root=call['gas'];frames=tr['frames'];top=sorted(allpc,key=lambda x:x['exclusiveCost'],reverse=True)[:40]
 out['cases'][name]={'gas':root,'error':call.get('error'),'beforeRoot':call['beforeRoot'],'afterRoot':call['afterRoot'],'result':call['slice']['Result'],'tracePCEntries':len(allpc),'exclusivePCSum':total,'exclusiveMinusReceipt':total-root,'costWithForwarded':sum(q['cost'] for q in allpc),'forwardedCallGas':sum(q.get('forwarded',0) for q in allpc),'frameCount':len(frames),'frameGasInclusiveSum':sum(q['used'] for q in frames),'rootFrame':frames[0],'functionGroups':sorted(groups.values(),key=lambda x:x['exclusiveCost'],reverse=True),'topPCs':top}
(dst/'report.json').write_text(json.dumps(out,indent=2)+'\n')
# Preserve exact raw aggregate receipts (not per-op rows) and compiler debug products compressed.
for p in [src/'padded262144-ordinary.json',src/'bigMethodRich-ordinary.json',src/'density181969-ordinary.json',src/'debug/vfs-solc.json',src/'debug/coordinator-solc.json']:
 with p.open('rb') as a,gzip.open(dst/(p.name+'.gz'),'wb',compresslevel=9) as b:b.write(a.read())
(dst/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(dst.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
