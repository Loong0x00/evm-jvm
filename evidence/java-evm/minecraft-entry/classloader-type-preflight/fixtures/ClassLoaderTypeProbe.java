/** Generated Java 8 ClassLoader type/linkage control. */
public final class ClassLoaderTypeProbe {
    private static final class MinimalLoader extends ClassLoader {
        protected MinimalLoader() { super(); }
    }

    private static void fail() {
        int[] zero = new int[1];
        int ignored = 1 / zero[0];
    }

    public static void main(String[] ignored) {
        ClassLoader loader = new MinimalLoader();
        ClassLoader[] loaders = new ClassLoader[] { loader, null };
        Object boxed = loaders;
        ClassLoader[] cast = (ClassLoader[]) boxed;
        String type = ClassLoader.class.getName();
        if (cast.length != 2 || cast[0] != loader || cast[1] != null
                || !"java.lang.ClassLoader".equals(type)) {
            fail();
        }
    }
}
