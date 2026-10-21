import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/** Never run on the host; this supplies a raw exception-name replacement refusal probe. */
public final class PatternSyntaxExceptionRawReplacementMain {
    public static void main(String[] args) {
        try {
            Pattern.compile("[z-a]");
        } catch (PatternSyntaxException expected) {
            // The raw class is rejected before this path can execute.
        }
    }
}
