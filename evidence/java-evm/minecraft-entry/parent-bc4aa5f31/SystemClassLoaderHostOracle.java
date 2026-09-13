/** Generated Java8 TEST oracle for portable system/defining loader identity. */
public final class SystemClassLoaderHostOracle {
  static final class B {}
  public static void main(String[] x) {
    ClassLoader s=ClassLoader.getSystemClassLoader();
    if(s==null || s!=SystemClassLoaderHostOracle.class.getClassLoader() || s!=B.class.getClassLoader()) throw new AssertionError();
    if(ClassLoader.class.getClassLoader()!=null || Class.class.getClassLoader()!=null) throw new AssertionError();
  }
}
