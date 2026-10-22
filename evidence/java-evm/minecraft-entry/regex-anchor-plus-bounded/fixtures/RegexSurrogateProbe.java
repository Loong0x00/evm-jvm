package regexprobe;
import java.util.regex.Pattern;
/** Conservative surrogate-input profile refusal, not a fabricated match. */
public final class RegexSurrogateProbe {
    public static void main(String[] args) {
        Pattern.compile("a").matcher("\ud800").matches();
        throw new RuntimeException("surrogate input unexpectedly accepted");
    }
}
