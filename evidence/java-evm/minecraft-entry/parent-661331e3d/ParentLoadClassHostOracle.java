/** Java8 TEST oracle for load-without-initialize and defining loader identity. */
public final class ParentLoadClassHostOracle {
 static int seen; static final class T{static{seen++;}}
 public static void main(String[] x)throws Exception{ClassLoader l=ParentLoadClassHostOracle.class.getClassLoader();if(l==null||l!=ClassLoader.getSystemClassLoader())throw new AssertionError();Class<?> c=l.loadClass("ParentLoadClassHostOracle$T");if(c!=T.class||seen!=0||c.getClassLoader()!=l)throw new AssertionError();new T();if(seen!=1)throw new AssertionError();if(l.loadClass("java.lang.Boolean")!=Boolean.class||Boolean.class.getClassLoader()!=null)throw new AssertionError();}
}
