/** setContextClassLoader is deliberately absent from the narrow profile. */
public final class ThreadUnsupportedSetter {
    public static void main(String[] ignored) { Thread.currentThread().setContextClassLoader(null); }
}
