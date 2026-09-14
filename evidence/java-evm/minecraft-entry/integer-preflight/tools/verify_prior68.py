#!/usr/bin/env python3
"""Verify append-only image identity against the parent-restored 68-image source."""
from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent.parent
prior=here.parent/'parent-6e7185d9c/engine/MCEntryInterpreter.sol'
old=prior.read_text(); new=(here/'engine/MCEntryInterpreter.sol').read_text()
def image(s,i):
 m=re.search(r'h\['+str(i)+r'\] = keccak256\(_(bootstrap\w+)\(\)\);',s); assert m,i
 f=m.group(1); x=re.search(r'function _'+f+r'\(\).*?hex"([0-9a-f]+)";',s,re.S); assert x,f
 return f,bytes.fromhex(x.group(1))
rows=[]
for i in range(68):
 a,ab=image(old,i);b,bb=image(new,i);assert a==b and ab==bb,(i,a,b)
 rows.append({'index':i,'function':a,'bytes':len(ab),'sha256':hashlib.sha256(ab).hexdigest()})
print(json.dumps({'prior68Exact':True,'images':rows},indent=2))
