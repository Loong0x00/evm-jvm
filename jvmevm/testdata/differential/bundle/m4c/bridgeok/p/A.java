package bundle.m4c.bridgeok.p;

/** Package-private declaration and its original symbolic call site. */
public class A {
    int slot(int value) { return value + 1; }

    public static int call(A receiver, int value) {
        return receiver.slot(value);
    }
}
