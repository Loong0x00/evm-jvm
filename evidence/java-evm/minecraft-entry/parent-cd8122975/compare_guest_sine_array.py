#!/usr/bin/env python3
"""Read-only authenticated checkpoint diagnostic; generated Java8 oracle is NEVER execution input."""
from pathlib import Path
import hashlib,importlib.util,json,sys
here=Path(__file__).resolve().parent;root=here.parents[3];world=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();assert output.parent==here/'artifacts' and not output.exists()
head=json.loads((world/'durable-head.json').read_text());assert head['lifecycle']==1 and head['internalSteps']==81
cp=(world/'checkpoints'/f"{head['checkpointSHA256']}.bin").read_bytes();assert hashlib.sha256(cp).hexdigest()==head['checkpointSHA256']
spec=importlib.util.spec_from_file_location('checkpoint_diagnostic',here/'checkpoint_diagnostic.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);state=mod.inspect(cp)
a=next(v for v in state['heap'] if v['handle']==666);assert a['packedFloat'] and not a['sparse'] and a['count']==65536 and a['metadata']=='0x46'
assert len(a['cells'])==65536 and int(a['cells'][0],16)==0
actual={i:int(cell,16) for i,cell in enumerate(a['cells']) if int(cell,16)!=0};n=len(actual);assert sorted(actual)==list(range(1,n+1))
oracle=root/'evidence/java-evm/minecraft-entry/math-sin-independent-oracle/results/samples.tsv';contents=oracle.read_bytes();assert hashlib.sha256(contents).hexdigest()=='6001a5c714608ca9649b08b25eba27a3aa011f7c870a32ddae15ca330fefc058'
expected={};lines=contents.decode('ascii').splitlines();assert lines[0]=='kind\tkey\tx_raw_bits\tmath_sin_raw_bits\tfloat_cast_raw_bits'
for line in lines[1:65537]:
 k,i,raw,sin,result=line.split('\t');assert k=='GRID';i=int(i);assert i==len(expected);expected[i]=int(result,16)
mismatch=[{'index':i,'guest':f'{actual[i]:08x}','oracle':f'{expected[i]:08x}'} for i in sorted(actual) if actual[i]!=expected[i]]
raw_actual=b''.join(actual[i].to_bytes(4,'big') for i in sorted(actual));raw_expected=b''.join(expected[i].to_bytes(4,'big') for i in sorted(actual));report={'scope':'TEST-ONLY comparison of independently produced Java8 grid to authenticated original guest heap; never an execution authority or injected table','checkpointSHA256':head['checkpointSHA256'],'jvmSteps':head['jvmSteps'],'internalSteps':head['internalSteps'],'heapHandle':666,'arrayLength':65536,'packedNonzeroCells':n,'contiguousIndicesFromOne':True,'firstFiveGuestCells':[f'{actual[i]:08x}' for i in range(1,6)],'lastIndex':n,'mismatchCount':len(mismatch),'firstMismatches':mismatch[:8],'guestNonzeroCellsSHA256':hashlib.sha256(raw_actual).hexdigest(),'oracleMatchingCellsSHA256':hashlib.sha256(raw_expected).hexdigest(),'oracleFixtureSHA256':hashlib.sha256(contents).hexdigest(),'noOriginalJarOrClassParsing':True};output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('jvmSteps','packedNonzeroCells','mismatchCount','guestNonzeroCellsSHA256')},indent=2))
