import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/** Generated-fixture-only Java 8 observable semantics probe; never original input. */
public final class RegexSemanticsProbe {
    private static void emit(String name, boolean value) {
        System.out.println(name + "=" + value);
    }
    private static void emit(String name, String value) {
        StringBuilder b = new StringBuilder();
        b.append(name).append('=');
        for (int i = 0; i < value.length(); i++) b.append(Integer.toHexString(value.charAt(i))).append(',');
        System.out.println(b.toString());
    }
    private static void match(String name, String regex, String input) {
        emit(name, Pattern.compile(regex).matcher(input).matches());
    }
    private static void replace(String name, String regex, String input, String repl) {
        emit(name, Pattern.compile(regex).matcher(input).replaceAll(repl));
    }
    public static void main(String[] args) {
        match("literal", "ab", "ab");
        match("literalNo", "ab", "zab");
        match("plusLiteral", "^q+$", "qqq");
        match("plusMin", "^q+$", "");
        match("rangePlus", "^[a-c]+$", "abccba");
        match("negatedPlus", "^[^0-9]+$", "xy_-");
        match("asciiFold", "(?i)^[a-c]+$", "aBc");
        match("asciiFoldNo", "(?i)^[a-c]+$", "\u00e9");
        match("startAnchor", "^ab", "ab");
        match("startAnchorNo", "^ab", "zab");
        match("endFinalLF", "a$", "a\n");
        match("endStrict", "^a$", "a\n");
        match("plusCrLfWhole", "[^\n]+$", "x\r\n");
        match("plusCrLfAnchoredWhole", "^[^\n]+$", "x\r\n");
        match("plusCrOnlyWhole", "[x\r]+$", "x\r\n");
        match("plusLiteralCrWhole", "\r+$", "\r\r\n");
        match("plusMinBeforeFinalCRLF", "\r+$", "\r\n");
        replace("replacePlus", "[a-c]+", "xabcYb", "<$0>");
        replace("replaceNoMatch", "^z+", "abc", "Q");
        replace("replaceEndLF", "a$", "a\n", "X");
        replace("replaceNegatedNewlineCRLF", "[^\n]+$", "x\r\n", "X");
        replace("replaceAnchoredNegatedNewlineCRLF", "^[^\n]+$", "x\r\n", "X");
        replace("replaceClassCRLF", "[x\r]+$", "x\r\n", "X");
        replace("replaceLiteralCRLF", "\r+$", "\r\r\n", "X");
        replace("replaceMinBeforeFinalCRLF", "\r+$", "\r\n", "X");
        match("quantifiedAnchorPlus", "^+", "");
        match("quantifiedAnchorStar", "^*", "");
        match("quantifiedAnchorQuestion", "^?", "");
        match("quantifiedAnchorEnd", "^+$", "");
        replace("replaceDollarCRLF", "$", "a\r\n", "X");
        replace("replaceDollarNEL", "$", "a\u0085", "X");
        replace("replaceDollarLS", "$", "a\u2028", "X");
        replace("replaceDollarPS", "$", "a\u2029", "X");
        replace("replaceEscapedDollar", "\\$", "a$b$", "X");
        emit("identity", Pattern.compile("z+").matcher("abc").replaceAll("x") == "abc");
        try { Pattern.compile(null); emit("nullPattern", "none"); }
        catch (NullPointerException e) { emit("nullPattern", "NPE"); }
        try { Pattern.compile("["); emit("malformedClass", "none"); }
        catch (PatternSyntaxException e) { emit("malformedClass", "PSE"); }
        try { Pattern.compile("\\"); emit("malformedEscape", "none"); }
        catch (PatternSyntaxException e) { emit("malformedEscape", "PSE"); }
        try { Pattern.compile("a").matcher(null); emit("nullInput", "none"); }
        catch (NullPointerException e) { emit("nullInput", "NPE"); }
        try { Pattern.compile("a").matcher("a").replaceAll(null); emit("nullReplacement", "none"); }
        catch (NullPointerException e) { emit("nullReplacement", "NPE"); }
        try { Pattern.compile("a").matcher("a").replaceAll("$"); emit("badReplacement", "none"); }
        catch (IllegalArgumentException e) { emit("badReplacement", "IAE"); }
    }
}
