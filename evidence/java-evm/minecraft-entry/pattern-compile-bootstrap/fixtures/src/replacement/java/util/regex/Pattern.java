package java.util.regex;

/** Compile-only raw-name replacement probe; never executed on the host. */
public final class Pattern {
    public static Pattern compile(String regex) {
        return new Pattern();
    }
}
