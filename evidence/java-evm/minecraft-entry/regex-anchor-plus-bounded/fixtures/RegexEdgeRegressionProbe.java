package regexprobe;
import java.util.regex.Pattern;
/** Bounded P42 regression workload; trusted synthetic text only. */
public final class RegexEdgeRegressionProbe {
    private static void check(boolean value) { if (!value) throw new RuntimeException("regex edge assertion"); }
    public static void main(String[] args) {
        check(!Pattern.compile("[^\n]+$").matcher("x\r\n").matches());
        check("X\r\n".equals(Pattern.compile("[^\n]+$").matcher("x\r\n").replaceAll("X")));
        check("X\r\n".equals(Pattern.compile("^[^\n]+$").matcher("x\r\n").replaceAll("X")));
        check("X\r\n".equals(Pattern.compile("[x\r]+$").matcher("x\r\n").replaceAll("X")));
        check("X\r\n".equals(Pattern.compile("\r+$").matcher("\r\r\n").replaceAll("X")));
        check(!Pattern.compile("\r+$").matcher("\r\n").matches());
        String oneCr = "\r\n";
        check(Pattern.compile("\r+$").matcher(oneCr).replaceAll("X") == oneCr);
        check("X\n".equals(Pattern.compile("q+").matcher("qq\n").replaceAll("X")));
        check("<abc>".equals(Pattern.compile("[a-c]+").matcher("abc").replaceAll("<$0>")));
        String unchanged = "other";
        check(Pattern.compile("z+").matcher(unchanged).replaceAll("X") == unchanged);
        check(Pattern.compile("(?i)^[a-c]+$").matcher("aBc").matches());
        check(!Pattern.compile("^a+$").matcher("zaa").matches());
        check("X".equals(Pattern.compile("a$").matcher("a").replaceAll("X")));
        check("X\r\n".equals(Pattern.compile("a+$").matcher("aa\r\n").replaceAll("X")));
        boolean syntax = false;
        try { Pattern.compile("+"); } catch (java.util.regex.PatternSyntaxException e) { syntax = true; }
        check(syntax);
    }
}
