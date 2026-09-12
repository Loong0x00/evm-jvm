#!/usr/bin/env python3
"""Copied-report negative controls only; never used as EVM execution evidence."""
import json,pathlib,shutil,subprocess,sys
base=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir(parents=True)
verifier=pathlib.Path(__file__).with_name('verify_parent.py');results=[]
for case in ('valid','overgas','q7-is-direct','cp-byte','recreate','wrong-open-root'):
 d=out/case;d.mkdir();shutil.copytree(base/'results',d/'results')
 for w in base.glob('world-*'):shutil.copytree(w/'checkpoints',d/w.name/'checkpoints')
 p=d/'results/mode1-q1-1.json';r=json.loads(p.read_text())
 if case=='overgas':r['gasUsed']=100000001;p.write_text(json.dumps(r))
 if case=='recreate':r['reopenedASOCreated']=True;p.write_text(json.dumps(r))
 if case=='wrong-open-root':r['loadedStateRoot']='0x'+'0'*64;p.write_text(json.dumps(r))
 if case=='q7-is-direct':
  for f in (d/'results').glob('mode1-q7-[0-9]*.json'):f.unlink()
  shutil.copyfile(d/'results/mode1-direct-1.json',d/'results/mode1-q7-1.json')
  shutil.copyfile(d/'results/mode1-direct-terminal.json',d/'results/mode1-q7-terminal.json')
 if case=='cp-byte':
  f=d/'world-mode1-q1/checkpoints'/(r['checkpointRoot'][2:]+'.checkpoint');b=bytearray(f.read_bytes());b[-1]^=1;f.write_bytes(b)
 done=subprocess.run([sys.executable,str(verifier),str(d)],capture_output=True,text=True)
 assert (done.returncode==0)==(case=='valid'),(case,done.stderr)
 results.append({'case':case,'exit':done.returncode,'expected':'accept' if case=='valid' else 'refuse'})
print(json.dumps(results,indent=2))
