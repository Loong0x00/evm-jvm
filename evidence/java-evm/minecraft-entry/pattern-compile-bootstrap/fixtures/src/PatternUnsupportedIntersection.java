import java.util.regex.Pattern;

/** Valid Java 8 class intersection outside the bounded literal/range grammar. */
public final class PatternUnsupportedIntersection {
    public static void main(String[] args) {
        Pattern.compile("[a-z&&[aeiou]]");
    }
}
