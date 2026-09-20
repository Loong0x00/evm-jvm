package java.lang;

/** Single guest current thread; no scheduler, host callback, or loader installation. */
public final class Thread {
    private static final Thread CURRENT = new Thread();
    private ClassLoader contextClassLoader;

    private Thread() { super(); }

    public static Thread currentThread() { return CURRENT; }

    public ClassLoader getContextClassLoader() { return contextClassLoader; }

    /** Bounded optional-caller-location surface: no guest frame snapshots are exposed. */
    public StackTraceElement[] getStackTrace() { return new StackTraceElement[0]; }
}
