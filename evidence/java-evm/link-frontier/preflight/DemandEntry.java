// Generated Java 8 preflight fixture. MissingTarget is intentionally omitted from
// selected worlds. The declaration contributes a non-executed symbolic reference.
public final class DemandEntry {
    private static MissingTarget unused;
    public static int run(int mode) {
        if (mode == 0) return 41;
        if (mode == 1) return MissingTarget.staticValue();
        if (mode == 2) return new MissingTarget().value();
        Object value = null;
        return ((MissingTarget)value).value();
    }
}
