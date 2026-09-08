package bundle.m5da.rootinit;

class RootFailedDependency { static int value = fail(); static int fail() { return 1 / 0; } }
/** A known NCDFE escaping root initialization is reported, not caught by run. */
public final class RootNoClassDef {
    static int value = initialize();
    static int initialize() {
        try { return RootFailedDependency.value; }
        catch (ExceptionInInitializerError e) { }
        return RootFailedDependency.value;
    }
    public static int run(int seed) {
        try { return value + seed; }
        catch (NoClassDefFoundError e) { return -1; }
    }
}
