package java.util.regex;

/** Compile-only raw-name replacement probe; never executed on the host. */
public class PatternSyntaxException extends IllegalArgumentException {
    public PatternSyntaxException(String description, String pattern, int index) {
        super();
    }
}
