#!/usr/bin/env python3
"""Generate trusted Java-8 COW fixtures only; no original input is read."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
stage=Path(__file__).resolve().parent.parent
out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir()
classes=out/'classes'; classes.mkdir()
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; java='/usr/lib/jvm/java-8-openjdk/bin/java'
main=stage/'fixtures/CopyOnWriteArrayListMain.java'
subprocess.run([javac,'-source','8','-target','8','-g:none','-d',classes,main],check=True)
# Trusted generated-fixture oracle only: successful exit proves ordinary Java 8 behavior.
subprocess.run([java,'-cp',classes,'CopyOnWriteArrayListMain'],check=True)
z=out/'copy-on-write.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
    info=zipfile.ZipInfo('CopyOnWriteArrayListMain.class',(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
    f.writestr(info,(classes/'CopyOnWriteArrayListMain.class').read_bytes())
summary={'generatedOnly':True,'hostJava8Oracle':'CopyOnWriteArrayListMain exited 0','entries':['CopyOnWriteArrayListMain.class'],'classSHA256':hashlib.sha256((classes/'CopyOnWriteArrayListMain.class').read_bytes()).hexdigest(),'classBytes':(classes/'CopyOnWriteArrayListMain.class').stat().st_size,'zipSHA256':hashlib.sha256(z.read_bytes()).hexdigest()}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
