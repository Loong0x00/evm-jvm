package java.lang;
/** Minimal immutable mirror shell for the class-literal preflight only. */
public final class Class<T> {
    private String name;
    private Class() {}
    public String getName() { return name; }
}
