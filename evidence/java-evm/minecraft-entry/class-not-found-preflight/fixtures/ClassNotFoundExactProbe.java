public final class ClassNotFoundExactProbe {
    static int seen;
    static final class Target { static { ClassNotFoundExactProbe.seen++; } }
    public static void main(String[] args) {
        ClassLoader loader = ClassNotFoundExactProbe.class.getClassLoader();
        try {
            Class<?> first = loader.loadClass("ClassNotFoundExactProbe$Target");
            Class<?> second = loader.loadClass("ClassNotFoundExactProbe$Target");
            if (first != second || first != Target.class || seen != 0) throw new Error();
        } catch (ClassNotFoundException unexpected) { throw new Error(); }
        try { loader.loadClass("missing.optional.Probe"); throw new Error(); }
        catch (ClassNotFoundException expected) { }
    }
}
