package bundle.m4c.bridgeok.p;

/** Public bridge that genuinely overrides A's package-private slot. */
public class B extends A {
    public int slot(int value) { return value + 20; }
}
