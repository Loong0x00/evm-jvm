import java.util.regex.Pattern;

/** Generated-only Java 8 oracle and guest compilation-family probe. */
public final class PatternCompileMatrix {
    private static void require(boolean condition) {
        if (!condition) throw new AssertionError("Pattern compile result mismatch");
    }

    public static void main(String[] args) {
        String measured = "(?i)\u00a7[0-9A-FK-OR]";
        Pattern required = Pattern.compile(measured);
        require(required.pattern().equals(measured));
        require(required.toString().equals(measured));
        require(required.flags() == Pattern.CASE_INSENSITIVE);

        Pattern literal = Pattern.compile("abc");
        require(literal.pattern().equals("abc") && literal.flags() == 0);

        Pattern aroundClass = Pattern.compile("a[b-d]z");
        require(aroundClass.pattern().equals("a[b-d]z") && aroundClass.flags() == 0);

        Pattern foldedNegatedClass = Pattern.compile("(?i)[^A-C]");
        require(foldedNegatedClass.pattern().equals("(?i)[^A-C]"));
        require(foldedNegatedClass.flags() == Pattern.CASE_INSENSITIVE);

        Pattern escapedPunctuation = Pattern.compile("x\\.");
        require(escapedPunctuation.pattern().equals("x\\."));
        require(escapedPunctuation.flags() == 0);

        Pattern adjacentRanges = Pattern.compile("[a-b-c]");
        require(adjacentRanges.pattern().equals("[a-b-c]"));

        Pattern empty = Pattern.compile("");
        require(empty.pattern().equals("") && empty.flags() == 0);

        Pattern flagsOnly = Pattern.compile("(?i)");
        require(flagsOnly.pattern().equals("(?i)"));
        require(flagsOnly.flags() == Pattern.CASE_INSENSITIVE);
    }
}
