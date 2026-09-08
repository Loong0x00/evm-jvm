package bundle.m4c.bridgegap.p;

/** Package-private slot whose subclasses cross a package without an override bridge. */
public class A {
    int slot(int value) { return value + 7; }

    public static int call(A receiver, int value) {
        return receiver.slot(value);
    }
}
