package java.lang;

import java.util.Properties;

/**
 * Bounded Java 8 System surface for this local guest launch profile.
 * Properties begin empty: no host or -D property channel is present.
 */
public final class System {
    private static SecurityManager security;
    private static Properties properties = new Properties();

    private System() {}

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    public static SecurityManager getSecurityManager() {
        return security;
    }

    public static String getProperty(String key) {
        if (key.length() == 0) throw new IllegalArgumentException();
        return properties.getProperty(key);
    }
}
