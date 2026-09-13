import java.net.URL;import java.util.Enumeration;
/** Java8 TEST oracle for one classpath resource and loader identity. */
public final class ParentResourceEnumerationHostOracle {
 public static void main(String[] x)throws Exception{
  ClassLoader l=ParentResourceEnumerationHostOracle.class.getClassLoader();if(l==null||l!=ClassLoader.getSystemClassLoader())throw new AssertionError();
  Enumeration<URL> e=l.getResources("probe/resource.txt");if(!e.hasMoreElements())throw new AssertionError();URL a=e.nextElement();if(e.hasMoreElements())throw new AssertionError();
  Enumeration<URL> f=l.getResources("probe/resource.txt");if(!f.hasMoreElements()||!a.equals(f.nextElement()))throw new AssertionError();
  if(l.getResources("probe/missing.txt").hasMoreElements())throw new AssertionError();
 }
}
