package bundle.m5da.rootinit;

class RootBadSuper { static int value = fail(); static int fail() { return 1 / 0; } }
/** Superclass initialization fails before this root method is entered. */
public final class RootSuper extends RootBadSuper {
    public static int run(int seed) {
        try { return value + seed; }
        catch (Throwable e) { return -1; }
    }
}
