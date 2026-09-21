package java.lang;

import java.io.PrintStream;
import java.util.Properties;

/**
 * Bounded Java 8 System surface for the local guest launch profile.
 * No host or -D property channel is present.
 */
public final class System {
    private static SecurityManager security;
    private static Properties properties;
    public static final PrintStream err;
    public static final PrintStream out;

    private System() {}

    /** Stable LOCAL replay epoch; this is not a host, block, or wall clock. */
    public static long currentTimeMillis() {
        return 0L;
    }

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    /** The VM-owned err and out cells are the only native mutable System statics. */
    public static native void setErr(PrintStream stream);

    /** The native binding mutates only the canonical guest out cell. */
    public static native void setOut(PrintStream stream);

    public static SecurityManager getSecurityManager() {
        return security;
    }

    public static String getProperty(String key) {
        if (key.length() == 0) throw new IllegalArgumentException();
        return properties.getProperty(key);
    }

    static {
        properties = new Properties();
        properties.setProperty("java.version", "1.8");
        err = new PrintStream();
        out = new PrintStream();
    }
}
