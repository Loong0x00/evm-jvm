package java.lang;
/** Minimal immutable mirror shell with VM-owned defining-loader identity. */
public final class Class<T> {
    private String name;
    private ClassLoader definingLoader;
    private Class() {}
    public String getName() { return name; }
    public ClassLoader getClassLoader() { return definingLoader; }
}
