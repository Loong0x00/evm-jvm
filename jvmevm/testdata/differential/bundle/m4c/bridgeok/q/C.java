package bundle.m4c.bridgeok.q;

import bundle.m4c.bridgeok.p.A;
import bundle.m4c.bridgeok.p.B;

/** q.C continues the real override chain A(package) -> B(public) -> C. */
public class C extends B {
    public int slot(int value) { return value + 300; }

    public static int bridgeSelectsB(int value) {
        return A.call(new B(), value);
    }

    public static int bridgeSelectsC(int value) {
        return A.call(new C(), value);
    }

    public static int bridgeAlternates(int value) {
        return A.call(new B(), value) * 1000 + A.call(new C(), value);
    }
}
