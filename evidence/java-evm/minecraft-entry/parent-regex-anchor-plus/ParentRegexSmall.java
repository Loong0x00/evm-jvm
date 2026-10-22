import java.util.regex.Pattern;

/** Parent generated-only admission and CRLF-backoff witness. */
public final class ParentRegexSmall {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Pattern names = Pattern.compile("^[a-z0-9_]+$");
        check(names.matcher("abc_12").matches());
        check(!names.matcher("").matches());
        check(!names.matcher("A").matches());
        check("x\r\n".replaceAll("[^\n]+$", "X").equals("X\r\n"));
        check("a!b".replaceAll("[^a-z]", "").equals("ab"));
    }
}
