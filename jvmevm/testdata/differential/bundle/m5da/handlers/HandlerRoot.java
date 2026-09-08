package bundle.m5da.handlers;

/** Ordered handlers, catch-all cleanup, precise ranges, and stack/local restoration. */
public final class HandlerRoot {
    private static int trace;

    private static int arithmetic() { return 1 / 0; }
    private static int nullFault() { int[] value = null; return value.length; }

    public static int orderedExactFirst(int seed) {
        try { return arithmetic(); }
        catch (ArithmeticException e) { return seed + 201; }
        catch (RuntimeException e) { return -1; }
    }
    public static int orderedSuperFallback(int seed) {
        try { return nullFault(); }
        catch (ArithmeticException e) { return -1; }
        catch (RuntimeException e) { return seed + 202; }
    }
    public static int orderedThrowableFallback(int seed) {
        try { return nullFault(); }
        catch (ArithmeticException e) { return -1; }
        catch (Throwable e) { return seed + 203; }
    }
    public static int multiArithmetic(int seed) {
        try { return arithmetic(); }
        catch (ArithmeticException | NullPointerException e) { return seed + 204; }
    }
    public static int multiNull(int seed) {
        try { return nullFault(); }
        catch (ArithmeticException | NullPointerException e) { return seed + 205; }
    }
    public static int nestedInner(int seed) {
        try {
            try { return arithmetic(); }
            catch (ArithmeticException e) { return seed + 206; }
        } catch (Throwable e) { return -1; }
    }
    public static int nestedOuter(int seed) {
        try {
            try { return nullFault(); }
            catch (ArithmeticException e) { return -1; }
        } catch (NullPointerException e) { return seed + 207; }
    }
    public static int rethrowOuter(int seed) {
        try {
            try { return arithmetic(); }
            catch (ArithmeticException e) { throw e; }
        } catch (RuntimeException e) { return seed + 208; }
    }
    public static int finallyOnReturn(int seed) {
        trace = 0;
        try { trace = 2; return seed + 209; }
        finally { trace = trace * 10 + 3; }
    }
    public static int finallyRethrow(int seed) {
        trace = 0;
        try {
            try { trace = 2; return arithmetic(); }
            finally { trace = trace * 10 + 3; }
        } catch (ArithmeticException e) { return trace * 100 + seed; }
    }
    public static int finallyNestedFault(int seed) {
        trace = 0;
        try {
            try { return arithmetic(); }
            finally { trace = 211; }
        } catch (Throwable e) { return trace + seed; }
    }
    public static int catchAllViaFinally(int seed) {
        trace = 0;
        try {
            try { return nullFault(); }
            finally { trace = 212; }
        } catch (NullPointerException e) { return trace + seed; }
    }
    public static int handlerEndExclusive(int seed) {
        try {
            try { return arithmetic(); }
            catch (ArithmeticException e) { throw e; }
        } catch (ArithmeticException e) { return seed + 213; }
    }
    public static int handlerStartInclusive(int seed) {
        try { return arithmetic(); }
        catch (ArithmeticException e) { return seed + 214; }
    }
    public static int operandPrefixCleared(int seed) {
        try { return seed + 7 + arithmetic(); }
        catch (ArithmeticException e) { return seed + 215; }
    }
    public static int deepOperandPrefixCleared(int seed) {
        try { return (seed * 3) + (seed + arithmetic()) + 9; }
        catch (Throwable e) { return seed + 216; }
    }
    public static int categoryLocals(int seed) {
        int i = seed + 7;
        long j = 0x100000002L;
        float f = 7.5f;
        double d = -3.25d;
        try { return i + arithmetic(); }
        catch (ArithmeticException e) { return i + (int) j + (int) (j >>> 32) + (int) f + (int) d + 217; }
    }
    public static int localsRemainMutable(int seed) {
        int before = seed + 1;
        int after = seed + 2;
        try { before += arithmetic(); }
        catch (ArithmeticException e) { after += 218; }
        return before * 10 + after;
    }
    public static int sideEffectsBeforeFault(int seed) {
        trace = seed;
        try { trace = trace * 10 + 1; return trace + arithmetic(); }
        catch (ArithmeticException e) { return trace; }
    }
    public static int handlerCanFault(int seed) {
        try { return arithmetic(); }
        catch (ArithmeticException e) { return nullFault(); }
    }
    public static int outerCatchesHandlerFault(int seed) {
        try {
            try { return arithmetic(); }
            catch (ArithmeticException e) { return nullFault(); }
        } catch (NullPointerException e) { return seed + 220; }
    }
    public static int duplicateSites(int mode) {
        try {
            if (mode == 0) return arithmetic();
            return nullFault();
        } catch (ArithmeticException e) { return 221; }
          catch (NullPointerException e) { return 222; }
    }
}
