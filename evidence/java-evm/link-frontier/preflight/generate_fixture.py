#!/usr/bin/env python3
"""Build only generated Java-8 link-frontier inputs; Oracle never enters the ZIP."""
import hashlib, json, pathlib, subprocess, sys, zipfile
root = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(sys.argv[1]).resolve()
if out.exists(): raise SystemExit("refusing existing output: " + str(out))
out.mkdir(parents=True)
javac=pathlib.Path('/usr/lib/jvm/java-8-openjdk/bin/javac'); java=pathlib.Path('/usr/lib/jvm/java-8-openjdk/bin/java'); javap=pathlib.Path('/usr/lib/jvm/java-8-openjdk/bin/javap')
for x in (javac,java,javap):
    if not x.is_file(): raise SystemExit('missing pinned Java 8 tool: '+str(x))
classes=out/'classes'; classes.mkdir()
sources=sorted(root.glob('*.java'))
subprocess.run([str(javac),'-source','8','-target','8','-g:none','-d',str(classes)]+[str(x) for x in sources],check=True)
# A separate host-Java oracle establishes only the generated fixture's normal semantics.
oracle=out/'Oracle.java'; oracle.write_text('public class Oracle { public static void main(String[] a) { System.out.println(LinkLauncher.run(Integer.parseInt(a[0]))); System.out.println(DemandEntry.run(0)); } }\n')
subprocess.run([str(javac),'-source','8','-target','8','-g:none','-cp',str(classes),'-d',str(out),str(oracle)],check=True)
oracleout=''.join(subprocess.check_output([str(java),'-cp',str(classes)+':'+str(out),'Oracle',mode],text=True) for mode in ('0','7'))
if oracleout != '10724\n41\n10731\n41\n': raise SystemExit('oracle mismatch '+repr(oracleout))
# The ZIP is opaque execution input; selecting known names is a CB0 assertion, not a host catalogue.
zip_path=out/'link-frontier-generated.zip'
with zipfile.ZipFile(str(zip_path),'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(classes.glob('*.class')):
  i=zipfile.ZipInfo(p.name,(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o100644<<16
  z.writestr(i,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
# javap is evidence-only inspection of generated fixture, never on execution path.
verbose={}
for p in sorted(classes.glob('*.class')):
 txt=subprocess.check_output([str(javap),'-classpath',str(classes),'-verbose',p.stem],text=True)
 (out/('javap-'+p.stem+'.txt')).write_text(txt)
 verbose[p.name]=hashlib.sha256(txt.encode()).hexdigest()
meta={'javac':subprocess.check_output([str(javac),'-version'],stderr=subprocess.STDOUT,text=True).strip(),'java':subprocess.check_output([str(java),'-version'],stderr=subprocess.STDOUT,text=True).splitlines()[0],'oracle':oracleout,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(classes.glob('*.class'))}|{zip_path.name:hashlib.sha256(zip_path.read_bytes()).hexdigest()},'javapSHA256':verbose}
(out/'fixture.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
print(zip_path)
