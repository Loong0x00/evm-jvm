import java.security.PrivilegedAction;
import java.util.Properties;

/** Generated control for canonical raw-loader and system-loader identity. */
public final class SystemClassLoaderProbe {
  static int seen, done;
  public static final class Second { static { seen++; } }
  static final class StringAction implements PrivilegedAction<String> {
    public String run() { return "system-loader-action"; }
  }
  static void require(boolean ok) { if (!ok) { int z=0; int x=1/z; } }
  @SuppressWarnings("rawtypes") static Object erased(PrivilegedAction x) { return x.run(); }
  public static void main(String[] args) {
    ClassLoader a=SystemClassLoaderProbe.class.getClassLoader();
    ClassLoader b=Second.class.getClassLoader();
    ClassLoader system1=ClassLoader.getSystemClassLoader();
    ClassLoader system2=ClassLoader.getSystemClassLoader();
    require(a!=null && a==b && a==system1 && system1==system2 && seen==0);
    require(ClassLoader.class.getClassLoader()==null && Class.class.getClassLoader()==null);
    require(Thread.currentThread()==Thread.currentThread());
    require(Thread.currentThread().getContextClassLoader()==null);
    PrivilegedAction<String> action=new StringAction();
    require("system-loader-action".equals(action.run()) && "system-loader-action".equals(erased(action)));
    require(System.getSecurityManager()==null);
    Properties p=new Properties();p.setProperty("loader","defined");
    Object[] src={system1,p.getProperty("loader")},dst=new Object[2];System.arraycopy(src,0,dst,0,2);
    require(dst[0]==system1 && "defined".equals(dst[1]));
    new Second(); require(seen==1); done=631;
  }
}
