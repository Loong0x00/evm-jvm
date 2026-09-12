#!/usr/bin/env python3
"""Read-only prototype driver memory/allocator counts, no Solidity edits."""
from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();p=out/'optimized/main.go';s=p.read_text();debug=json.loads((out/'selectedvfsassets/debug-products.json').read_text());fd=debug['contract']['evm']['deployedBytecode']['functionDebugData'];alloc=fd['allocate_and_zero_memory_struct_struct_Selected']['entryPoint'];put=fd['fun_putSelection']['entryPoint']
s=s.replace('"encoding/hex"','"encoding/hex"\n"encoding/binary"',1)
s=s.replace('type observer struct {','''type pcCost struct { MemoryBeforeMax uint64;MemoryGrowthGas uint64;MemoryGrowthBytes uint64;FreePointerIncrease uint64;FreePointerWrites uint64;FreePointerRewinds uint64 }
type observer struct {
 Memory pcCost `json:"memory"`
 SelectedAllocations uint64 `json:"selectedAllocations"`
 PutSelections uint64 `json:"putSelections"`
 AllocationSizes map[string]uint64 `json:"allocationSizes"`
''',1)
s=s.replace('o := &observer{}','o := &observer{AllocationSizes:map[string]uint64{}}',1)
needle='\tmust(setter.ParentTrace(hooks))'
code='''hooks.OnOpcode=func(pc uint64,op byte,gas,cost uint64,scope tracing.OpContext,rdata []byte,depth int,err error){
 if scope.Address()!=common.HexToAddress("0x4a564d45564d564653304152554e5449ca000001"){return}
 if pc==%d{o.SelectedAllocations++};if pc==%d{o.PutSelections++}
 memoryObservation(&o.Memory,o,"",op,cost,scope)
 }
'''%(alloc,put)
assert s.count(needle)==1;s=s.replace(needle,code+needle,1)
s+='\n'+(root/'evidence/java-evm/preparation-cost/parent-59cbf4c2c/memory_observer.go.txt').read_text()
p.write_text(s);env=dict(os.environ,TMPDIR=str(out/'tmp'))
subprocess.run(['gofmt','-w',str(p)],check=True)
subprocess.run(['go','build','-trimpath','-o',str(out/'optimized/memory-driver'),str(p)],cwd=root,env=env,check=True)
subprocess.run(['go','vet',str(p)],cwd=root,env=env,check=True)
print(json.dumps({'SelectedAllocatorEntry':alloc,'putSelectionEntry':put,'observerOnly':True},indent=2))
