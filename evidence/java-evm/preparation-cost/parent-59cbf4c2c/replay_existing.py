#!/usr/bin/env python3
"""Fresh EVM worlds using independently rebuilt hash-checked debug artifacts/driver."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();(out/'debug').mkdir()
for n in ('vfs-solc.json','coordinator-solc.json'):shutil.copyfile(source/'debug'/n,out/'debug'/n)
shutil.copy2(source/'prototype/driver',out/'driver');env=dict(os.environ,TMPDIR=str(out/'tmp'))
roots={'padded262144':(source/'fixtures/zips/aggregate262144.zip','BoundaryEntry,BoundaryPad'),'bigMethodRich':(source/'fixtures/zips/big-method-rich.zip','BigCaller,BigEntry'),'density181969':(source/'density.zip','BigPair,BigEntry,BigTwin')}
rows={};hashes={'driver':hashlib.sha256((out/'driver').read_bytes()).hexdigest()}
def call(label,args,timeout):
 with (out/(label+'.json')).open('w') as f,(out/(label+'.stderr')).open('w') as err:subprocess.run([str(out/'driver')]+list(map(str,args)),env=env,stdout=f,stderr=err,check=True,timeout=timeout)
 return json.loads((out/(label+'.json')).read_text())
for label,(z,names) in roots.items():
 hashes[label]=hashlib.sha256(z.read_bytes()).hexdigest();world=out/('world-'+label)
 setup=call(label+'-setup',['-command','setup','-dir',world,'-zip',z,'-names',names],120)
 r=call(label+'-ordinary',['-command','slice','-dir',world,'-length',z.stat().st_size,'-mode',7,'-gas',100000000],32);rows[label]={'setup':setup,'ordinary':r}
z=roots['density181969'][0];world=out/'world-density181969'
rows['density181969-boundary']={'setup':rows['density181969']['setup'],'ordinary':call('density181969-boundary',['-command','slice','-dir',world,'-length',z.stat().st_size,'-mode',7,'-gas',1000000000],122)}
world=out/'world-density-q1';setup=call('density-q1-setup',['-command','setup','-dir',world,'-zip',z,'-names',roots['density181969'][1]],120)
for name,q,gas,timeout in [('density-q1-first',1,100000000,32),('density-q1-refusal',1,100000000,32),('density-q1-boundary-resume',4096,1000000000,122)]:
 rows[name]={'setup':setup,'ordinary':call(name,['-command','slice','-dir',world,'-length',z.stat().st_size,'-mode',7,'-quantum',q,'-gas',gas],timeout)}
(out/'raw-summary.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'input-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
root=Path(__file__).resolve().parents[4]
with (out/'report.json').open('w') as f:subprocess.run([sys.executable,str(Path(__file__).with_name('analyze.py')),str(out)],stdout=f,check=True)
subprocess.run(['go','vet',str(source/'prototype/main.go')],cwd=root,env=env,check=True)
assert subprocess.check_output(['git','diff','ea1fa2c8a','--','core','params','jvmevm','Makefile'],cwd=root)==b''
print('PASS: seven fresh traced EVM calls, strict byte/frame/gas/roots/memory/allocator reconciliation, existing rebuilt code')
