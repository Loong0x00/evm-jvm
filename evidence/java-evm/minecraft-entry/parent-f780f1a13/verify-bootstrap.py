#!/usr/bin/env python3
"""Verify generated platform sources and all prior embedded bootstrap bytes."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
src=here.parent/'arraycopy-preflight';env=dict(os.environ,TMPDIR=str(out/'tmp'))
for f in ('build_runnable.py','build_class.py','build_platform_map.py'):
 subprocess.run([sys.executable,str(src/'bootstrap'/f),str(out/f[:-3])],env=env,check=True)
def boots(p):
 s=p.read_text();return dict(re.findall(r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";',s))
before=boots(here.parent/'marker-map-preflight/engine/MCEntryInterpreter.sol');after=boots(src/'engine/MCEntryInterpreter.sol')
assert len(before)==44 and len(after)==45 and after.keys()-before.keys()=={'_bootstrapSystem'},(len(before),len(after))
assert all(after[n]==b for n,b in before.items())
system=bytes.fromhex(after['_bootstrapSystem']);assert system==(src/'bootstrap/java/lang/System.class').read_bytes()
(out/'summary.json').write_text(json.dumps({'unchangedPriorBootstrapCount':len(before),'newSystemBytes':len(system),'newSystemSHA256':hashlib.sha256(system).hexdigest()},indent=2)+'\n')
print((out/'summary.json').read_text())
