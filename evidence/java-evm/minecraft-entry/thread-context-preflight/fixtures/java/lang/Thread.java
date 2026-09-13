package java.lang;
/** Caller replacement payload: the engine must reject this class before use. */
public final class Thread {
    private static final Thread CURRENT = new Thread();
    private ClassLoader contextClassLoader;
    private Thread() { super(); }
    public static Thread currentThread() { return CURRENT; }
    public ClassLoader getContextClassLoader() { return contextClassLoader; }
}
