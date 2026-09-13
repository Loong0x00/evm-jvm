/** The system getter is real; resource enumeration remains intentionally absent. */
public final class LoaderResourcesUnsupported {
  public static void main(String[] ignored) throws Exception {
    ClassLoader loader=LoaderResourcesUnsupported.class.getClassLoader();
    if (loader==null) throw new AssertionError();
    loader.getResources("not-implemented");
  }
}
