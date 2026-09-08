package bundle.m5da.init;

/** Initialization continuations, caught failures, erroneous state, and prerequisites. */
public final class InitRoot {
    public static int insideArithmetic(int seed) { return InsideArithmetic.value + seed; }
    public static int insideNull(int seed) { return InsideNull.value + seed; }

    public static int selfFirstSecond(int seed) {
        int result = 0;
        try { result += BadSelf.value; } catch (ExceptionInInitializerError e) { result += 601; }
        try { result += BadSelf.value; } catch (NoClassDefFoundError e) { result += 602; }
        return result + seed;
    }
    public static int selfCatchLinkage(int seed) {
        try { return BadSelf.value; } catch (LinkageError e) { return seed + 603; }
    }
    public static int selfCatchError(int seed) {
        try { return BadSelf.value; } catch (Error e) { return seed + 604; }
    }
    public static int selfCatchThrowable(int seed) {
        try { return BadSelf.value; } catch (Throwable e) { return seed + 605; }
    }
    public static int uncaughtSelf(int seed) { return BadSelf.value + seed; }
    public static int uncaughtSecondSelf(int seed) {
        try { return BadSelf.value; } catch (ExceptionInInitializerError e) { }
        return BadSelf.value + seed;
    }

    public static int failedGetSecond(int seed) {
        try { int ignored = FailedUses.field; } catch (ExceptionInInitializerError e) { }
        try { return FailedUses.field; } catch (NoClassDefFoundError e) { return seed + 608; }
    }
    public static int failedPutSecond(int seed) {
        try { FailedUses.field = seed; } catch (ExceptionInInitializerError e) { }
        try { FailedUses.field = seed + 1; return -1; } catch (NoClassDefFoundError e) { return seed + 609; }
    }
    public static int failedInvokeSecond(int seed) {
        try { return FailedUses.call(); } catch (ExceptionInInitializerError e) { }
        try { return FailedUses.call(); } catch (NoClassDefFoundError e) { return seed + 610; }
    }
    public static int failedNewSecond(int seed) {
        try { return new FailedUses().field; } catch (ExceptionInInitializerError e) { }
        try { new FailedUses(); return -1; } catch (NoClassDefFoundError e) { return seed + 611; }
    }
    public static int ncdfeLinkage(int seed) {
        try { int ignored = FailedUses.field; } catch (ExceptionInInitializerError e) { }
        try { return FailedUses.field; } catch (LinkageError e) { return seed + 612; }
    }
    public static int ncdfeError(int seed) {
        try { int ignored = FailedUses.field; } catch (ExceptionInInitializerError e) { }
        try { return FailedUses.field; } catch (Error e) { return seed + 613; }
    }
    public static int ncdfeThrowable(int seed) {
        try { int ignored = FailedUses.field; } catch (ExceptionInInitializerError e) { }
        try { return FailedUses.field; } catch (Throwable e) { return seed + 614; }
    }

    public static int activeCatchCompletes(int seed) { return ActiveCatch.value + seed; }
    public static int activeCatchDependencyLater(int seed) {
        int result = ActiveCatch.value;
        try { result += ActiveDependency.value; }
        catch (NoClassDefFoundError e) { result += 616; }
        return result + seed;
    }
    public static int dependentErrorUnwrapped(int seed) {
        try { return ErrorDependent.value; }
        catch (ExceptionInInitializerError e) { return e == ErrorHolder.value ? seed + 617 : -1; }
    }
    public static int dependentFirstSecond(int seed) {
        int result = 0;
        try { result += ErrorDependent.value; } catch (Error e) { result += 618; }
        try { result += ErrorDependent.value; } catch (NoClassDefFoundError e) { result += 619; }
        return result + seed;
    }

    public static int reentryPrepared(int seed) { return ReentryA.before + seed; }
    public static int reentryCompleted(int seed) { return ReentryA.after + seed; }

    public static int superFirstSecond(int seed) {
        int result = 0;
        try { result += BadSub.value; } catch (ExceptionInInitializerError e) { result += 622; }
        try { result += BadSub.value; } catch (NoClassDefFoundError e) { result += 623; }
        return result + seed;
    }
    public static int defaultFirstSecond(int seed) {
        int result = 0;
        try { result += BadDefaultImpl.value; } catch (ExceptionInInitializerError e) { result += 624; }
        try { result += BadDefaultImpl.value; } catch (NoClassDefFoundError e) { result += 625; }
        return result + seed;
    }
    public static int unusedFailureNotEntered(int seed) { return Unrelated.value + seed; }
    public static int caughtThenContinue(int seed) { return ContinueAfterCatch.value + seed; }
}

final class InitFaults {
    static int arithmetic() { return 1 / 0; }
    static int nullFault() { int[] value = null; return value.length; }
}
final class InsideArithmetic {
    static int value;
    static { try { value = InitFaults.arithmetic(); } catch (ArithmeticException e) { value = 6010; } }
}
final class InsideNull {
    static int value;
    static { try { value = InitFaults.nullFault(); } catch (NullPointerException e) { value = 6020; } }
}
final class BadSelf { static int value = InitFaults.arithmetic(); }
final class FailedUses {
    static int field = InitFaults.arithmetic();
    static int call() { return field; }
}
final class ActiveDependency { static int value = InitFaults.arithmetic(); }
final class ActiveCatch {
    static int value;
    static {
        try { value = ActiveDependency.value; }
        catch (ExceptionInInitializerError e) { value = 615; }
    }
}
final class ErrorOrigin { static int value = InitFaults.arithmetic(); }
final class ErrorHolder { static Throwable value; }
final class ErrorDependent {
    static int value = initialize();
    static int initialize() {
        try { return ErrorOrigin.value; }
        catch (ExceptionInInitializerError e) { ErrorHolder.value = e; throw e; }
    }
}
final class ReentryA {
    static int before = ReentryB.read();
    static int after = 621;
}
final class ReentryB { static int read() { return ReentryA.after; } }
class BadSuper { static int broken = InitFaults.arithmetic(); }
final class BadSub extends BadSuper { static int value = 1; }
interface BadDefault {
    int BROKEN = InitFaults.arithmetic();
    default int value() { return 1; }
}
final class BadDefaultImpl implements BadDefault { static int value = 1; }
final class NeverUsedFailure { static int value = InitFaults.arithmetic(); }
final class Unrelated { static int value = 626; }
final class ContinueAfterCatch {
    static int value;
    static {
        try { value = InitFaults.nullFault(); }
        catch (RuntimeException e) { value = 627; }
        value += 1;
    }
}
