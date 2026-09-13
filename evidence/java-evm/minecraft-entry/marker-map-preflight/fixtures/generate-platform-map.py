#!/usr/bin/env python3
"""Generated Java-8 map smoke and TEST-only host oracle; no production input."""
import hashlib,json,pathlib,subprocess,sys,zipfile
root=pathlib.Path(__file__).parent/'platformmap'; out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
classes=out/'classes'; classes.mkdir()
src=sorted(root.glob('*.java'))
subprocess.run(['javac','--release','8','-g:none','-d',str(classes),*map(str,src)],check=True)
subprocess.run(['java','-cp',str(classes),'MapMain'],check=True)
entries=['MapMain.class','MapMain$Key.class']
with zipfile.ZipFile(out/'platform-map.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in entries:
  info=zipfile.ZipInfo(name, (1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,(classes/name).read_bytes())
print(json.dumps({'compiler':'javac --release 8 -g:none','oracle':'MapMain','entries':entries,
 'zipSHA256':hashlib.sha256((out/'platform-map.zip').read_bytes()).hexdigest()},sort_keys=True))
