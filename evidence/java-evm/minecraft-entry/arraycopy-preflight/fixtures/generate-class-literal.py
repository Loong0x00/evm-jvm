#!/usr/bin/env python3
"""Generated-fixture-only Java 8 class-literal ZIPs; no production class parser."""
import hashlib,json,pathlib,subprocess,sys,zipfile
root=pathlib.Path(__file__).parent/'classliteral'; out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
classes=out/'classes'; classes.mkdir()
src=sorted(root.glob('*.java'))
subprocess.run(['javac','--release','8','-g:none','-d',str(classes),*map(str,src)],check=True)
sets={
 'class-literal.zip':['LiteralMain.class','LiteralMain$Target.class','LiteralMain$Tracker.class','LiteralMain$Face$Inner.class'],
 'wide-class-literal.zip':['WideLiteralMain.class','WideLiteralMain$Target.class'],
 'untaken-missing-literal.zip':['UntakenMissingLiteral.class'],
 'missing-literal.zip':['MissingLiteral.class'],
}
for name, entries in sets.items():
 with zipfile.ZipFile(out/name,'w',zipfile.ZIP_DEFLATED) as z:
  for e in entries:z.write(classes/e,e)
wide=subprocess.check_output(['javap','-classpath',str(classes),'-c','WideLiteralMain'],text=True)
if 'ldc_w' not in wide: raise SystemExit('wide fixture did not emit ldc_w')
for main in ('LiteralMain','WideLiteralMain','UntakenMissingLiteral'):
 subprocess.run(['java','-cp',str(classes),main],check=True)
print(json.dumps({'compiler':'javac --release 8 -g:none','oracles':['LiteralMain','WideLiteralMain','UntakenMissingLiteral'],'wideUsesLdcW':True,'zips':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in sets}},sort_keys=True))
