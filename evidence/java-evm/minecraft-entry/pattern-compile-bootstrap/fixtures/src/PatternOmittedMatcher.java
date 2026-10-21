import java.util.regex.Pattern;

/** Matcher creation is intentionally outside the compile-only measured slice. */
public final class PatternOmittedMatcher {
    public static void main(String[] args) {
        Pattern.compile("abc").matcher("abc");
    }
}
