package bundle.m5da.rootinit;

/** The root method's handler is ineligible until root initialization succeeds. */
public final class RootArithmetic {
    static int value = fail();
    static int fail() { return 1 / 0; }
    public static int run(int seed) {
        try { return value + seed; }
        catch (ExceptionInInitializerError e) { return -1; }
        catch (Throwable e) { return -2; }
    }
}
