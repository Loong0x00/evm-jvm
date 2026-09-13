/** Host-only generated observation: identity is portable; loader installation is host-specific. */
public final class ThreadHostOracle {
    public static void main(String[] ignored) {
        Thread a = Thread.currentThread();
        if (a != Thread.currentThread()) throw new AssertionError("identity");
        System.out.println(a.getContextClassLoader() == null ? "host-null" : "host-installed-loader");
    }
}
