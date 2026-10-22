#!/usr/bin/env python3
"""Generate isolated namespace-replacement and omitted-navigation-API fixtures."""
from pathlib import Path
import hashlib, json, subprocess, zipfile
root=Path(__file__).resolve().parents[1]; out=root/'generatedfixtures'; srcroot=out/'refusal-src'; clroot=out/'refusal-classes'
for d in (srcroot,clroot): d.mkdir(parents=True,exist_ok=True)
javac='/usr/lib/jvm/java-8-openjdk/bin/javac'
def build(label, files, entries):
 src=srcroot/label; cls=clroot/label; src.mkdir(parents=True,exist_ok=True); cls.mkdir(parents=True,exist_ok=True)
 for name,text in files.items():
  p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 subprocess.run([javac,'-source','8','-target','8','-g:none','-d',str(cls),*map(str,sorted(src.rglob('*.java')))],check=True)
 zpath=out/(label+'.zip')
 with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_STORED) as z:
  for name in entries:
   data=(cls/name).read_bytes(); i=zipfile.ZipInfo(name,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_STORED;z.writestr(i,data)
  if label.startswith('raw-navigable-map'):
   data=(root/'generatedfixtures/java/util/NavigableMap.class').read_bytes();i=zipfile.ZipInfo('java/util/NavigableMap.class',(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_STORED;z.writestr(i,data)
 return {'entries':entries+(['java/util/NavigableMap.class'] if label=='raw-navigable-map' else []),'sha256':hashlib.sha256(zpath.read_bytes()).hexdigest(),'bytes':zpath.stat().st_size}
a=build('raw-navigable-map-v2-exact-image',{'CollisionMain.java':'public final class CollisionMain { public static void main(String[] x) {} }\n'},['CollisionMain.class'])
b=build('omitted-navigation-api-v2',{
 'java/util/Map.java':'package java.util; public interface Map<K,V> {}\n',
 'java/util/SortedMap.java':'package java.util; public interface SortedMap<K,V> extends Map<K,V> {}\n',
 'java/util/NavigableMap.java':'package java.util; public interface NavigableMap<K,V> extends SortedMap<K,V> { NavigableMap<K,V> descendingMap(); }\n',
 'Impl.java':'public class Impl implements java.util.NavigableMap<String,String> { public Impl() {} public java.util.NavigableMap<String,String> descendingMap() { return null; } }\n',
 'OmittedMain.java':'public final class OmittedMain { public static void main(String[] x) { ((java.util.NavigableMap<String,String>)new Impl()).descendingMap(); } }\n',
},['OmittedMain.class','Impl.class'])
(out/'refusal-fixtures.json').write_text(json.dumps({'rawNamespace':a,'omittedAPI':b,'scope':'generated Java 8 only'},indent=2)+'\n')
print(json.dumps({'rawNamespace':a,'omittedAPI':b},indent=2))
