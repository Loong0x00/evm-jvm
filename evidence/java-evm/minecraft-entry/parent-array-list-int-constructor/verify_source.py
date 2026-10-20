#!/usr/bin/env python3
"""Independent append-only ArrayList source checks before any parent EVM acceptance."""
from pathlib import Path
import json,os,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE.parent/'parent-raw75-byte531965/artifacts/engine/MCEntryInterpreter.sol'
CAND=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE.parent/'array-list-int-constructor/engine/MCEntryInterpreter.sol'

def bodies(text):
 out={}
 for m in re.finditer(r'^    function\s+(\w+)\s*\(',text,re.M):
  at=text.index('{',m.end());depth=1;i=at+1;quote=None
  while depth:
   c=text[i]
   if quote:
    if c=='\\':i+=2;continue
    if c==quote:quote=None
   elif text.startswith('//',i):
    i=text.index('\n',i);continue
   elif text.startswith('/*',i):
    i=text.index('*/',i+2)+2;continue
   elif c in ('"',"'"):quote=c
   elif c=='{':depth+=1
   elif c=='}':depth-=1
   i+=1
  out.setdefault(m.group(1),[]).append(text[m.start():i])
 return out

def clean(s):return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))
base=BASE.read_text();source=CAND.read_text();b=bodies(base);c=bodies(source)
allowed={'_bootstrapRoot','_prepare','_isReservedCollectionClass','_appendTailBootstraps'}
assert set(b)<=set(c)
changed={name for name in b if b[name]!=c[name]};assert changed<=allowed,changed
assert set(c)-set(b)<={'_bootstrapAbstractList','_bootstrapArrayList','_appendArrayListBootstraps'}
# Exact _prepare count change; no allocation, method or execution-path alteration.
assert clean(c['_prepare'][0])==clean(b['_prepare'][0].replace('inputCount + 91','inputCount + 93',1))
for name in b:
 if name not in allowed:assert b[name]==c[name],name
# Root logic has only two appended literal-image commitments.
r=clean(c['_bootstrapRoot'][0]);e=clean(b['_bootstrapRoot'][0]).replace('newbytes32[](97)','newbytes32[](99)').replace('h[96]=DBOOT_RANDOM;','h[96]=DBOOT_RANDOM;h[97]=DBOOT_ABSTRACT_LIST;h[98]=DBOOT_ARRAY_LIST;');assert r==e,'root outside exact append'
reserve=clean(c['_isReservedCollectionClass'][0])
for name in ('java/util/ArrayList','java/util/AbstractList'):
 token='||_isNamedClass(c,bytes("'+name+'"))';assert reserve.count(token)==1;reserve=reserve.replace(token,'',1)
assert reserve==clean(b['_isReservedCollectionClass'][0])
tail=clean(b['_appendTailBootstraps'][0]);actual_tail=clean(c['_appendTailBootstraps'][0])
marker='p.classes[classSlot+57].data=_bootstrapRandom();'
direct=marker+'p.classes[classSlot+58].data=_bootstrapAbstractList();p.classes[classSlot+59].data=_bootstrapArrayList();'
outlined=marker+'_appendArrayListBootstraps(p.classes,classSlot+58);'
assert actual_tail in (tail.replace(marker,direct,1),tail.replace(marker,outlined,1))
if '_appendArrayListBootstraps' in c:
 assert clean(c['_appendArrayListBootstraps'][0])=='function_appendArrayListBootstraps(ClassInfo[]memoryclasses,uint256at)privatepure{classes[at].data=_bootstrapAbstractList();classes[at+1].data=_bootstrapArrayList();}'
def without_functions(text,functions):
 for items in functions.values():
  for item in items:assert text.count(item)==1;text=text.replace(item,'',1)
 return text
global_base=without_functions(base,b);global_new=without_functions(source,c)
for name in ('ABSTRACT_LIST','ARRAY_LIST'):
 pattern=r'bytes32 private constant DBOOT_'+name+r' = hex"[0-9a-f]{64}";';global_new,n=re.subn(pattern,'',global_new);assert n==1
assert clean(global_new)==clean(global_base),'global state/constant delta exceeds two new commitments'
# No existing non-collection reservation or class/image function can change.
env=dict(os.environ,NODE_PATH=str(ROOT/'jvmevm/runtime/node_modules'))
from root_helper import root_record
old=root_record(base,'JVMEVM:MC-RANDOM-CLASS-P28:BOOTSTRAP:1',ROOT,env)
new=root_record(source,'JVMEVM:MC-RANDOM-CLASS-P28:BOOTSTRAP:1',ROOT,env)
assert len(old['leaves'])==97 and len(new['leaves'])==99 and new['leaves'][:97]==old['leaves']
print(json.dumps({'result':'PASS','baseLeaves':97,'candidateLeaves':99,'old97ImageFunctionsAndHashesUnchanged':True,'allowedChangedFunctions':sorted(changed),'newFunctions':sorted(set(c)-set(b)),'newExactImageCommitmentsVerified':True,'candidateSameP28Root':new['root']},indent=2))
