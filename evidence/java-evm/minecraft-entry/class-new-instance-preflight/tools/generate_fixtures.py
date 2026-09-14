#!/usr/bin/env python3
"""Generate trusted Java-8 Class.newInstance fixtures only; no original inputs."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
stage=Path(__file__).resolve().parent.parent
out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir()
classes=out/'classes'; classes.mkdir(); src=stage/'fixtures'
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; java='/usr/lib/jvm/java-8-openjdk/bin/java'
all_sources=sorted(src.glob('*.java'))
subprocess.run([javac,'-source','8','-target','8','-g:none','-d',classes,*all_sources],check=True)
# Trusted host-JVM oracle is only used for success/null fixture construction.
for main in ('NewInstanceMain','NullNewInstanceMain'):
    subprocess.run([java,'-cp',classes,main],check=True)
cases={
 'success':['NewInstanceMain.class','NewInstanceTarget.class'],
 'null':['NullNewInstanceMain.class'],
 'bootstrap-refusal':['UnsupportedBootstrapMain.class'],
 'abstract-refusal':['UnsupportedAbstractMain.class','AbstractNewInstanceTarget.class'],
 'constructor-refusal':['UnsupportedConstructorMain.class','PrivateNewInstanceTarget.class'],
}
rows={}
for label,names in cases.items():
    z=out/(label+'.zip')
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
        for name in names:
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            f.writestr(info,(classes/name).read_bytes())
    rows[label]={'entries':names,'zipSHA256':hashlib.sha256(z.read_bytes()).hexdigest(),
      'classSHA256':{n:hashlib.sha256((classes/n).read_bytes()).hexdigest() for n in names},
      'classBytes':{n:(classes/n).stat().st_size for n in names}}
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
