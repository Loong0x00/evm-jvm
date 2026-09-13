#!/usr/bin/env python3
"""Add a DECLARED same-JAR binding and run to the next actual EVM refusal."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();jar=Path(sys.argv[3]).resolve();namesfile=Path(sys.argv[4]).resolve();names=json.loads(namesfile.read_text());assert 0<len(names)<=24 and len(set(names))==len(names);assert not out.exists();out.mkdir();(out/'tmp').mkdir()
assert hashlib.sha256(jar.read_bytes()).hexdigest()=='fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e'
quantum=int(sys.argv[5]) if len(sys.argv)>5 else 1;assert quantum in (1,7)
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',MC_ENTRY_BINDINGS=','.join(names));w=out/'official';args=[build/'driver','setup-chain',w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',jar,quantum]
(out/'declared-bindings.json').write_text(json.dumps(names,indent=2)+'\n')
with (out/'setup.log').open('w') as f:
 p=subprocess.Popen(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
(out/'setup-process.json').write_text(json.dumps({'pid':p.pid,'exit':code,'command':list(map(str,args))})+'\n');assert code==0
m=json.loads((w/'durable-head.json').read_text());failure=out/'reports/official/start-refusal.json'
if failure.exists():
 print(failure.read_text())
else:
 with (out/'continue.log').open('w') as f:subprocess.run([sys.executable,str(here/'frontier_continue.py'),str(out),'official',str(out/'continuation'),str(jar),str(build)],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 print((out/'continue.log').read_text())
