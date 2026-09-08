package bundle.m5ba.init;

/** Long-valued class/interface initialization ordering, prepared defaults, cycles, and replay. */
public class InitRoot {
    private static int fold(long value) { return (int) (value ^ (value >>> 32)); }

    public static int classOrder(int value) {
        OrderChild made = new OrderChild();
        return InitState.trace * 1000 + fold(OrderParent.VALUE) + fold(OrderChild.VALUE) + fold(made.defaultValue(value));
    }
    public static int repeatedUse(int value) {
        long first = OnceLong.VALUE;
        long second = OnceLong.VALUE;
        return InitState.trace * 1000 + fold(first) + fold(second) + value;
    }
    public static int reentrantPreparedDefault(int value) {
        return fold(ReentrantLong.VALUE) * 31 + fold(ReentrantLong.OBSERVED) + InitState.trace * 1000 + value;
    }
    public static int cycleAFirst(int value) {
        return fold(CycleA.VALUE) * 31 + fold(CycleB.VALUE) + InitState.trace * 1000 + value;
    }
    public static int cycleBFirst(int value) {
        return fold(CycleB.VALUE) * 31 + fold(CycleA.VALUE) + InitState.trace * 1000 + value;
    }
    public static int interfaceOwnSkipsParent(int value) {
        return fold(ActiveChild.OWN) + InitState.trace * 1000 + value;
    }
    public static int inheritedInterfaceOwner(int value) {
        return fold(ActiveChild.PARENT) + InitState.trace * 1000 + value;
    }
    public static int pendingLongPrefix(int value) {
        return fold((0x1234567887654321L ^ (long) value) + PrefixOwner.VALUE)
            + InitState.trace * 1000;
    }
}

class InitState {
    static int trace;
    static long mark(int digit, long value) { trace = trace * 10 + digit; return value; }
}
class OrderParent { static long VALUE = InitState.mark(1, 0x1111111100000001L); }
interface OrderDefault {
    long VALUE = InitState.mark(2, 0x2222222200000002L);
    default long defaultValue(int value) { return VALUE + value; }
}
class OrderChild extends OrderParent implements OrderDefault {
    static long VALUE = InitState.mark(3, 0x3333333300000003L);
}
class OnceLong { static long VALUE = InitState.mark(4, 0x4444444400000004L); }
class ReentrantLong {
    static long VALUE = initialize();
    static long OBSERVED;
    static long initialize() {
        InitState.trace = InitState.trace * 10 + 5;
        OBSERVED = VALUE;
        return 0x5555555500000005L;
    }
}
class CycleA { static long VALUE = InitState.mark(6, 0x6000000000000006L) + CycleB.VALUE; }
class CycleB { static long VALUE = InitState.mark(7, 0x7000000000000007L) + CycleA.VALUE; }
interface ActiveParent { long PARENT = InitState.mark(8, 0x0808080800000008L); }
interface ActiveChild extends ActiveParent { long OWN = InitState.mark(9, 0x0909090900000009L); }
class PrefixOwner { static long VALUE = InitState.mark(4, 0x7654321089abcdefL); }
