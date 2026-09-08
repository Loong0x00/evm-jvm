package bundle.m5da.rootinit;

interface RootBadDefault {
    int VALUE = fail();
    static int fail() { return 1 / 0; }
    default int value() { return VALUE; }
}
/** Default-declaring interface initialization fails before root entry. */
public final class RootDefault implements RootBadDefault {
    public static int run(int seed) {
        try { return seed; }
        catch (Throwable e) { return -1; }
    }
}
