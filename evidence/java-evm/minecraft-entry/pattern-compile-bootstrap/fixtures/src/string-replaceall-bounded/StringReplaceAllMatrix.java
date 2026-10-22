import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/** Generated-only Java 8 oracle and guest String.replaceAll profile matrix. */
public final class StringReplaceAllMatrix {
    private static void require(boolean condition) {
        if (!condition) throw new ArithmeticException();
    }

    public static void main(String[] args) {
        // General token-sequence matching: leftmost, non-overlapping literals,
        // classes, ranges, negation, escaped punctuation, and flags.
        require("cat cat".replaceAll("cat", "dog").equals("dog dog"));
        require("aaaaa".replaceAll("aa", "X").equals("XXa"));
        require("ababa".replaceAll("aba", "X").equals("Xba"));
        require("abz".replaceAll("a[b-d]z", "Q").equals("Q"));
        require("aBcD".replaceAll("(?i)[a-c]", "x").equals("xxxD"));
        require("aAbB".replaceAll("(?i)ab", "X").equals("aXB"));
        require(Pattern.compile("ab").matcher("zabab").replaceAll("_").equals("z__"));
        require("x.x.".replaceAll("x\\.", "!").equals("!!"));
        require("a-b.c".replaceAll("[-.]", "_").equals("a_b_c"));
        require("a§b".replaceAll("[^a-z]", "").equals("ab"));
        require("a§Bc".replaceAll("(?i)[^a-z]", "").equals("aBc"));
        require("<a><b>".replaceAll("[<>]", "").equals("ab"));

        // Start/end, adjacent and repeated matches, empty input and zero width.
        require("aaa".replaceAll("a", "<").equals("<<<"));
        require("".replaceAll("a", "X").equals(""));
        require("".replaceAll("", "_").equals("_"));
        require("ab".replaceAll("", "-").equals("-a-b-"));
        require("abc".replaceAll("z", "X").equals("abc"));

        // Replacement text is literal except for Java's backslash quoting and
        // group-zero reference; this admitted regex grammar has no captures.
        require("aba".replaceAll("a", "<$0>").equals("<a>b<a>"));
        require("aba".replaceAll("a", "<$00>").equals("<a>b<a>"));
        require("a".replaceAll("a", "$01").equals("a1"));
        require("a".replaceAll("a", "\\$").equals("$"));
        require("a".replaceAll("a", "\\\\").equals("\\"));
        require("a".replaceAll("a", "\\z").equals("z"));

        // Java identity rules: no match returns the source String; a match
        // constructs an owned result even when replacement text is identical.
        String untouched = new String(new char[] {'n', 'o'});
        require(untouched.replaceAll("z", "x") == untouched);
        String source = new String(new char[] {'a'});
        String replaced = source.replaceAll("a", "a");
        require(replaced.equals("a") && replaced != source && replaced != "a");

        // Invalid regex and replacement inputs produce ordinary guest exceptions.
        String absentReceiver = null;
        try {
            absentReceiver.replaceAll("a", "x");
            throw new ArithmeticException();
        } catch (NullPointerException expected) { }
        try {
            "a".replaceAll(null, "x");
            throw new ArithmeticException();
        } catch (NullPointerException expected) { }
        try {
            "a".replaceAll("a", null);
            throw new ArithmeticException();
        } catch (NullPointerException expected) { }
        try {
            "a".replaceAll("a", "\\");
            throw new ArithmeticException();
        } catch (IllegalArgumentException expected) { }
        try {
            "a".replaceAll("a", "$");
            throw new ArithmeticException();
        } catch (IllegalArgumentException expected) { }
        try {
            "a".replaceAll("a", "$x");
            throw new ArithmeticException();
        } catch (IllegalArgumentException expected) { }
        try {
            "a".replaceAll("a", "$1");
            throw new ArithmeticException();
        } catch (IndexOutOfBoundsException expected) { }
        try {
            "a".replaceAll("a", "${missing}");
            throw new ArithmeticException();
        } catch (IllegalArgumentException expected) { }
        try {
            "a".replaceAll("[", "x");
            throw new ArithmeticException();
        } catch (PatternSyntaxException expected) { }
        try {
            Pattern.compile("a").matcher(null);
            throw new ArithmeticException();
        } catch (NullPointerException expected) { }

        // Matcher.replaceAll, as in Java 8, does not inspect a null replacement
        // when the pattern has no match; it returns the original String identity.
        String noMatch = new String(new char[] {'n', 'o'});
        require(noMatch.replaceAll("z", null) == noMatch);
    }
}
