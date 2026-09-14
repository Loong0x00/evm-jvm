public final class OmittedLoadClassOverloadProbe extends ClassLoader {
    static final class Nested {}
    public static void main(String[] x) throws Exception {
        Class<?> literal = Nested.class;
        new OmittedLoadClassOverloadProbe().loadClass("OmittedLoadClassOverloadProbe$Nested", false);
    }
}
