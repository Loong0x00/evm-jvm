#!/usr/bin/env python3
"""Independent source-only reconstruction. Never loads a generated engine as input."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
src=here.parent/'arraycopy-preflight';out=Path(sys.argv[1]).resolve();mode=sys.argv[2]
assert mode in ('candidate','repaired') and out.parent==root/'build' and out.name.startswith('java-diff-mc-entry-parent-') and not out.exists()
out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
oldAddr='0x4d434d41524b45524d4150000000000000000001';addr=oldAddr if mode=='candidate' else '0x4d434152524159434f5059504152454e54000001'
domain='MC-ARRAYCOPY-PREFLIGHT' if mode=='candidate' else 'MC-ARRAYCOPY-PARENT1'
artifacts={}
for kind,name in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 d=out/kind;d.mkdir();s=(src/kind/(name+'.sol')).read_text()
 if mode=='repaired':
  s=s.replace('MC-ARRAYCOPY-PREFLIGHT',domain)
  if kind=='engine':
   a='''        s.loaded = true;
    }

    /// @dev Bounded EVM implementation of the sole owned System native.'''
   assert s.count(a)==1;s=s.replace(a,'''        s.argumentCount = s.argumentKinds.length;
'''+a)
  else:
   s=s.replace('e26868d0da83a19f81db91913b72f0b8e64141c660dcd9fd4ab9c1faa01ef5ba',artifacts['engine']['codeHashes']['runtimeKeccak256'])
   s,n=re.subn(r'address private constant ENGINE = 0x[0-9a-fA-F]+;', 'address private constant ENGINE = address(bytes20(hex"'+addr[2:]+'"));',s);assert n==1
 (d/(name+'.sol')).write_text(s);shutil.copy2(src/kind/'build.js',d/'build.js')
 with (out/(kind+'-build.log')).open('w') as f:subprocess.run(['node',str(d/'build.js')],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 a=json.loads((d/(name+'.json')).read_text());artifacts[kind]=a
 if mode=='candidate':assert a==json.loads((src/kind/(name+'.json')).read_text()),kind
# Use the parent-confirmed bounded transport, NOT the candidate's old driver.
s=(here.parent/'parent-25b1f35a0/executed_bounded_driver.go.txt').read_text()
for a,b in [('df1418eae9dbdad7fe455ea6b8d3d1270be20527f84aa18837b80351985c2f70',artifacts['engine']['codeHashes']['runtimeSHA256']),('edc205611814164dea1c67b9c62f5de9ba5ad39e6126a87720fcf1323a238c30',artifacts['engine']['codeHashes']['runtimeKeccak256']),('213d900ca684872adf26d842e321ea11301256486fd7a25c7c8d11161120a25f',artifacts['coordinator']['codeHashes']['runtimeKeccak256']),('310375',str(len(artifacts['engine']['deployedBytecode'])//2)),('MC-MARKER-MAP-PREFLIGHT',domain),('MC-MARKER-MAP-PARENT-BOUNDED-1',domain+'-BOUNDED-1')]:
 assert a in s,a;s=s.replace(a,b)
assert oldAddr in s;s=s.replace(oldAddr,addr)
p=out/'main.go';p.write_text(s)
for cmd in (['gofmt','-w',str(p)],['go','build','-trimpath','-o',str(out/'driver'),str(p)],['go','vet',str(p)]):subprocess.run(cmd,cwd=root,env=env,check=True)
(out/'pins.json').write_text(json.dumps({'mode':mode,'address':addr,'domain':domain,**{k:{'bytes':len(a['deployedBytecode'])//2,**a['codeHashes']} for k,a in artifacts.items()}},indent=2)+'\n')
print((out/'pins.json').read_text())
