#!/usr/bin/env python3
"""Map an archived generated observer PC aggregate to unchanged Solidity spans.
No bytecode, memory, checkpoint, guest class, resource, or original artifact is emitted.
"""
import gzip, json, sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
META=json.loads(gzip.open(HERE/'MCEntryInterpreter.debug.json.gz','rt').read())
SOURCE=(ROOT/'evidence/java-evm/minecraft-entry/parent-c24d374bc/engine/MCEntryInterpreter.sol').read_text()
RUNTIME=bytes.fromhex((ROOT/'evidence/java-evm/minecraft-entry/parent-c24d374bc/engine/MCEntryInterpreter.runtime.hex').read_text().strip())
# Solidity source-map fields inherit from their preceding entry.
def source_entries(s):
    previous=[-1,0,-1,'','0']; out=[]
    for item in s.split(';'):
        values=item.split(':')
        now=previous[:]
        for i,v in enumerate(values):
            if v!='': now[i]=int(v) if i<3 else v
        out.append(tuple(now)); previous=now
    return out
def opcode_pcs(opcodes, count):
    # solc's text opcode stream preserves the executable instruction boundary;
    # trailing immutable/data bytes must not be decoded as instructions.
    tokens=opcodes.split(); out=[]; pc=0; i=0
    while i<len(tokens) and len(out)<count:
        op=tokens[i]; out.append(pc); pc+=1; i+=1
        if op.startswith('PUSH') and op!='PUSH0':
            if i>=len(tokens): raise RuntimeError('truncated PUSH')
            pc += int(op[4:]); i+=1
    return out
def linecol(offset):
    line=SOURCE.count('\n',0,offset)+1; prior=SOURCE.rfind('\n',0,offset); return [line,offset-(prior+1)+1]
def functions(node, acc):
    if isinstance(node,dict):
        if node.get('nodeType')=='FunctionDefinition':
            a,l,_=map(int,node['src'].split(':')); acc.append((a,a+l,node.get('name') or '<constructor/fallback>'))
        for v in node.values(): functions(v,acc)
    elif isinstance(node,list):
        for v in node: functions(v,acc)
def fn_for(functions, start):
    matches=[(end-start,name) for a,end,name in functions if a<=start<end]
    return min(matches)[1] if matches else '<compiler/generated>'
def main():
    if len(sys.argv)!=3: raise SystemExit('OBSERVATION.json OUTPUT.json')
    obs=json.loads(Path(sys.argv[1]).read_text()); sm=source_entries(META['deployedSourceMap']); pcs=opcode_pcs(META['opcodes'], len(sm))
    if len(sm)!=len(pcs): raise RuntimeError(f'source map/opcode mismatch {len(sm)} {len(pcs)}')
    funcs=[]; functions(META['ast'],funcs)
    bypc={pc:sm[i] for i,pc in enumerate(pcs)}; agg=defaultdict(lambda:[0,0]); last=[]
    for row in obs['enginePCs']:
        start,length,file,_,_=bypc[row['pc']]; key=fn_for(funcs,start) if file==0 and start>=0 else '<compiler/generated>'
        agg[key][0]+=row['count']; agg[key][1]+=row['cost']
    for row in obs['lastEnginePC']:
        start,length,file,_,_=bypc[row['pc']]
        x={'pc':row['pc'],'opcode':row['opcode'],'function':fn_for(funcs,start) if file==0 and start>=0 else '<compiler/generated>','sourceStart':start,'sourceLength':length}
        if file==0 and start>=0: x['lineColumn']=linecol(start); x['sourceEndLineColumn']=linecol(start+length)
        last.append(x)
    guards={}
    for name,needle in {'_checkBudgets':'function _checkBudgets','_commit':'function _commit','_execute':'function _execute'}.items():
        a=SOURCE.index(needle); guards[name]={'lineColumn':linecol(a),'sourceStart':a}
    output={'format':'MC-PROPERTIES-COST-SOURCE-MAP-1','observationSHA256':__import__('hashlib').sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'runtimeKeccak256':META['runtimeKeccak256'],'sourceMapEntries':len(sm),'guardFunctionStarts':guards,'functionTotals':[{'function':k,'opcodeCount':v[0],'opcodeCost':v[1]} for k,v in sorted(agg.items(),key=lambda x:-x[1][1])],'lastEnginePCMapped':last}
    Path(sys.argv[2]).write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__': main()
