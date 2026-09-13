#!/usr/bin/env python3
"""Static integrity checks for the generated-only defining-loader archive."""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent; A=D/'artifacts'; s=(A/'engine/MCEntryInterpreter.sol').read_text()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def images(t): return dict(re.findall(r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)"',t))
base=(D.parent/'parent-cc0c40e71'/'engine'/'MCEntryInterpreter.sol').read_text(); old=images(base); new=images(s)
assert len(old)==51 and len(new)==52
assert all(k=='_bootstrapClass' or new.get(k)==v for k,v in old.items())
assert '_bootstrapVMClassLoader' in new and len(bytes.fromhex(new['_bootstrapVMClassLoader']))==143
assert s.count('MC-CLASS-DEFINING-LOADER-PREFLIGHT1')==9 and 'MC-THREAD-CONTEXT-PREFLIGHT1' not in s
eng=json.loads((A/'engine/MCEntryInterpreter.json').read_text()); assert len(eng['deployedBytecode'])//2==327658 <= 320*1024
for n,want in [('Class.class','4e13134b8f82af8fb51b268f92fea91ccf3ed731b1adcb24eddc66b1889913bd'),('ClassLoader.class','df3b18c48b514343c2dcf9d025afd714027e319db03174c8f831215645f39e8b'),('VMClassLoader.class','936fc65d33d3b2f7d9c2267b8e62c42e58c8135b35d6e4d08f65daec831cf944')]: assert sha(A/'bootstrap/java/lang'/n)==want
print(json.dumps({'prior51ExceptClassExact':True,'bootstrapCount':52,'runtimeBytes':len(eng['deployedBytecode'])//2,'runtimeSHA256':eng['codeHashes']['runtimeSHA256'],'runtimeKeccak256':eng['codeHashes']['runtimeKeccak256']},indent=2))
