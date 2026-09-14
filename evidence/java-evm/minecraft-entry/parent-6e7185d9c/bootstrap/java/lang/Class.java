package java.lang;
public final class Class<T> {
    private String name;
    private ClassLoader definingLoader;
    private Class() { super(); }
    public String getName() { return name; }
    public ClassLoader getClassLoader() { return definingLoader; }
    public static Class<?> forName(String className) throws ClassNotFoundException {
        return forName0(className);
    }
    private static native Class<?> forName0(String className);
}
