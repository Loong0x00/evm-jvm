#!/usr/bin/env python3
"""Generated fixture only; host Java/ZIP builder is NOT execution authority."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir();c=out/'classes';c.mkdir()
subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-d',str(c),str(here/'EdgeMain.java')],check=True)
subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',str(c),'EdgeMain'],check=True)
names=['EdgeMain.class','EdgeMain$Marker.class','EdgeMain$A.class','EdgeMain$B.class']
with zipfile.ZipFile(out/'arraycopy.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in names:
  i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(c/n).read_bytes())
print(json.dumps({'java8TESTOracle':True,'classes':{n:hashlib.sha256((c/n).read_bytes()).hexdigest() for n in names}},indent=2))
