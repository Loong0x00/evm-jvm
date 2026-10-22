package regexprobe;
import java.util.regex.Pattern;
/** Minimal generated q1/q7 witness. */
public final class RegexOnePlusProbe {
    public static void main(String[] args) {
        if (!Pattern.compile("a+").matcher("a").matches()) throw new RuntimeException("plus");
    }
}
