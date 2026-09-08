package bundle.m5da.calls;

/** Interframe unwind uses each invoke opcode's start PC and preserves exception identity. */
public final class CallRoot {
    private static int fail() { return 1 / 0; }
    private static void failVoid() { int ignored = 1 / 0; }
    private int privateFail() { return fail(); }

    public static int staticCall(int seed) {
        try { return fail(); } catch (ArithmeticException e) { return seed + 301; }
    }
    public static int staticVoidCall(int seed) {
        try { failVoid(); return -1; } catch (ArithmeticException e) { return seed + 302; }
    }
    public static int nestedStaticCall(int seed) {
        try { return CallHelper.staticMiddle(); } catch (ArithmeticException e) { return seed + 303; }
    }
    public static int virtualCall(int seed) {
        CallBase value = new CallChild();
        try { return value.virtualFail(); } catch (ArithmeticException e) { return seed + 304; }
    }
    public static int virtualInheritedCall(int seed) {
        CallBase value = new CallChild();
        try { return value.inheritedFail(); } catch (ArithmeticException e) { return seed + 305; }
    }
    public static int interfaceCall(int seed) {
        CallFace value = new CallChild();
        try { return value.interfaceFail(); } catch (ArithmeticException e) { return seed + 306; }
    }
    public static int interfaceDefaultCall(int seed) {
        CallFace value = new DefaultCall();
        try { return value.defaultFail(); } catch (ArithmeticException e) { return seed + 307; }
    }
    public static int interfaceSuperCall(int seed) {
        return new DirectDefault().directFail(seed);
    }
    public static int interfaceStaticCall(int seed) {
        try { return CallFace.staticFail(); } catch (ArithmeticException e) { return seed + 3080; }
    }
    public static int privateSpecialCall(int seed) {
        CallRoot value = new CallRoot();
        try { return value.privateFail(); } catch (ArithmeticException e) { return seed + 309; }
    }
    public static int constructorCall(int seed) {
        try { return new FailingCallCtor(seed).value; } catch (ArithmeticException e) { return seed + 310; }
    }
    public static int staticPrefix(int seed) {
        try { return seed * 10 + CallHelper.staticMiddle(); } catch (ArithmeticException e) { return seed + 311; }
    }
    public static int virtualPrefix(int seed) {
        CallBase value = new CallChild();
        try { return seed * 10 + value.virtualFail(); } catch (ArithmeticException e) { return seed + 312; }
    }
    public static int interfacePrefix(int seed) {
        CallFace value = new CallChild();
        try { return seed * 10 + value.interfaceFail(); } catch (ArithmeticException e) { return seed + 313; }
    }
    public static int privatePrefix(int seed) {
        CallRoot value = new CallRoot();
        try { return seed * 10 + value.privateFail(); } catch (ArithmeticException e) { return seed + 314; }
    }
    public static int constructorPrefix(int seed) {
        try { return seed * 10 + new FailingCallCtor(seed).value; } catch (ArithmeticException e) { return seed + 315; }
    }
    public static int identityStatic(int seed) {
        ArithmeticException first;
        try { fail(); return -1; } catch (ArithmeticException e) { first = e; }
        try { CallHelper.rethrow(first); return -2; } catch (Throwable e) { return e == first ? seed + 316 : -3; }
    }
    public static int identityVirtual(int seed) {
        ArithmeticException first;
        try { fail(); return -1; } catch (ArithmeticException e) { first = e; }
        ThrowableCarrier value = new ThrowableCarrier();
        try { value.virtualRethrow(first); return -2; } catch (Throwable e) { return e == first ? seed + 317 : -3; }
    }
    public static int identityInterface(int seed) {
        ArithmeticException first;
        try { fail(); return -1; } catch (ArithmeticException e) { first = e; }
        ThrowFace value = new ThrowableCarrier();
        try { value.interfaceRethrow(first); return -2; } catch (Throwable e) { return e == first ? seed + 318 : -3; }
    }
    public static int callOutsideRange(int seed) {
        try { return CallHelper.safe(seed); } catch (ArithmeticException e) { return -1; }
    }
    public static int calleeCatchesOwn(int seed) {
        return CallHelper.catchOwn(seed);
    }
}

interface CallFace {
    int interfaceFail();
    default int defaultFail() { return 1 / 0; }
    static int staticFail() { return 1 / 0; }
}
class CallBase {
    int virtualFail() { return 7; }
    int inheritedFail() { return 1 / 0; }
}
final class CallChild extends CallBase implements CallFace {
    public int virtualFail() { return 1 / 0; }
    public int interfaceFail() { return 1 / 0; }
}
final class DefaultCall implements CallFace {
    public int interfaceFail() { return 3; }
}
final class DirectDefault implements CallFace {
    public int interfaceFail() { return 4; }
    int directFail(int seed) {
        try { return CallFace.super.defaultFail(); }
        catch (ArithmeticException e) { return seed + 308; }
    }
}
final class FailingCallCtor {
    int value;
    FailingCallCtor(int seed) { value = seed + 1 / 0; }
}
class ThrowableCarrier implements ThrowFace {
    public void interfaceRethrow(Throwable value) throws Throwable { throw value; }
    void virtualRethrow(Throwable value) throws Throwable { throw value; }
}
interface ThrowFace { void interfaceRethrow(Throwable value) throws Throwable; }
final class CallHelper {
    static int staticMiddle() { return 1 / 0; }
    static int safe(int seed) { return seed + 319; }
    static int catchOwn(int seed) {
        try { return staticMiddle(); } catch (ArithmeticException e) { return seed + 320; }
    }
    static void rethrow(Throwable value) throws Throwable { throw value; }
}
