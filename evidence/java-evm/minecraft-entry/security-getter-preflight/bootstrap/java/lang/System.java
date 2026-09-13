package java.lang;

/**
 * Minimal VM bootstrap System surface for the Java 8 default security state.
 * No setter is intentionally supplied: unsupported security APIs must link
 * honestly rather than pretending to install or bypass a manager.
 */
public final class System {
    private static SecurityManager security;

    private System() {}

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    public static SecurityManager getSecurityManager() {
        return security;
    }
}
