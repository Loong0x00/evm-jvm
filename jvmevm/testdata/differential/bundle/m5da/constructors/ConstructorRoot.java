package bundle.m5da.constructors;

/** Constructor abrupt completion is caught by callers; post-super handlers are ordinary. */
public final class ConstructorRoot {
    private static int divide() { return 1 / 0; }

    public static int callerCatchesBody(int seed) {
        try { return new BodyFailure(seed).value; }
        catch (ArithmeticException e) { return seed + 501; }
    }
    public static int callerCatchesArgument(int seed) {
        try { return new ArgumentFailure(seed).value; }
        catch (ArithmeticException e) { return seed + 502; }
    }
    public static int callerCatchesSuperArgument(int seed) {
        try { return new SuperArgumentFailure(seed).value; }
        catch (ArithmeticException e) { return seed + 503; }
    }
    public static int callerCatchesSuperBody(int seed) {
        try { return new SuperBodyChild(seed).value; }
        catch (NullPointerException e) { return seed + 504; }
    }
    public static int callerCatchesThisChain(int seed) {
        try { return new ThisChainFailure(seed).value; }
        catch (ArithmeticException e) { return seed + 505; }
    }
    public static int postsuperCatchArithmetic(int seed) {
        return new PostSuperCatch(seed).value;
    }
    public static int postsuperCatchNull(int seed) {
        return new PostSuperNullCatch(seed).value;
    }
    public static int postsuperFinallyCatch(int seed) {
        return new PostSuperFinally(seed).value;
    }
    public static int failedThenFresh(int seed) {
        int caught = 0;
        try { new BodyFailure(seed); } catch (ArithmeticException e) { caught = 1; }
        return new GoodAfterFailure(seed).value + caught * 100;
    }
    public static int aliasNotPublished(int seed) {
        Holder.value = null;
        try { Holder.value = new BodyFailure(seed); } catch (ArithmeticException e) { }
        return Holder.value == null ? seed + 510 : -1;
    }
    public static int helperBeforeSuperNormal(int seed) {
        return new HelperBeforeSuper(seed).value;
    }
    public static int nestedAllocationFailure(int seed) {
        try { return new OuterAllocation(seed).value; }
        catch (ArithmeticException e) { return seed + 512; }
    }

    static int fail() { return divide(); }
}

class BodyFailure {
    int value;
    BodyFailure(int seed) { value = seed; value += ConstructorRoot.fail(); }
}
class ArgumentFailure {
    int value;
    ArgumentFailure(int seed) { this(seed, ConstructorRoot.fail()); }
    ArgumentFailure(int seed, int other) { value = seed + other; }
}
class SuperValue {
    int value;
    SuperValue(int value) { this.value = value; }
}
class SuperArgumentFailure extends SuperValue {
    SuperArgumentFailure(int seed) { super(seed + ConstructorRoot.fail()); }
}
class SuperNullBody {
    int value;
    SuperNullBody(int seed) { int[] missing = null; value = missing.length + seed; }
}
class SuperBodyChild extends SuperNullBody {
    SuperBodyChild(int seed) { super(seed); }
}
class ThisChainFailure {
    int value;
    ThisChainFailure(int seed) { this(seed, 1); }
    ThisChainFailure(int seed, int ignored) { value = seed + ConstructorRoot.fail(); }
}
class PostSuperCatch extends SuperValue {
    PostSuperCatch(int seed) {
        super(seed);
        try { value += ConstructorRoot.fail(); }
        catch (ArithmeticException e) { value += 506; }
    }
}
class PostSuperNullCatch extends SuperValue {
    PostSuperNullCatch(int seed) {
        super(seed);
        try { int[] missing = null; value += missing.length; }
        catch (NullPointerException e) { value += 507; }
    }
}
class PostSuperFinally extends SuperValue {
    PostSuperFinally(int seed) {
        super(seed);
        try {
            try { value += ConstructorRoot.fail(); }
            finally { value += 508; }
        } catch (ArithmeticException e) { value += 1; }
    }
}
class GoodAfterFailure { int value; GoodAfterFailure(int seed) { value = seed + 509; } }
class Holder { static BodyFailure value; }
class HelperBeforeSuper extends SuperValue {
    HelperBeforeSuper(int seed) { super(normal(seed)); }
    private static int normal(int seed) { return seed + 511; }
}
class OuterAllocation {
    int value;
    OuterAllocation(int seed) { value = new BodyFailure(seed).value; }
}
