import java.util.regex.Pattern;

/** Valid Java 8 inline mode other than the supported CASE_INSENSITIVE-only form. */
public final class PatternUnsupportedInline {
    public static void main(String[] args) {
        Pattern.compile("(?m)foo");
    }
}
