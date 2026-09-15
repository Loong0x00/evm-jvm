#!/usr/bin/env python3
"""Trusted generated Java8 Enum fixtures only; no original artifact is read."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir(); src=out/'src'; classes=out/'classes'; src.mkdir(); classes.mkdir()
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; java='/usr/lib/jvm/java-8-openjdk/bin/java'
def build(label,sources,entries,boot=None):
 d=src/label; c=classes/label; d.mkdir(); c.mkdir()
 for n,text in sources.items(): (d/n).write_text(text)
 cmd=[javac,'-source','8','-target','8','-g:none']
 if boot: cmd += ['-bootclasspath',str(boot)]
 subprocess.run(cmd+['-d',str(c),*map(str,sorted(d.glob('*.java')))],check=True)
 # Host execution is limited to unchanged generated Java8 sources, never a patched guest image.
 if not boot: subprocess.run([java,'-cp',str(c),entries[0][:-6]],check=True)
 archive=out/(label+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
  for name in entries:
   i=zipfile.ZipInfo(name,(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_STORED; z.writestr(i,(c/name).read_bytes())
 row={'entries':entries,'bindingCount':len(entries),'zipSHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'classSHA256':{n:hashlib.sha256((c/n).read_bytes()).hexdigest() for n in entries},'classBytes':{n:(c/n).stat().st_size for n in entries},'totalClassBytes':sum((c/n).stat().st_size for n in entries),'java8HostOracle':not bool(boot)}
 (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n'); return row
main='''import java.io.Serializable;
public final class EnumBootstrapMain {
  static int result;
  public static void main(String[] ignored) {
    FocusLevel high=FocusLevel.HIGH, low=FocusLevel.LOW;
    if (high.name().length()!=4 || high.ordinal()!=2 || high.toString()!=high.name()) throw new Error();
    if (!(high instanceof Comparable) || !(high instanceof Serializable)) throw new Error();
    if (high.compareTo(low)!=2) throw new Error();
    Comparable raw=high;
    if (raw.compareTo(low)!=2) throw new Error();
    try { high.compareTo((FocusLevel)null); throw new Error(); } catch (NullPointerException expected) { result+=1; }
    try { raw.compareTo(new Object()); throw new Error(); } catch (ClassCastException expected) { result+=2; }
    if (result!=3) throw new Error();
  }
}
'''
level='enum FocusLevel { LOW, MID, HIGH }\n'
rows={'enum-bootstrap':build('enum-bootstrap',{'EnumBootstrapMain.java':main,'FocusLevel.java':level},['EnumBootstrapMain.class','FocusLevel.class'])}
# The replacement control is compiled only after removing the platform Enum. It is not
# executed by host Java; EVM must refuse raw java/lang/Enum before parsing hierarchy.
api=out/'rt-without-enum.jar'; shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar',api); subprocess.run(['zip','-q','-d',api,'java/lang/Enum.class'],check=True)
rows['raw-enum-replacement']=build('raw-enum-replacement',{'RawEnumReplacementMain.java':'public final class RawEnumReplacementMain { public static void main(String[] a) {} }\n','Enum.java':'package java.lang; public abstract class Enum<E extends Enum<E>> {}\n'},['RawEnumReplacementMain.class','java/lang/Enum.class'],api)
assert rows['enum-bootstrap']['bindingCount']==2 and rows['raw-enum-replacement']['bindingCount']==2
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
