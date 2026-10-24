"""Exact ordered source commitments for the bounded LOCAL raw160 profile."""
import json,re,subprocess

def leaf_pairs(source):
 body=source[source.index('    function _bootstrapRoot('):];body=body[:body.index('\n    function ',1)]
 count=int(re.search(r'new bytes32\[\]\((\d+)\)',body).group(1));rows={int(i):x.strip() for i,x in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',body)}
 assert set(rows)==set(range(count));pairs=[]
 for i in range(count):
  rhs=rows[i];m=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',rhs)
  if m:
   f=source[source.index('    function '+m.group(1)+'('):];end=f.find('\n    function ',1);f=f[:end] if end>=0 else f;v=re.findall(r'hex"([0-9a-f]+)"',f);assert len(v)==1,(i,m.group(1));pairs.append(['image',v[0]])
  else:
   assert re.fullmatch(r'DBOOT_[A-Z_]+',rhs),(i,rhs)
   expr=re.search(r'bytes32 private constant '+rhs+r'\s*=\s*([^;]+);',source).group(1).strip();v=re.findall(r'hex"([0-9a-f]+)"',expr);assert len(v)==1;pairs.append(['image' if expr.startswith('keccak256(') else 'hexhash',v[0]])
 return pairs

def root_record(source,domain,root_dir,environment):
 match=re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\);',source)
 assert match, 'source must define bootstrap domain from actual DBOOT literal'
 assert domain==match.group(1), (domain,match.group(1))
 assert domain.startswith('JVMEVM:'), 'keep JVMEVM domain prefix'
 pairs=leaf_pairs(source)
 js="""const fs=require('fs'),{keccak256:k}=require('js-sha3');let x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');const hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(JSON.stringify({root:k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(hs.length),...hs.map(v=>Buffer.from(v,'hex'))])),leaves:hs}));"""
 p=subprocess.run(['node','-e',js],cwd=root_dir,env=environment,input=json.dumps({'domain':domain,'pairs':pairs}),capture_output=True,text=True,check=True);out=json.loads(p.stdout);assert len(out['leaves'])==len(pairs) and len(pairs) in (127,128)
 for i,name,fn in ((89,'Math','Math'),(97,'AbstractList','AbstractList'),(98,'ArrayList','ArrayList'),(99,'IdentityHashMap','IdentityHashMap'),(100,'HashMap','HashMap'),(101,'Pattern','Pattern'),(102,'PatternSyntaxException','PatternSyntaxException'),(103,'Matcher','Matcher'),(104,'HashMapNode','HashMapNode'),(105,'Function','Function'),(106,'NavigableMap','NavigableMap'),(107,'Comparator','Comparator'),(108,'SortedSet','SortedSet'),(109,'NavigableSet','NavigableSet'),(110,'HashMapEntrySet','HashMapEntrySet'),(111,'HashMapEntryIterator','HashMapEntryIterator'),(112,'ConcurrentModificationException','ConcurrentModificationException'),(113,'LinkedHashMap','LinkedHashMap'),(114,'ListIterator','ListIterator'),(115,'ArrayListItr','ArrayListItr'),(116,'ReflectArray','ReflectArray'),(117,'Collections','Collections'),(118,'SingletonList','SingletonList'),(119,'SingletonIterator','SingletonIterator'),(120,'Arrays','Arrays'),(121,'Arrays$ArrayList','ArraysArrayList'),(122,'Arrays$ArrayIterator','ArraysArrayIterator')):
  if i>=len(pairs): continue
  m=re.search(r'function _bootstrap'+fn+r'\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',source);assert m,name
  x=subprocess.run(['node','-e',"const {keccak256:k}=require('js-sha3');console.log(k(Buffer.from(process.argv[1],'hex')))",m.group(1)],cwd=root_dir,env=environment,capture_output=True,text=True,check=True).stdout.strip();assert x==out['leaves'][i],(i,name,'new commitment/materializer mismatch')
 return out
