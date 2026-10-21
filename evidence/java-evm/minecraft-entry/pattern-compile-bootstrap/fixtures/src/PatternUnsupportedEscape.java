import java.util.regex.Pattern;

/** Valid Java 8 shorthand escape outside the bounded literal/range grammar. */
public final class PatternUnsupportedEscape {
    public static void main(String[] args) {
        Pattern.compile("\\d+");
    }
}
