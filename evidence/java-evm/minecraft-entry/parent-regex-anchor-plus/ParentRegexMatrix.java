import java.util.regex.Pattern;

/** Generated-only oracle assertions, not original-server inputs or authority. */
public final class ParentRegexMatrix {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        String[] terminators = {"\n", "\r", "\r\n", "\u0085", "\u2028", "\u2029"};
        for (int i = 0; i < terminators.length; i++) {
            String text = "abc" + terminators[i];
            Pattern p = Pattern.compile("^[a-z]+$");
            check(!p.matcher(text).matches());
            check(p.matcher(text).replaceAll("X").equals("X" + terminators[i]));
        }
        check("x\r\n".replaceAll("^[^\n]+$", "X").equals("X\r\n"));
        check("x\r\n".replaceAll("[x\r]+$", "X").equals("X\r\n"));
        check("\r\r\n".replaceAll("\r+$", "X").equals("X\r\n"));
        check("\r\n".replaceAll("\r+$", "X").equals("\r\n"));
        check("x\r\n".replaceAll("^x\r$", "X").equals("x\r\n"));
        check(Pattern.compile("a+").matcher("aaaa").matches());
        check(!Pattern.compile("a+").matcher("").matches());
        check("baaaac".replaceAll("a+", "<$0>").equals("b<aaaa>c"));
        check(Pattern.compile("(?i)^[a-c]+$").matcher("ABc").matches());
        check(!Pattern.compile("(?i)^[a-c]+$").matcher("ABz").matches());
        check("ab".replaceAll("^", "X").equals("Xab"));
        check("ab\r\n".replaceAll("$", "X").equals("abX\r\nX"));
        check("ab".replaceAll("", "-").equals("-a-b-"));
        check("aaba".replaceAll("a", "$0!").equals("a!a!ba!"));
        String untouched = new String(new char[] {'x'});
        check(untouched.replaceAll("^a+$", null) == untouched);
        Pattern digits = Pattern.compile("^[0-9_]+$");
        check(digits.matcher("01_9").matches());
        check(!digits.matcher("01-a").matches());
    }
}
