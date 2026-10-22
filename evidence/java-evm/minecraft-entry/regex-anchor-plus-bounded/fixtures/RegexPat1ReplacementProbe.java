package regexprobe;
import java.util.regex.Pattern;
/** Regression for the original fixed-width PAT1 program and replacement grammar. */
public final class RegexPat1ReplacementProbe {
    private static void check(boolean value) { if (!value) throw new RuntimeException("PAT1 replacement assertion"); }
    public static void main(String[] args) {
        check(Pattern.compile("ab").matcher("ab").matches());
        check(!Pattern.compile("ab").matcher("zab").matches());
        check("z<ab>!".equals(Pattern.compile("ab").matcher("zab!").replaceAll("<$0>")));
        String unchanged = "abc";
        check(Pattern.compile("z").matcher(unchanged).replaceAll("X") == unchanged);
        check("x$ay".equals(Pattern.compile("a").matcher("xay").replaceAll("\\$$0")));
        check("X".equals(Pattern.compile("[a-c]").matcher("b").replaceAll("X")));
    }
}
