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
  static int done;
  static final class Old { public int hashCode(){return 11;} public boolean equals(Object o){return false;} }
  static final class New { public int hashCode(){return 11;} public boolean equals(Object o){return o instanceof Old;} }
  static final class StringAction implements PrivilegedAction<String> { public String run(){return "resource-action";} }
  static void require(boolean x){if(!x){int z=0;int y=1/z;}}
  @SuppressWarnings("rawtypes") static Object erased(PrivilegedAction x){return x.run();}
  public static void main(String[] ignored) throws Exception {
    ClassLoader loader=ParentResourceEnumerationProbe.class.getClassLoader();
    require(loader!=null && loader==Old.class.getClassLoader() && loader==ClassLoader.getSystemClassLoader());
    require(ClassLoader.class.getClassLoader()==null && Class.class.getClassLoader()==null);
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
    done=947;
  }
}
