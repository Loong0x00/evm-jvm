import java.security.PrivilegedAction;
import java.util.Properties;
/** Generated EVM control combining defining-loader identity with inherited controls. */
public final class ParentDefiningLoaderProbe {
  static int seen, done;
  public static final class Second { static { seen++; } }
  static final class StringAction implements PrivilegedAction<String> {
    public String run() { return "loader-action"; }
  }
  static void require(boolean ok) { if (!ok) { int z=0; int x=1/z; } }
  @SuppressWarnings("rawtypes") static Object erased(PrivilegedAction x) { return x.run(); }
  public static void main(String[] args) {
    ClassLoader a=ParentDefiningLoaderProbe.class.getClassLoader();
    ClassLoader b=Second.class.getClassLoader();
    ClassLoader c=StringAction.class.getClassLoader();
    require(a!=null && a==b && b==c && seen==0);
    require(ClassLoader.class.getClassLoader()==null && Class.class.getClassLoader()==null);
    require(Thread.currentThread()==Thread.currentThread());
    require(Thread.currentThread().getContextClassLoader()==null);
    PrivilegedAction<String> action=new StringAction();
    require("loader-action".equals(action.run()) && "loader-action".equals(erased(action)));
    require(System.getSecurityManager()==null);
    Properties p=new Properties();p.setProperty("loader","defined");
    Object[] src={a,p.getProperty("loader")},dst=new Object[2];System.arraycopy(src,0,dst,0,2);
    require(dst[0]==a && "defined".equals(dst[1]));
    new Second(); require(seen==1); done=527;
  }
}
