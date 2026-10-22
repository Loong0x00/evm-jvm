package regexprobe;
import java.util.regex.Pattern;
/** Must produce a profile refusal, never a fabricated guest result. */
public final class RegexUnsupportedProbe {
    public static void main(String[] args) {
        Pattern.compile("a|b");
        throw new RuntimeException("unsupported alternation returned");
    }
}
