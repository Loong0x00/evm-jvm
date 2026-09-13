public final class DefiningLoaderProbe {
    public static final class Second {}
    private static void require(boolean okay) {
        if (!okay) { int zero = 0; int ignored = 1 / zero; }
    }
    public static void main(String[] args) {
        ClassLoader first = DefiningLoaderProbe.class.getClassLoader();
        ClassLoader second = Second.class.getClassLoader();
        require(first != null);
        require(first == second);
        require(first instanceof ClassLoader);
        require(ClassLoader.class.getClassLoader() == null);
        require(Class.class.getClassLoader() == null);
        require(DefiningLoaderProbe.class.getName().length() == 19);
        require(Second.class.getName().length() == 26);
    }
}
