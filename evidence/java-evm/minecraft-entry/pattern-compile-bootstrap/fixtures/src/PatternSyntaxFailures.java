import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/** Checks guest Java 8 PatternSyntaxException fields and formatted message. */
public final class PatternSyntaxFailures {
    private static void require(boolean condition) {
        if (!condition) throw new AssertionError("PatternSyntaxException mismatch");
    }

    private static void expect(String regex, String description, int index, String message) {
        try {
            Pattern.compile(regex);
            throw new AssertionError("invalid pattern compiled");
        } catch (PatternSyntaxException failure) {
            require(failure.getDescription().equals(description));
            require(failure.getPattern().equals(regex));
            require(failure.getIndex() == index);
            require(failure.getMessage().equals(message));
        }
    }

    public static void main(String[] args) {
        expect("[z-a]", "Illegal character range", 3,
            "Illegal character range near index 3\n[z-a]\n   ^");
        expect("[]", "Unclosed character class", 1,
            "Unclosed character class near index 1\n[]\n ^");
        expect("(?q)", "Unknown inline modifier", 2,
            "Unknown inline modifier near index 2\n(?q)\n  ^");

        try {
            Pattern.compile(null);
            throw new AssertionError("null pattern compiled");
        } catch (NullPointerException expected) {
            // Java 8 Pattern.compile(null) is a guest NullPointerException.
        }
    }
}
