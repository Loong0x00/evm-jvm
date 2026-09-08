package bundle.m5da.types;

/** User Throwable subtypes are catch types only; no user Throwable is constructed. */
public final class UserCatchRoot {
    private static int fail() { return 1 / 0; }
    private static int declaredUserThrowable() throws UserThrowable { return fail(); }

    public static int userArithmeticSkipped(int seed) {
        try { return fail(); }
        catch (UserArithmetic e) { return -1; }
        catch (ArithmeticException e) { return seed + 701; }
    }
    public static int userRuntimeSkipped(int seed) {
        try { return fail(); }
        catch (UserRuntime e) { return -1; }
        catch (RuntimeException e) { return seed + 702; }
    }
    public static int userErrorSkipped(int seed) {
        try { return UserFailing.value; }
        catch (UserError e) { return -1; }
        catch (Error e) { return seed + 703; }
    }
    public static int userThrowableSkipped(int seed) {
        try { return declaredUserThrowable(); }
        catch (UserThrowable e) { return -1; }
        catch (Throwable e) { return seed + 704; }
    }
}
class UserArithmetic extends ArithmeticException { }
class UserRuntime extends RuntimeException { }
class UserError extends Error { }
class UserThrowable extends Throwable { }
class UserFailing { static int value = 1 / 0; }
