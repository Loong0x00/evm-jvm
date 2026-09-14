import java.net.URL;
import java.security.PrivilegedAction;
import java.util.Collection;
import java.util.Enumeration;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.NoSuchElementException;
import java.util.Properties;
import java.util.Set;

/** Generated positive/negative indexed resource control plus prior measured paths. */
public final class ParentResourceEnumerationProbe {
  static int done,seen;
  static final class Target { static { seen++; } }
  static final class Old { public int hashCode(){return 11;} public boolean equals(Object o){return false;} }
  static final class New { public int hashCode(){return 11;} public boolean equals(Object o){return o instanceof Old;} }
  static final class StringAction implements PrivilegedAction<String> { public String run(){return "resource-action";} }
  static void require(boolean x){if(!x){int z=0;int y=1/z;}}
  static void same(String[] a,String[] b){require(a.length==b.length);for(int i=0;i<a.length;i++)require(a[i].equals(b[i]));}
  @SuppressWarnings("rawtypes") static Object erased(PrivilegedAction x){return x.run();}
  public static void main(String[] ignored) throws Exception {
    ClassLoader loader=ParentResourceEnumerationProbe.class.getClassLoader();
    require(loader!=null && loader==ClassLoader.getSystemClassLoader() && seen==0);
    Class<?> loaded=loader.loadClass("ParentResourceEnumerationProbe$Target");
    require(loaded==loader.loadClass("ParentResourceEnumerationProbe$Target") && loaded==Target.class && seen==0);
    require(loaded.getClassLoader()==loader && Old.class.getClassLoader()==loader);
    Class<?> boot=loader.loadClass("java.lang.Boolean");
    require(boot==Boolean.class && boot.getClassLoader()==null);
    try { loader.loadClass("missing.parent.Optional"); require(false); }
    catch (ClassNotFoundException expected) { require(expected instanceof ReflectiveOperationException); }
    try { loader.loadClass("bad/name"); require(false); }
    catch (ReflectiveOperationException expected) { require(expected instanceof ClassNotFoundException); }
    try { Class.forName("missing.parent.ForNameOptional"); require(false); }
    catch (ClassNotFoundException expected) { require(expected instanceof ReflectiveOperationException); }
    try { Class.forName("bad/forName"); require(false); }
    catch (ReflectiveOperationException expected) { require(expected instanceof ClassNotFoundException); }
    require(ClassLoader.class.getClassLoader()==null && Class.class.getClassLoader()==null);
    require(System.getProperty("mc.parent.absent")==null && System.getProperty("mc.parent.absent")==null);
    require("1.8".equals(System.getProperty("java.version")));
    String regex="-|\\.";same("1.8".split(regex),new String[]{"1","8"});
    same("a..b-".split(regex),new String[]{"a","","b"});same("a--".split(regex),new String[]{"a"});
    String noMatch="abc",empty="";String[] noMatchParts=noMatch.split(regex),emptyParts=empty.split(regex);
    require(noMatchParts.length==1&&noMatchParts[0]==noMatch&&emptyParts.length==1&&emptyParts[0]==empty);
    require(".".split(regex).length==0);String[] derived="a.b".split(regex);require(derived[0]!="a"&&derived[1]!="b");
    char[] chars={'x'};String constructed=new String(chars);chars[0]='y';String copied=new String(constructed);
    require("x".equals(constructed)&&copied!=constructed&&copied.equals(constructed));
    try{((String)null).split(regex);require(false);}catch(NullPointerException expected){}
    try{"a".split(null);require(false);}catch(NullPointerException expected){}
    SplitOOMProbe.check();
    require(Integer.parseInt("1")==1&&Integer.parseInt("8")==8&&Integer.parseInt("-0")==0);
    try{Integer.parseInt("2147483648");require(false);}catch(NumberFormatException expected){require(expected instanceof IllegalArgumentException);}
    Integer ia=new Integer(5),ib=new Integer("5");Number number=ia;Comparable<Integer> integerComparable=ia;
    require(ia.equals(ib)&&number.intValue()==5&&number.longValue()==5L&&integerComparable.compareTo(ib)==0);
    try{System.getProperty(null);require(false);}catch(NullPointerException expected){}
    try{System.getProperty("");require(false);}catch(IllegalArgumentException expected){}
    Boolean t=Boolean.valueOf(true),f=Boolean.valueOf(false),nt=new Boolean(true),nf=new Boolean(false);
    require(t==Boolean.TRUE && f==Boolean.FALSE && t==Boolean.valueOf(true) && f==Boolean.valueOf(false));
    require(nt!=t && nf!=f && nt.equals(t) && nf.equals(f) && !nt.equals(nf));
    require(t.booleanValue() && !f.booleanValue() && t.hashCode()==1231 && f.hashCode()==1237);
    require("true".equals(t.toString()) && "false".equals(Boolean.toString(false)));
    require(Boolean.compare(false,true)<0 && Boolean.compare(true,false)>0 && Boolean.compare(true,true)==0);
    Comparable<Boolean> comparable=t;require(comparable.compareTo(f)>0 && t.compareTo(nt)==0);
    Enumeration<URL> first=loader.getResources("probe/resource.txt");
    require(first.hasMoreElements());URL one=first.nextElement();require(!first.hasMoreElements());
    try{first.nextElement();require(false);}catch(NoSuchElementException expected){}
    Enumeration<URL> second=loader.getResources("probe/resource.txt");
    require(second.hasMoreElements());URL two=second.nextElement();require(!second.hasMoreElements());
    require(one!=two && one.equals(two) && two.equals(one) && one.hashCode()==two.hashCode());
    require("probe/resource.txt".equals(one.toString()));
    Enumeration<URL> missing=loader.getResources("probe/missing.txt");
    require(!missing.hasMoreElements());try{missing.nextElement();require(false);}catch(NoSuchElementException expected){}
    Collection<URL> urls=new LinkedHashSet<URL>();require(urls.add(one)&&!urls.add(two)&&urls.size()==1);
    String[] names={"probe/r0","probe/r1","probe/r2","probe/r3","probe/r4","probe/r5","probe/r6","probe/r7","probe/r8"};
    for(int i=0;i<names.length;i++)require(urls.add(new URL(names[i])));
    Iterator<URL> it=urls.iterator();require(it.next()==one);
    Set<Object> direction=new LinkedHashSet<Object>(2);require(direction.add(new Old())&&!direction.add(new New())&&direction.size()==1);
    require(Thread.currentThread()==Thread.currentThread()&&Thread.currentThread().getContextClassLoader()==null);
    PrivilegedAction<String> a=new StringAction();require("resource-action".equals(a.run())&&"resource-action".equals(erased(a)));
    require(System.getSecurityManager()==null);Properties p=new Properties();p.setProperty("resource","indexed");
    Object[] src={loader,p.getProperty("resource")},dst=new Object[2];System.arraycopy(src,0,dst,0,2);require(dst[0]==loader&&"indexed".equals(dst[1]));
    new Target();require(seen==1);
    Class<?> named=Class.forName("ParentResourceEnumerationProbe$Target");
    require(named==loaded && named==Class.forName("ParentResourceEnumerationProbe$Target") && named.getClassLoader()==loader && seen==1);
    Class<?> namedBoot=Class.forName("java.lang.Boolean");
    require(namedBoot==boot && namedBoot==Class.forName("java.lang.Boolean") && namedBoot.getClassLoader()==null);
    done=997;
  }
}
