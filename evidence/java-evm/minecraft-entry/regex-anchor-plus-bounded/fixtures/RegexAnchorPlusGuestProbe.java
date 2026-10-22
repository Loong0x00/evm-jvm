package regexprobe;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Trusted generated guest fixture, only; no original programs/data. */
public final class RegexAnchorPlusGuestProbe {
    private static void require(boolean ok) {
        if (!ok) throw new RuntimeException("regex fixture assertion");
    }
    public static void main(String[] args) {
        require(Pattern.compile("ab").matcher("ab").matches());
        require(!Pattern.compile("ab").matcher("zab").matches());
        require(Pattern.compile("^q+$").matcher("qqq").matches());
        require(!Pattern.compile("^q+$").matcher("").matches());
        require(Pattern.compile("^[a-c]+$").matcher("abccba").matches());
        require(Pattern.compile("^[^0-9]+$").matcher("xy_-").matches());
        require(Pattern.compile("(?i)^[a-c]+$").matcher("aBc").matches());
        require(!Pattern.compile("(?i)^[a-c]+$").matcher("\u00e9").matches());
        require(Pattern.compile("^ab").matcher("ab").matches());
        require(!Pattern.compile("^ab").matcher("zab").matches());
        require(!Pattern.compile("^a$").matcher("a\n").matches());
        require("x<abc>Y<b>".equals(Pattern.compile("[a-c]+").matcher("xabcYb").replaceAll("<$0>")));
        String unchanged = "abc";
        require(Pattern.compile("z+").matcher(unchanged).replaceAll("x") == unchanged);
        require("X\n".equals(Pattern.compile("a$").matcher("a\n").replaceAll("X")));
        require(!Pattern.compile("[^\n]+$").matcher("x\r\n").matches());
        require("X\r\n".equals(Pattern.compile("[^\n]+$").matcher("x\r\n").replaceAll("X")));
        require("X\r\n".equals(Pattern.compile("^[^\n]+$").matcher("x\r\n").replaceAll("X")));
        require("X\r\n".equals(Pattern.compile("[x\r]+$").matcher("x\r\n").replaceAll("X")));
        require("X\r\n".equals(Pattern.compile("\r+$").matcher("\r\r\n").replaceAll("X")));
        require("aX\r\nX".equals(Pattern.compile("$").matcher("a\r\n").replaceAll("X")));
        require("aXbX".equals(Pattern.compile("\\$").matcher("a$b$").replaceAll("X")));
        Matcher full = Pattern.compile("[0-9]+").matcher("12");
        require(full.matches());
        require(!Pattern.compile("[0-9]+").matcher("12x").matches());
        boolean caught = false;
        try { Pattern.compile(null); } catch (NullPointerException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("["); } catch (java.util.regex.PatternSyntaxException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("\\"); } catch (java.util.regex.PatternSyntaxException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("+"); } catch (java.util.regex.PatternSyntaxException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("a").matcher(null); } catch (NullPointerException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("a").matcher("a").replaceAll(null); } catch (NullPointerException e) { caught = true; }
        require(caught);
        caught = false;
        try { Pattern.compile("a").matcher("a").replaceAll("$"); } catch (IllegalArgumentException e) { caught = true; }
        require(caught);
    }
}
