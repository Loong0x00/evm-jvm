package bundle.m4c.bridgegap.q;

import bundle.m4c.bridgegap.p.A;

/** Same signature does not override inaccessible A.slot across this package gap. */
public class B extends A {
    public int slot(int value) { return value + 40; }
}
