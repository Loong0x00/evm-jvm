#!/usr/bin/env python3
"""Build trusted Java-8 marker-link fixtures; no external inputs or Java runtime path."""
from pathlib import Path
import hashlib, json, subprocess, zipfile

root = Path(__file__).resolve().parents[1]
out = root / "generatedfixtures"
src = out / "src"
classes = out / "classes"
for d in (src, classes): d.mkdir(parents=True, exist_ok=True)
files = {
    "java/util/Map.java": "package java.util; public interface Map<K,V> {}\n",
    "java/util/SortedMap.java": "package java.util; public interface SortedMap<K,V> extends Map<K,V> {}\n",
    "java/util/NavigableMap.java": "package java.util; public interface NavigableMap<K,V> extends SortedMap<K,V> {}\n",
    "Child.java": "public interface Child extends java.util.NavigableMap<String,String> {}\n",
    "Impl.java": "public class Impl implements Child { public Impl() {} public int value() { return 7; } }\n",
    "EntryMain.java": """public final class EntryMain {
  static int result;
  public static void main(String[] ignored) {
    Object value = new Impl();
    if (!(value instanceof java.util.NavigableMap)) throw new Error();
    java.util.NavigableMap<?,?> cast = (java.util.NavigableMap<?,?>) value;
    if (cast == null || !(value instanceof Child) || ((Impl)value).value() != 7) throw new Error();
    result = 7;
  }
}
""",
}
for i in range(147): files[f"Filler{i:03}.java"] = f"public final class Filler{i:03} {{ public int value() {{ return {i}; }} }}\n"
for name, text in files.items():
    p=src/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
javac=Path('/usr/lib/jvm/java-8-openjdk/bin/javac')
assert javac.is_file()
subprocess.run([str(javac), '-source','8','-target','8','-g:none','-d',str(classes), *map(str,sorted(src.rglob('*.java')))],check=True)
names=["EntryMain.class","Impl.class","Child.class"]+[f"Filler{i:03}.class" for i in range(147)]
assert len(names)==150
archive=out/'navigable-map-raw150.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
    for n in names:
        data=(classes/n).read_bytes(); info=zipfile.ZipInfo(n,(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; z.writestr(info,data)
rows={n:{'bytes':(classes/n).stat().st_size,'sha256':hashlib.sha256((classes/n).read_bytes()).hexdigest()} for n in names}
report={'sourceFiles':len(files),'rawBindingNames':[n[:-6] for n in names],'rawBindingCount':len(names),'classBytes':rows,'totalClassBytes':sum(x['bytes'] for x in rows.values()),'zipSHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'fixture':'generated trusted Java8 only','expectedDerivedClassCount':257,'navigableMapDerivedIndex':256}
(out/'navigable-map-raw150.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('rawBindingCount','totalClassBytes','zipSHA256','expectedDerivedClassCount','navigableMapDerivedIndex')},indent=2))
