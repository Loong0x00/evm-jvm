#!/usr/bin/env python3
"""Trusted generated TEST sources/oracles; the execution driver only sees opaque ZIP."""
from pathlib import Path
import json,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();assert not out.exists()
src=Path(str(out)+'-sources');assert not src.exists();src.mkdir(parents=True)
for f in (root/'evidence/java-evm/link-frontier/preflight').glob('*.java'):shutil.copyfile(f,src/f.name)
shutil.copyfile(here/'cast/CastEntry.java',src/'CastEntry.java')
shutil.copyfile(root/'evidence/java-evm/link-frontier/preflight/generate_fixture.py',src/'generate_fixture.py')
subprocess.run([sys.executable,str(src/'generate_fixture.py'),str(out)],check=True)
java='/usr/lib/jvm/java-8-openjdk/bin/java';javac='/usr/lib/jvm/java-8-openjdk/bin/javac'
classes=out/'classes';oracle=out/'cast-oracle';oracle.mkdir()
subprocess.run([javac,'-source','8','-target','8','-g:none','-cp',str(classes),'-d',str(oracle),str(here/'cast/Oracle.java')],check=True)
subset=out/'cast-missing-oracle';subset.mkdir();shutil.copyfile(classes/'CastEntry.class',subset/'CastEntry.class');shutil.copyfile(oracle/'Oracle.class',subset/'Oracle.class')
answers={}
for available,cp in [('full',str(classes)+':'+str(oracle)),('missing',str(subset))]:
 for mode in (0,1):answers[f'{available}-{mode}']=subprocess.check_output([java,'-cp',cp,'Oracle',str(mode)],text=True).strip()
(out/'cast-oracle.json').write_text(json.dumps(answers,indent=2)+'\n')
assert answers=={'full-0':'R:61','full-1':'X:java.lang.ClassCastException','missing-0':'R:61','missing-1':'X:java.lang.NoClassDefFoundError'},answers
