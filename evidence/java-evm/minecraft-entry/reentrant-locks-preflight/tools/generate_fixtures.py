#!/usr/bin/env python3
"""Generate trusted Java-8 lock/COW fixtures only; no original input is read."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
stage=Path(__file__).resolve().parent.parent
out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir()
classes=out/'classes'; classes.mkdir()
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; java='/usr/lib/jvm/java-8-openjdk/bin/java'
mains=('ReentrantLocksMain','CopyOnWriteArrayListMain')
for name in mains:
    subprocess.run([javac,'-source','8','-target','8','-g:none','-d',classes,stage/'fixtures'/(name+'.java')],check=True)
    subprocess.run([java,'-cp',classes,name],check=True)
entries={}
for name,archive in (('ReentrantLocksMain','reentrant-locks.zip'),('CopyOnWriteArrayListMain','copy-on-write.zip')):
    z=out/archive
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
        info=zipfile.ZipInfo(name+'.class',(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
        f.writestr(info,(classes/(name+'.class')).read_bytes())
    data=(classes/(name+'.class')).read_bytes()
    entries[name]={'oracle':name+' exited 0','classSHA256':hashlib.sha256(data).hexdigest(),'classBytes':len(data),'zipSHA256':hashlib.sha256(z.read_bytes()).hexdigest()}
summary={'generatedOnly':True,'hostJava8Oracle':entries,'entries':[name+'.class' for name in mains]}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
