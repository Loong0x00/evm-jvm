#!/usr/bin/env python3
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();s=Path(__file__).with_name('driver.go.txt').read_text();m='github.com/ethereum/go-ethereum/'
for name,pkg,assets,domain in [('prototype',m+str(out.relative_to(root))+'/capacitycb0',m+str(out.relative_to(root))+'/capacitycb0/runtime','MC-CAPACITY-PREFLIGHT'),('baseline',m+'jvmevm/localcontinuation/cb0',m+'jvmevm/localcontinuation/cb0/runtime','MC-CB0')]:
 d=out/name;assert not d.exists();d.mkdir();p=d/'main.go';p.write_text(s.replace('__PACKAGE__',pkg).replace('__ASSETS__',assets).replace('__DOMAIN__',domain))
 subprocess.run(['gofmt','-w',str(p)],check=True)
 env=dict(os.environ,TMPDIR=str(out/'tmp'))
 subprocess.run(['go','build','-trimpath','-o',str(d/'driver'),str(p)],cwd=root,env=env,check=True)
 subprocess.run(['go','vet',str(p)],cwd=root,env=env,check=True)
