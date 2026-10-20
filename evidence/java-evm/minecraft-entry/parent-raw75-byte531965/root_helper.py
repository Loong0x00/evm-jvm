import json,re,subprocess
def root_from_source(text,domain):
 body=text[text.index('    function _bootstrapRoot('):];body=body[:body.index('\n    function ',1)]
 rhs={int(i):v.strip() for i,v in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',body)};assert set(rhs)==set(range(97));pairs=[]
 for i in range(97):
  expr=rhs[i];m=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',expr)
  if m:
   f=text[text.index('    function '+m.group(1)+'('):];f=f[:f.index('\n    function ',1)];v=re.findall(r'hex"([0-9a-f]+)"',f);assert len(v)==1;pairs.append(['image',v[0]])
  else:
   assert re.fullmatch(r'DBOOT_[A-Z_]+',expr);v=re.search(r'bytes32 private constant '+expr+r'\s*=\s*([^;]+);',text).group(1).strip();h=re.findall(r'hex"([0-9a-f]+)"',v);assert len(h)==1;pairs.append(['image' if v.startswith('keccak256(') else 'hexhash',h[0]])
 node="""const fs=require('fs'),{keccak256:k}=require('js-sha3');const x=JSON.parse(fs.readFileSync(0,'utf8'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');let hs=x.pairs.map(([t,v])=>t==='image'?k(Buffer.from(v,'hex')):v);console.log(k(Buffer.concat([Buffer.from(k(x.domain),'hex'),w(64),w(97),...hs.map(v=>Buffer.from(v,'hex'))])));"""
 p=subprocess.run(['node','-e',node],cwd=ROOT,env=env,input=json.dumps({'domain':domain,'pairs':pairs}),text=True,capture_output=True,check=True);value=p.stdout.strip();assert re.fullmatch('[0-9a-f]{64}',value);return value