public final class LoadClassProbe {
    static int done;
    static final class Nested {
        static { done = 91; }
    }
    public static void main(String[] ignored) throws Exception {
        Class<?> literal = Nested.class;
        ClassLoader loader = ClassLoader.getSystemClassLoader();
        Class<?> one = loader.loadClass("LoadClassProbe$Nested");
        Class<?> two = loader.loadClass("LoadClassProbe$Nested");
        if (one != two || one != literal || one.getClassLoader() != loader || done != 0) throw new AssertionError();
        Class<?> bool = loader.loadClass("java.lang.Boolean");
        if (bool.getClassLoader() != null || bool != Boolean.class) throw new AssertionError();
        done = 733;
    }
}
