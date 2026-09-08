package bundle.m4c.bridgegap.q;

import bundle.m4c.bridgegap.p.A;

/** C overrides B.slot, but neither declaration overrides A's original slot. */
public class C extends B {
    public int slot(int value) { return value + 500; }

    public static int gapKeepsAForB(int value) {
        return A.call(new B(), value);
    }

    public static int gapKeepsAForC(int value) {
        return A.call(new C(), value);
    }

    public static int directBSlot(int value) {
        B receiver = new C();
        return receiver.slot(value);
    }

    public static int gapAlternates(int value) {
        return A.call(new B(), value) * 1000 + A.call(new C(), value);
    }
}
