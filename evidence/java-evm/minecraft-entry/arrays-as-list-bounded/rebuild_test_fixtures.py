#!/usr/bin/env python3
"""Rebuild generated Java 8 oracle/EVM fixture classfiles in a fresh directory."""
import pathlib,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parent
if len(sys.argv)!=2: raise SystemExit('usage: rebuild_test_fixtures.py NEW_OUTPUT_DIRECTORY')
out=pathlib.Path(sys.argv[1]).resolve()
if out.exists(): raise SystemExit('refusing to reuse existing attempt path: '+str(out))
classes=out/'classes';pads=out/'pads';refusals=out/'refusal-classes';refusal_zips=out/'refusal-zips'
classes.mkdir(parents=True);pads.mkdir();refusals.mkdir();refusal_zips.mkdir()
for i in range(149):
    (pads/f'ArraysAsListPad{i:03}.java').write_text(f'public final class ArraysAsListPad{i:03} {{ public int id() {{ return {i}; }} }}\n')
javac='/usr/lib/jvm/java-8-openjdk/bin/javac';java='/usr/lib/jvm/java-8-openjdk/bin/java'
subprocess.run([javac,'-g:none','-source','8','-target','8','-d',str(classes),str(ROOT/'tests/ArraysAsListProbe.java')],check=True)
subprocess.run([javac,'-g:none','-source','8','-target','8','-classpath',str(classes),'-d',str(classes),*map(str,sorted(pads.glob('*.java')))],check=True)
# Host execution is only the generated-fixture oracle, never an original program input.
subprocess.run([java,'-cp',str(classes),'ArraysAsListProbe'],check=True)
for source in sorted((ROOT/'tests/refusals').glob('*.java')):
    d=refusals/source.stem;d.mkdir()
    subprocess.run([javac,'-g:none','-source','8','-target','8','-d',str(d),str(source)],check=True)
def archive(path,files):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
        for p in files:
            info=zipfile.ZipInfo(p.name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED
            z.writestr(info,p.read_bytes())
archive(out/'arrays-as-list-fixture.zip',sorted(classes.glob('*.class')))
archive(out/'arrays-as-list-single-fixture.zip',[classes/'ArraysAsListProbe.class'])
for src in sorted((ROOT/'tests/refusals').glob('*.java')):
    p=refusals/src.stem/(src.stem+'.class')
    archive(refusal_zips/(src.stem+'.zip'),[p])
print('generated 150 raw classfiles, single-class positive fixture, and refusal fixtures under',out)
