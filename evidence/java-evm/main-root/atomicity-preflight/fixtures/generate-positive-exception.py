#!/usr/bin/env python3
# TEST-only fixture builder. Oracle.class is deliberately excluded from opaque ZIPs.
import hashlib,json,pathlib,subprocess,sys,zipfile
root=pathlib.Path(__file__).parent; out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
classes=out/'classes'; classes.mkdir(exist_ok=True)
src=[root/'MainPositive.java',root/'MainHelper.java',root/'MainException.java',root/'MainRebind.java',root/'MainRebindNew.java',root/'Oracle.java']
subprocess.run(['javac','--release','8','-g:none','-d',str(classes),*map(str,src)],check=True)
for name, entries in [('positive.zip',['MainPositive.class','MainHelper.class']),('exception.zip',['MainException.class']),('rebind.zip',['MainRebind.class']),('rebind-new.zip',['MainRebindNew.class'])]:
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for e in entries: z.write(classes/e,e)
print(json.dumps({'compiler':'javac --release 8 -g:none','positiveSHA256':hashlib.sha256((out/'positive.zip').read_bytes()).hexdigest(),'exceptionSHA256':hashlib.sha256((out/'exception.zip').read_bytes()).hexdigest(),'oracleExcluded':True},sort_keys=True))
