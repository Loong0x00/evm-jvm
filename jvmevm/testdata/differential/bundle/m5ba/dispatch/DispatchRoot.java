package bundle.m5ba.dispatch;

/** Long arguments/results across static, special, virtual, interface, default, and constructor calls. */
public class DispatchRoot {
    private static int fold(long value) { return (int) (value ^ (value >>> 32)); }
    private static long make(int value) { return ((long) value << 32) | ((long) ~value & 0xffffffffL); }

    private static long staticLong(long value) { return value + 0x100000001L; }
    private static long staticMixed(int first, long wide, DispatchBox box, int last) {
        return wide + first * 3L + box.value + last * 5L;
    }
    private long privateSpecial(long value, int add) { return value ^ ((long) add << 40); }

    public static int staticCall(int value) { return fold(staticLong(make(value))); }
    public static int staticMixedCall(int value) {
        return fold(staticMixed(value + 1, make(value), new DispatchBox(value + 2), value + 3));
    }
    public static int privateSpecialCall(int value) {
        return fold(new DispatchRoot().privateSpecial(make(value), value + 7));
    }

    private static long virtualSite(DispatchBase receiver, long wide, int add, DispatchBox box) {
        return receiver.apply(wide, add, box);
    }
    private static long interfaceSite(DispatchFace receiver, long wide, int add, DispatchBox box) {
        return receiver.apply(wide, add, box);
    }
    private static long defaultSite(DispatchFace receiver, long wide, int add) {
        return receiver.defaultValue(wide, add);
    }

    public static int virtualBase(int value) {
        return fold(virtualSite(new DispatchBase(), make(value), value + 1, new DispatchBox(value + 2)));
    }
    public static int virtualOverride(int value) {
        return fold(virtualSite(new DispatchChild(), make(value), value + 1, new DispatchBox(value + 2)));
    }
    public static int interfaceBase(int value) {
        return fold(interfaceSite(new DispatchBase(), make(value), value + 1, new DispatchBox(value + 2)));
    }
    public static int interfaceOverride(int value) {
        return fold(interfaceSite(new DispatchChild(), make(value), value + 1, new DispatchBox(value + 2)));
    }
    public static int defaultCall(int value) { return fold(new DispatchBase().defaultValue(make(value), value)); }
    public static int interfaceDefaultCall(int value) {
        return fold(defaultSite(new DispatchBase(), make(value), value + 4));
    }
    public static int directInterfaceSuper(int value) { return fold(new DispatchBase().directDefault(make(value), value)); }
    public static int interfaceStatic(int value) { return fold(DispatchFace.staticValue(make(value), value + 5)); }

    public static int constructorArguments(int value) {
        DispatchConstructed made = new DispatchConstructed(make(value), value + 1, new DispatchBox(value + 2));
        return fold(made.value);
    }
    public static int constructorChain(int value) {
        DispatchConstructedChild made = new DispatchConstructedChild(value, make(value));
        return fold(made.value) ^ fold(made.own);
    }
    public static int longReturnTransport(int value) {
        long first = staticLong(make(value));
        long second = virtualSite(new DispatchChild(), first, value, new DispatchBox(3));
        long third = interfaceSite(new DispatchBase(), second, value + 1, new DispatchBox(4));
        return fold(third);
    }
    public static int alternatingDispatch(int value) {
        DispatchBase receiver = new DispatchBase();
        long total = virtualSite(receiver, make(value), 1, new DispatchBox(2));
        receiver = new DispatchChild();
        total += virtualSite(receiver, make(value + 1), 3, new DispatchBox(4));
        receiver = new DispatchBase();
        total ^= virtualSite(receiver, make(value + 2), 5, new DispatchBox(6));
        return fold(total);
    }
}

interface DispatchFace {
    long apply(long wide, int add, DispatchBox box);
    default long defaultValue(long wide, int add) { return wide + add * 11L; }
    static long staticValue(long wide, int add) { return wide ^ ((long) add << 36); }
}
class DispatchBase implements DispatchFace {
    public long apply(long wide, int add, DispatchBox box) { return wide + add + box.value; }
    long directDefault(long wide, int add) { return DispatchFace.super.defaultValue(wide, add); }
}
class DispatchChild extends DispatchBase {
    public long apply(long wide, int add, DispatchBox box) { return wide - add - box.value; }
}
class DispatchBox { int value; DispatchBox(int value) { this.value = value; } }
class DispatchConstructed {
    long value;
    DispatchConstructed(long wide, int add, DispatchBox box) { value = wide + add + box.value; }
}
class DispatchConstructedChild extends DispatchConstructed {
    long own;
    DispatchConstructedChild(int value, long wide) { this(wide, new DispatchBox(value + 3), value + 2); }
    DispatchConstructedChild(long wide, DispatchBox box, int add) { super(wide, add, box); own = wide ^ add; }
}
