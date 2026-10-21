import java.util.regex.Pattern;

/** Never run on the host; this supplies a raw platform-name replacement refusal probe. */
public final class PatternRawReplacementMain {
    public static void main(String[] args) {
        Pattern.compile("abc");
    }
}
