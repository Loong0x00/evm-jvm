#!/usr/bin/env python3
"""Independent source-only candidate/repair compiler + bounded original-safe driver."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'properties-preflight';old=here.parent/'parent-6748eb593'
out=Path(sys.argv[1]).resolve();mode=sys.argv[2];assert mode in ('candidate','repaired') and out.parent==root/'build' and out.name.startswith('java-diff-mc-properties-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
for kind in ('engine','coordinator'):
 (out/kind).mkdir()
 for f in (('MCEntryInterpreter.sol','build.js') if kind=='engine' else ('MCEntryCoordinator.sol','build.js')):shutil.copy2(src/kind/f,out/kind/f)
shutil.copytree(src/'bootstrap',out/'bootstrap')
if mode=='repaired':
 p=out/'bootstrap/java/util/Properties.java';s=p.read_text();assert s.count('Object value = get(key);')==1;p.write_text(s.replace('Object value = get(key);','Object value = super.get(key);'))
with (out/'bootstrap-build.log').open('w') as f:subprocess.run([sys.executable,str(out/'bootstrap/build_bootstraps.py')],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
engine=out/'engine/MCEntryInterpreter.sol';s=engine.read_text()
for n in ('Dictionary','Hashtable','Properties'):
 raw=(out/('bootstrap/java/util/'+n+'.class.hex')).read_text().strip()
 pattern=r'(function _bootstrap'+n+r'\(\) private pure returns \(bytes memory\) \{ return hex")([0-9a-f]+)("; \})'
 m=re.search(pattern,s);assert m
 if mode=='candidate':assert m.group(2)==raw
 else:s,k=re.subn(pattern,lambda m:m.group(1)+raw+m.group(3),s);assert k==1
oldaddr='4d4350524f504552544945535046000000000001';addr=oldaddr if mode=='candidate' else '4d4350524f50455254494553504152454e540001';domain='MC-PROPERTIES-PREFLIGHT1' if mode=='candidate' else 'MC-PROPERTIES-PARENT1'
assert len(bytes.fromhex(addr))==20
s=s.replace('MC-PROPERTIES-PREFLIGHT1',domain);engine.write_text(s)
# All preceding45 bootstrap byte images remain identical.
pat=r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
a=dict(re.findall(pat,(old/'engine/MCEntryInterpreter.sol').read_text()));b=dict(re.findall(pat,s));assert len(a)==45 and len(b)==48 and all(b[n]==v for n,v in a.items())
artifacts={}
for kind,name in (('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')):
 if kind=='coordinator' and mode=='repaired':
  p=out/kind/(name+'.sol');c=p.read_text().replace('MC-PROPERTIES-PREFLIGHT1',domain).replace('6d0246f86987ae5bc90129b521cc342e7c36a86cc4b5c0ce22c7df8985264f29',artifacts['engine']['codeHashes']['runtimeKeccak256'])
  c,k=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"'+addr+'"));',c);assert k==1;p.write_text(c)
 with (out/(kind+'-build.log')).open('w') as f:subprocess.run(['node',str(out/kind/'build.js')],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 j=json.loads((out/kind/(name+'.json')).read_text());artifacts[kind]=j
 if mode=='candidate':assert j==json.loads((src/kind/(name+'.json')).read_text()),kind
s=(old/'executed_bounded_driver.go.txt').read_text()
for a,b in [('9f272f78fb59ffc827a7456073cbfefa70c8b1f6c7b70731d505161194f2ee3c',artifacts['engine']['codeHashes']['runtimeSHA256']),('b840a1368591f665791e3a2458e311c06a6ec47a68116e26748adaf0c9e74b60',artifacts['engine']['codeHashes']['runtimeKeccak256']),('16b9c3624206cbd7a183bd270df3608f199047cb29b09dd742ac184ef4eb46ba',artifacts['coordinator']['codeHashes']['runtimeKeccak256']),('0x4d43434c415353434f554e543234000000000001','0x'+addr),('MC-CLASSCOUNT24-PREFLIGHT1',domain),('MC-CLASSCOUNT24-PARENT-BOUNDED-1',domain+'-BOUNDED-1'),('314365',str(len(artifacts['engine']['deployedBytecode'])//2))]:
 assert a in s,a;s=s.replace(a,b)
p=out/'main.go';p.write_text(s)
for args in (['gofmt','-w',str(p)],['go','build','-trimpath','-o',str(out/'driver'),str(p)],['go','vet',str(p)]):subprocess.run(args,cwd=root,env=env,check=True)
(out/'pins.json').write_text(json.dumps({'mode':mode,'address':'0x'+addr,'domain':domain,**{k:{'bytes':len(v['deployedBytecode'])//2,**v['codeHashes']} for k,v in artifacts.items()}},indent=2)+'\n')
print((out/'pins.json').read_text())
