#!/usr/bin/env python3
"""Test-only copied-report mutations; no EVM state or archived capture edits."""
import json, pathlib, shutil, subprocess, sys
root=pathlib.Path(__file__).resolve().parents[4]
base=pathlib.Path(sys.argv[1]).resolve(); out=pathlib.Path(sys.argv[2]).resolve()
assert not out.exists();out.mkdir(parents=True)
results=[]
for case in ('overgas','q7-is-direct'):
 d=out/case;d.mkdir();shutil.copytree(base/'fixture',d/'fixture');shutil.copytree(base/'results',d/'results')
 if case=='overgas':
  p=d/'results/mode1-q1-1.json';j=json.loads(p.read_text());j['gasUsed']=100000001;p.write_text(json.dumps(j))
 else:
  r=json.loads((d/'results/mode1-direct-1.json').read_text());term=json.loads((d/'results/mode1-direct-terminal.json').read_text())
  for p in (d/'results').glob('mode1-q7-[0-9]*.json'):p.unlink()
  (d/'results/mode1-q7-1.json').write_text(json.dumps(r));(d/'results/mode1-q7-terminal.json').write_text(json.dumps(term))
 p=subprocess.run([sys.executable,str(root/'evidence/java-evm/main-entry/preflight/verify.py'),str(d)],capture_output=True,text=True)
 results.append({'case':case,'originalVerifierExit':p.returncode,'acceptedBadReport':p.returncode==0})
assert all(x['acceptedBadReport'] for x in results),results
print(json.dumps(results,indent=2))
