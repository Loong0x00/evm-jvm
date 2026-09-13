/** Generated Java8 TEST oracle for portable defining-loader/null-bootstrap identity. */
public final class ParentDefiningLoaderHostOracle {
  static final class B {}
  public static void main(String[] x) {
    ClassLoader a=ParentDefiningLoaderHostOracle.class.getClassLoader();
    if(a==null || a!=B.class.getClassLoader()) throw new AssertionError();
    if(ClassLoader.class.getClassLoader()!=null || Class.class.getClassLoader()!=null) throw new AssertionError();
  }
}
