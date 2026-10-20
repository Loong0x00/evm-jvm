#!/usr/bin/env python3
"""Parent-generated constructor/type/refusal controls; no original inputs or host guest results."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
H=Path(__file__).resolve().parent;ROOT=H.parents[3];out=Path(sys.argv[1]).resolve();assert out.parent==ROOT/'build' and out.name.startswith('java-diff-mc-array-list-local1m-fixtures-') and not out.exists();out.mkdir()
sources={
'constructor':'''package generated;
import java.util.ArrayList; import java.util.AbstractList; import java.util.AbstractCollection; import java.util.List; import java.util.RandomAccess;
public final class ConstructorMain {
 public static ArrayList held; public static int result;
 public static void main(String[] args) {
  int[] capacities={0,1,3,10,1024};
  for(int i=0;i<capacities.length;i++) { ArrayList a=new ArrayList(capacities[i]);
   if(a.size()!=0||!a.isEmpty())throw new Error();
   if(!(a instanceof AbstractList)||!(a instanceof AbstractCollection)||!(a instanceof List)||!(a instanceof RandomAccess)||!(a instanceof Cloneable)||!(a instanceof java.io.Serializable))throw new Error();
   if(a.getClass()!=ArrayList.class||a.getClass().asSubclass(List.class)!=a.getClass())throw new Error();
   int h=System.identityHashCode(a);if(h!=System.identityHashCode(a))throw new Error();
   held=a;
  }
  int caught=0;try{new ArrayList(-1);}catch(IllegalArgumentException e){caught++;}
  try{new ArrayList(Integer.MIN_VALUE);}catch(IllegalArgumentException e){caught++;}
  if(caught!=2)throw new Error(); result=12345;
 }
}''',
'list-object-fallback':'''package generated; public final class ListFallbackMain { public static int hash; public static boolean equal; public static void main(String[] x){java.util.ArrayList a=new java.util.ArrayList(3),b=new java.util.ArrayList(3);hash=a.hashCode();equal=a.equals(b);} }''',
'add-refusal':'''package generated; public final class AddMain { public static void main(String[] a){new java.util.ArrayList(3).add(null);} }''',
'iterator-refusal':'''package generated; public final class IteratorMain { public static void main(String[] a){new java.util.ArrayList(3).iterator();} }''',
'interface-add-refusal':'''package generated; public final class InterfaceAddMain { public static void main(String[] a){java.util.Collection c=new java.util.ArrayList(3);c.add(null);} }''',
'interface-iterator-refusal':'''package generated; public final class InterfaceIteratorMain { public static void main(String[] a){java.util.Collection c=new java.util.ArrayList(3);c.iterator();} }''',
'default-refusal':'''package generated; public final class DefaultMain { public static void main(String[] a){new java.util.ArrayList();} }'''
}
rows={};javac=Path('/usr/lib/jvm/java-8-openjdk/bin/javac');assert javac.is_file()
for label,text in sources.items():
 import re
 cls=re.search(r'public final class (\w+)',text).group(1);src=out/'src'/label/'generated';classes=out/'classes'/label;src.mkdir(parents=True);classes.mkdir(parents=True);p=src/(cls+'.java');p.write_text(text);subprocess.run([javac,'-g:none','-d',classes,p],cwd=ROOT,check=True)
 name='generated/'+cls+'.class';data=(classes/name).read_bytes();zp=out/(label+'.zip')
 with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_STORED) as z:
  i=zipfile.ZipInfo(name,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_STORED;z.writestr(i,data)
 row={'entries':[name],'bindingCount':1,'bootstrapCount':99,'classBytes':len(data),'classSHA256':hashlib.sha256(data).hexdigest(),'zipSHA256':hashlib.sha256(zp.read_bytes()).hexdigest(),'hostGuestExecution':False};(out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');rows[label]=row
(out/'summary.json').write_text(json.dumps({'generatedOnly':True,'fixtures':rows},indent=2)+'\n');print(json.dumps({'fixtures':len(rows),'generatedOnly':True}))
